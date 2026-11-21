# ADR-018: People sign in through the API and hold a server-side session

- Status: Accepted — owner, 2026-11-21; drafted from the owner's answers in the
  identity and authorisation grilling (2026-11-21) and their answers to its review;
  the options chosen are marked ✅. It supersedes ADR-003 for the API data source;
  ADR-003 stands for the Sheets adapter until the deployed editor switches to the API.
- Date: 2026-11-21

## Context

ADR-003 connects the editor to Google Sheets with a browser-held access token and never
learns who the user is. The API that replaces the spreadsheet (ADR-015, ADR-017) must
know who each person is: every change set names its person, a scratch is visible to its
owner alone, and row-level security reads the person and the tenant per transaction.
ADR-015 fixes the shape this ADR fills in: a person has one or more sign-in identities,
linked explicitly and never merged by email (ADR-015 Option 11); access is a membership
granted by a tenant admin's invitation (ADR-015 Option 12); writes to shared tables go
to a platform audit log (ADR-015 Option 27). Where the editor and API are served from,
and the API's HTTP hardening, are ADR-020's; what people may do is ADR-019's.

The owner wants sign-in with Google and Microsoft (2026-11-20): DHCW's Google Workspace
first, which today's editor already uses, then Microsoft Entra ID through the NHS Wales
directory, after which Google is retired (2026-11-21). Security is the owner's first
priority. The analysis behind this ADR is
[identity and authorisation](../analysis/identity-and-authorisation.md); the facts that
shape it:

- NHS Wales runs one Entra directory for every organisation, so a token's directory
  (`tid`) never says which tenant a person belongs to.
- An email claim is mutable and, on Entra, unverified unless its domain owner is: keying
  an account on it allows takeover.
- RFC 10017 (OAuth 2.0 for Browser-Based Applications, August 2026) ranks a backend that
  runs the OAuth flow, leaving the browser only an `HttpOnly` cookie, as the most secure
  pattern for browser apps.

## Decision

### The API runs the sign-in

- **The API is a confidential OpenID Connect client** for each provider: authorisation
  code with PKCE (`S256`), `state` and `nonce`, by a top-level navigation, never a
  popup, with `response_mode=query`. The browser never holds a provider token; the API
  keeps none after sign-in, since it calls no provider API. Scopes are
  `openid email profile` only.
- **Providers are a fixed allow-list of issuers, in code**: DHCW's Google Workspace
  (`https://accounts.google.com`, also accepting the `accounts.google.com` form Google
  documents), then the NHS Wales directory as a single-tenant Entra registration
  (`https://login.microsoftonline.com/{tid}/v2.0`), never the `common` or
  `organizations` endpoints. Adding a provider or directory amends this ADR.
- **The local mock provider can never be admitted in a deployed environment**: its
  issuer is accepted only in an explicit local mode; the API refuses a non-HTTPS or
  loopback issuer whenever it runs on Cloud Run (`K_SERVICE` set), tested against the
  production image; the mock binds to loopback; settings fail closed (ADR-017).
- **Each provider has its own callback path**, and the sign-in transaction records the
  issuer it was started for, so a response from one provider cannot complete another's
  sign-in (RFC 9700, mix-up attacks).
- **ID tokens are validated in full by a maintained library**: signature against keys
  from the provider's pinned discovery document, an algorithm allow-list (`RS256`), the
  issuer, `aud` equal to the client ID, `exp` and `iat` within a minute's skew, `nonce`,
  and `azp` where present. Keys are cached, and kept across a provider outage; an
  unknown `kid` triggers one rate-limited refetch with a timeout; an unreachable key set
  fails closed. Tests cover each refused claim and a key rollover. python-jose and
  hand-rolled JWT parsing are banned (ruff banned-API); only the identity module imports
  the OIDC library, and only the session service writes sessions (import-linter).
- **Client authentication**: Google by its client secret, held in Secret Manager and
  rotated; Entra by a federated credential trusting the API's Google service account, or
  a certificate, never a client secret (to be confirmed in the Entra spike).
- **Local development and tests use the same code path** against the mock provider in
  Compose; there is no development-only sign-in route. In local mode the cookie names
  carry the port, since cookies ignore ports and parallel worktrees share `localhost`.

### The sign-in transaction

- **Starting a sign-in is a same-origin `POST`** naming the provider and the
  transaction's purpose: `sign-in`, `link` (adding an identity) or `redeem` (an
  invitation). The API stores the state, nonce, PKCE verifier, issuer, purpose, a return
  path checked against an allow-list (no open redirect), and, for `link`, the session
  and person that started it, or, for `redeem`, the invitation; for ten minutes, behind a
  `__Host-` cookie named for the transaction, so two tabs signing in do not overwrite
  each other, with `SameSite=Lax` (the provider's redirect back is a cross-site
  navigation, so the `Strict` session cookie does not arrive with it). The start answers
  with the provider's authorisation address, and the editor navigates to it.
- **The callback lands on a static editor page**, which then asks "who am I": the new
  `Strict` cookie is not sent on the redirect that a cross-site navigation began.
- **The callback is the one state-changing `GET`**, exempt from ADR-020's same-origin
  rule because it is bound instead by the transaction cookie, the single-use state, the
  nonce and PKCE. A missing, reused or expired state is refused, which also defeats
  login CSRF.
- **At every callback, whatever its purpose**: the person must not be disabled; a
  Google identity is refused for a person who holds an Entra identity; and for `redeem`,
  the callback's issuer must be the provider the invitation names.
- **Then, by purpose:**
  - `sign-in`: the identity must belong to a person; else refused (below).
  - `link`: as _Linking identities_ below; the session ID is replaced.
  - `redeem`: any existing session is ignored; the invitation binds to the identity the
    provider returned (below), and a new session replaces any old one.
- **The transaction table is the only database write anonymous traffic can cause**,
  bounded by the edge's rate limit (ADR-020) and a one-day purge. A refused sign-in lands
  on an editor route with an error code, so its copy is in English and Welsh (ADR-008).
- **The OIDC `code` and `state` travel in the callback's URL** and so reach request
  logs: tolerable, since the code is single-use, bound to PKCE and useless without the
  client's credentials, and the state is single-use. Request-log access is restricted
  (EPC-023).

### Who a person is

- **An identity is `(issuer, subject)`**: Google's `sub`; Entra's `oid` under the NHS
  Wales directory's issuer (Entra's `sub` is pairwise per app registration). This
  refines ADR-015 Option 11's "provider and subject".
- **Email and name are display attributes of the identity**, refreshed at each sign-in,
  never a key: no lookup, link or grant matches on them, except an invitation's address
  below. A person's name lives on the person (ADR-015); the email stays on each
  identity, since a person's Google and Entra addresses may differ. The profile picture
  is not stored.
- **Google sign-in admits DHCW's Workspace only** (Option 3): an Internal OAuth client
  in DHCW's Workspace organisation, and the API also refuses a token whose `hd` is not
  on the allow-list or whose `email_verified` is not true.
- **Entra sign-in admits any valid user of the NHS Wales directory** (Option 4): no
  app-specific Conditional Access policy and no group assignment; the invitation is the
  app's gate. Guest accounts are refused.
- **No MFA requirement in the API for now** (Option 7): sign-in is as strong as each
  provider's own policy makes it, for every role. Google can report the time and method
  of a sign-in (`auth_time`, `amr`) through its security bundle, for published, verified
  apps that enable it; Entra's v2.0 ID token carries no method claim by default. Neither
  is relied on yet; a later rule using them amends this ADR.
- **Availability**: open sessions and the public read do not depend on the provider;
  while only Google works, a Google outage stops new sign-ins, with no fallback.

### Getting in

- **A person record is created only when an invitation is redeemed** (Option 6). A
  sign-in by someone with no person record and no invitation is refused, writes nothing
  but a log line, and lands on "You haven't been invited". No one in the
  125,000-strong directory leaves a row by trying. Asking for access from that page is a
  later story (STY-094).
- **An invitation is a single-use link and a matching verified email** (Option 5): a
  256-bit token, stored only as its SHA-256 hash, expiring after seven days, naming the
  tenant, the invited address, its provider and the roles. The token travels in the
  link's URL fragment to an editor route, so it reaches no request log or `Referer`;
  that route clears the fragment, shows which tenant is inviting and who invited, and
  posts the token to the API only when the person accepts, so nobody joins a tenant
  without seeing which. It is redeemed by a sign-in whose verified email (Google:
  `email` with `email_verified`; Entra: a claim the directory controls, chosen in the
  Entra spike, which blocks Entra invitations until it settles) equals the invited
  address, compared case-folded. A forwarded link alone, or a spoofed email alone,
  admits nobody.
- **Redemption consumes the token atomically**, and is refused, with one code, when the
  invitation is redeemed, revoked or expired, when its inviter no longer holds
  `members:manage` (an invitation a platform job issued has no such inviter, and an
  operator revokes it), or when its tenant or a role it names no longer exists. When the
  returned identity already belongs to a person, the membership is added to that person;
  otherwise the person, the identity and the membership are created together.
- **An invitation is part of the tenant's access**: creating, revoking and redeeming one
  are access change sets, like any other access write (ADR-015).
- **The admin copies the invitation link** and sends it themselves (Option 8). The API
  sending email is a later decision.
- **A tenant's first admin, and a replacement admin, are invited too**: a platform job
  (ADR-019) issues the invitation, recorded in the platform audit log, so there is no
  second way in.

### Linking identities and the move to Entra

- **Only the person attaches an identity** (Option 9), through a `link` sign-in while
  signed in. **The person removes one** (never their last), **or a platform operator
  does**. A tenant admin does neither: people are shared across tenants, so an admin of
  one tenant attaching or removing an identity would take over, or lock out, a person's
  access to another. A tenant admin ends a membership instead.
- **Linking is guarded against a session someone else is using**, at a shared desk or
  through a stolen cookie, since a linked Entra identity would lock the person's Google
  sign-in out:
  - a person holds at most one identity per issuer, and only an Entra identity can be
    linked;
  - the session that starts a `link` must itself be under ten minutes old, so the
    person has just signed in;
  - an identity that already belongs to anyone else is refused, never moved or merged;
  - linking revokes the person's other sessions and shows the new identity, with its
    time, on their account page;
  - for seven days after a link, the person cannot remove an identity, and a session
    started with the newer identity never can; a platform operator undoes a hostile
    link.

  A walk-up on a desk left signed in remains a residual risk, as signing out's does.

- **Production may start on Google** (Option 2). When Entra works, each person links
  their NHS Wales Microsoft account while signed in with Google, and from then on
  **signs in with Entra only**: their Google sign-in is refused (Option 11). New
  invitations name Entra from the day it works. On a date announced in advance, Google
  sign-in stops for everyone, and every session started with a Google identity is
  revoked (Option 10). Anyone who did not link is re-invited and starts as a new person;
  their past change sets keep their old person. A tenant whose only admin did not link
  gets a replacement through the platform job.

### Sessions

- **A session is an opaque row in PostgreSQL** (Option 1): a 256-bit random ID in the
  cookie, only its SHA-256 hash stored, with the person, the identity and time of the
  sign-in, last activity, an idle and an absolute expiry, and revocation; no IP address
  or user agent. It is found by hash through a definer function.
- **A state-changing request carries the person the editor believes is signed in**, and
  the API refuses it when the session's person differs, so a form held across a
  sign-in by someone else can never be saved as theirs.
- **The cookie is `__Host-`, `Secure`, `HttpOnly`, `SameSite=Strict` and `Path=/`, with
  no expiry attribute.** A browser that restores sessions keeps it, so the server's
  timeouts, not the browser, end a session.
- **A session ends after 60 minutes without a request to the API, or 10 hours after
  sign-in, whichever comes first** (Option 12), both enforced by the API (ASVS 5.0 V7;
  NIST SP 800-63B-4 sets 1 and 24 hours for AAL2). A leaver disabled in Workspace or
  Entra keeps an open session at most that long.
- **Every request re-reads the session and the person**, and refuses a disabled person;
  ADR-019 re-reads the membership and roles. Removing a member, a role or a person bites
  on the next request. Last activity is written at most once a minute; each identity
  records its last sign-in, for the access review (ADR-019).
- **The session ID is replaced at sign-in and at linking an identity.**
- **Signing out** revokes the row and expires the cookie (no `Clear-Site-Data` for
  cookies, which would clear every site on the registrable domain); it does not sign the
  person out of the provider (Option 13). The next sign-in in that browser asks Google
  to show its account picker (`prompt=select_account`), and Entra to sign in afresh
  (`prompt=login`). On Google this stops a silent sign-in, not a deliberate one: the
  last person's account, still signed in to Google in that browser, is one click away.
  That residual risk on a shared desk is accepted until Entra. "Sign out everywhere"
  revokes all the person's sessions.
- **No step-up on Google** (Option 14): access changes rely on the session lifetimes and
  on each being an attributed change set. With Entra, access changes and redaction will
  require an Entra authentication context; that amends this ADR when Entra lands.

### The editor

- **The editor's `AuthClient` is reshaped for the API data source**: `connect()` posts
  the sign-in start for the chosen provider and navigates to the authorisation address
  it returns; the state comes
  from a "who am I" call; the access token leaves the port, so no token reaches the
  browser at all (ADR-016 kept tokens in memory). A 401 moves the state to `expired`.
- **Expiry keeps an open form for its own person** (Option 15): two minutes before the
  idle limit the editor's session warning offers "Stay signed in", which extends it;
  before the absolute limit, and after any expiry, "Sign in again" opens the sign-in in
  a new tab. When the original tab regains focus it re-checks "who am I": the same
  person keeps the form; a different person, as when someone else signs in at a shared
  desk, makes the tab discard the held form unsent and treat itself as signed out. Any
  request to the API counts as activity.
- **The account menu shows the person's name and their tenant** (Option 16), with a
  tenant switcher only for someone in more than one; the email is on the account page.
  ADR-003's "we never claim to know who the user is" ends with the Sheets adapter.

### Records and retention

- **New shared tables** (an ADR-015 _Tenancy_ amendment): sessions and sign-in
  transactions, each with row-level security, reached only through their definer
  functions and by the person they belong to.
- **New definer functions**, each owned by a dedicated no-login role with only the
  grants it needs and policies scoped to that role (not the schema owner, which holds
  DDL rights; forced row-level security binds an owner too), a pinned `search_path` and
  `EXECUTE` revoked from `PUBLIC`: creating a sign-in transaction and looking it up;
  creating, looking up, extending and revoking a session (one person's, or every session
  started with a Google identity at the cut-over); the invitation lookup by token hash;
  redemption; and the purges of transactions, sessions and invitations the retention
  jobs run. Redemption takes only the token's
  hash and the validated issuer, subject, email and name; it locks the invitation row
  and takes the tenant, the roles and the inviter from it; and it creates the person,
  identity, membership and session with no person or tenant yet set, recording the
  access change set with the new person as its actor.
- **Shared-table writes go to the platform audit log** (ADR-015 Option 27): a person
  created, an identity linked or removed, a person disabled, invitations a platform job
  issues. It stays append-only and is never purged.
- **Security events go to the structured log on stdout, never the database**: signed
  in, refused, signed out, session revoked, with IDs only. EPC-023 exports them to a
  retention-locked bucket.
- **Logs carry IDs, never tokens, cookies, codes, ID tokens or email addresses**;
  redaction is by an allow-list of fields. This binds the application's logs; request
  logs are restricted by EPC-023.
- **Retention, until the data protection assessment sets it** (Option 17): sign-in
  transactions deleted after a day, ended sessions after 30 days, spent or expired
  invitations after 90 days, exported security events kept two years; the database's
  deletions run as scheduled API jobs (ADR-017) through the definer functions above. The
  assessment also sets how long a person whose memberships have all ended is kept.

### Assurance

- **A threat model** of sign-in, sessions, invitations and linking is the first identity
  record: written and reviewed by DHCW's cyber security team before any identity code is
  built (Option 18). **An independent penetration test** comes before the deployed
  editor switches to the API.

## Consequences

- **Accepted risks** (owner, 2026-11-21): no MFA evidence required on sign-in, for
  every role; up to 10 hours of access for a leaver whose session is open; no step-up on
  Google; on a shared desk, the last person's Google account one click away after
  signing out.
- **ADR-015 is amended** (its _ADR-018 and ADR-019 amendments_):
  - ADR-015 Option 11: an identity is `(issuer, subject)`; only the person attaches one; the
    person (never their last) or a platform operator removes one, never a tenant admin.
  - _Tenancy_: sessions and sign-in transactions join the shared tables; the closed list
    of definer functions gains those above, owned by a dedicated no-login role rather
    than the schema owner (_Roles, operation and data protection_).
  - _People, access and permissions_: an invitation names an address, not a person,
    until it is redeemed, rather than being a pending membership the person-keyed policy
    reads; creating, revoking and redeeming one are access change sets.
  - ADR-015 Option 27: the platform audit log also records a person disabled and invitations a
    platform job issues.
- **ADR-003's Status is** "Superseded by ADR-018 for the API data source; stands
  for the Sheets adapter", with its row in `docs/adr/README.md`.
- **`docs/operations/replacing-google-sheets.md`** changes with the API adapter: no
  CORS and no `Authorization` header (ADR-020), and no `getAccessToken`.
- **The `AuthClient` port, the session warning (STY-017) and the reconnect-from-action
  flow (STY-057)** change shape for the API data source in the switch-over epic; the
  Sheets adapter keeps ADR-003 until then.
- **Follow-on work**: the threat model, then EPC-022's identity stories (schema,
  sign-in with Google and the mock provider, sessions, invitations, the editor's
  adapter); STY-094 (asking for access); a later Entra story with its spike (the email
  claim, client authentication, the authentication context); EPC-023 for the provider
  registrations and log export.

## Options (owner's choice marked ✅, 2026-11-21)

1. **Where the session lives** — ✅ the API as OIDC client, an opaque PostgreSQL session
   behind an `HttpOnly` cookie. Lost: the API minting its own JWT and refresh token
   (permissions stale until expiry, signing keys and refresh families to guard); the
   editor holding provider tokens (within reach of page scripts, left on shared
   workstations). An identity broker (a third party in every sign-in, browser-persisted
   tokens) and IAP as the app's identity (cloud lock-in, no local path) were rejected in
   the analysis.
2. **Which provider first** — ✅ Google Workspace now, Entra next, so EPC-022 does not
   wait on directory governance; production may start on Google. Lost: Entra first;
   both together; the switch-over waiting for Entra.
3. **Which Google accounts** — ✅ DHCW's Workspace only (Internal client, `hd` and
   `email_verified` checked). Lost: any invited Google account (no control the app can
   rely on); named Workspace domains.
4. **The Entra gate** — ✅ any valid NHS Wales directory user, the invitation being the
   gate (review answer). Lost: assignment to a group as well (a group to keep in step
   with invitations across organisations); an app-specific MFA policy.
5. **Redeeming an invitation** — ✅ the link and a matching verified email. Lost: the
   email alone (access on an email claim); the link alone (a forwarded link admits the
   wrong person).
6. **When a person record is created** — ✅ when an invitation is redeemed. Lost: at
   first sign-in (rows for people who never use the tool).
7. **MFA** — ✅ none required for now; each provider's own policy. Lost: accepting
   Workspace 2-Step Verification once confirmed; admins waiting for Entra.
8. **Delivering an invitation** — ✅ the admin copies the link; email later.
9. **Who links identities** — ✅ the person attaches; the person or a platform operator
   removes. Lost: ADR-015 Option 11's "or by an admin" (cross-tenant takeover or
   lock-out).
10. **Moving to Entra** — ✅ each person links, then Google stops on an announced date;
    once Entra works, ✅ Google is retired entirely. Lost: re-inviting everyone (history
    split across two person records); an operator mapping by email (the matching ADR-015
    Option 11 forbids); retiring Google only for people holding Entra; keeping both.
11. **The overlap** — ✅ a person who has linked Entra signs in with Entra only (review
    answer). Lost: both providers until the cut-over (Google bypasses what Entra
    enforces).
12. **Lifetimes** — ✅ 60 minutes idle, 10 hours absolute. Lost: 30 minutes and 8
    hours (interruptions mid-edit); 8 and 24 hours (a day on a shared desk).
13. **Signing out** — ✅ the app only, then the account picker. Lost: signing out of the
    provider too (signs people out of Microsoft 365); the app only with nothing more
    (a silent sign-in into the last person's account).
14. **Step-up** — ✅ none on Google, an Entra authentication context later. Lost:
    re-sign-in on Google (proves little while Google's session lives); no step-up ever.
15. **Expiry in the editor** — ✅ warn, extend the idle limit, sign in again in a new
    tab. Lost: a redirect that loses an open form; today's flow unchanged.
16. **The account menu** — ✅ name and tenant. Lost: name only; nothing, as today.
17. **Retention** — ✅ defaults until the data protection assessment confirms them.
18. **Assurance** — ✅ a threat model now, before the identity build; a penetration test
    before the switch-over.
