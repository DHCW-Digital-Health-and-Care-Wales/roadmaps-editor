# Identity and authorisation for the roadmaps API

How people sign in to the API that replaces the spreadsheet, how the API knows who
they are and what they may do, and which checks prove it. It was written for the
identity ADR (successor to ADR-003) and the authorisation ADR (ADR-015 Options 16, 17,
19–23, 35) that EPC-022 waited for; its decisions became three ADRs (_Outcome_). Security is the owner's first priority for both.

- **This repository:** audited at `86afe40` on 2026-11-21: ADR-003, ADR-015 (Accepted),
  ADR-016 and ADR-017 (Proposed), `.github/`, `docs/operations/google-cloud-setup.md`.
- **Owner direction:** sign-in with both Microsoft and Google (2026-11-20); Google
  today, Microsoft Entra ID with single sign-on through the NHS Wales directory later
  (2026-11-21); security is a critical priority, following current best practice.
- **Standards read:** OAuth 2.0 for Browser-Based Applications (RFC 10017,
  August 2026), the OAuth 2.0 Security BCP (RFC 9700), OWASP ASVS 5.0 (V3 web frontend
  security, V6 authentication, V7 session management, V8 authorisation, V10 OAuth and
  OIDC, V16 logging), the OWASP API Security Top 10
  (2023), NIST SP 800-63B-4 and Microsoft's guidance on email claims.

## Findings

### F1 — Every NHS Wales organisation shares one Entra directory

NHS Wales runs one shared Microsoft 365 tenancy for all its organisations (health
boards, trusts, special health authorities), more than 125,000 active users, configured
by DHCW on NHS Wales's behalf; staff who move between organisations keep their account.
So an Entra token's directory (`tid`) says "NHS Wales", never which organisation a
person works for. ADR-015's tenant cannot be read from a token: the API's memberships
stay the only authority for which tenants a person belongs to, and a person who moves
organisation keeps one identity and changes memberships.

The word clashes: Microsoft calls its directory a _tenant_. This analysis says
**directory** for Entra's and keeps **tenant** for ADR-015's; the glossary should too.

### F2 — An email address is not an identity

- Entra's `email` claim is mutable and, unless the domain owner is verified, unverified;
  apps that keyed accounts or authorisation on it suffered account takeover (the
  "nOAuth" class). Microsoft's guidance: key on the directory and object IDs (`tid`,
  `oid`), never `email`, `upn` or `preferred_username`. Entra's `sub` is pairwise per
  app registration; `oid` is stable across the directory's apps.
- Google's `sub` is stable per account; `email_verified` and, for Workspace accounts,
  `hd` describe the email, not who holds the account.
- Linking a sign-in to an existing account by matching email lets anyone who controls
  an email claim, or who registers an address first, take over or pre-hijack the
  account. ADR-015 Option 11 already forbids merging by email; this applies the same
  rule to invitations and to every lookup.

### F3 — Tokens held in the browser are the weakest place to keep a credential

RFC 10017 ranks a backend-for-frontend (BFF), where a server-side component runs the
OAuth flow and the browser holds only an `HttpOnly` session cookie, as the most secure
of its patterns; a browser that holds tokens exposes them to any script that runs on
the page. The identity SDKs persist tokens by default (MSAL in session or local
storage, Firebase's refresh token in IndexedDB), which on a shared NHS workstation
leaves a credential on disk after the tab closes: the reason ADR-015 round 4 rejected
browser storage for unpublished content. ADR-016 already requires tokens in memory
only.

### F4 — The editor's origin is shared until it has its own domain

On GitHub Pages the editor shares an origin with every organisation site, including the
public site, which loads a third-party analytics script (ADR-016 _Consequences_). A
cookie, a CSP or a storage partition cannot tell them apart. ADR-016 makes a custom
domain for the editor a precondition of switching it to the API; GitHub Pages also
cannot set response headers, so the editor's CSP, HSTS and framing rules need a host
that can (EPC-023).

### F5 — Without passwords, the application has little to brute-force

If the API holds no passwords, codes or recovery secrets, the identity provider owns
brute-force protection, lockout, MFA and credential recovery. What is left to the
application: the sign-in callback (bound to a single-use state value), invitation
redemption (a high-entropy token), and abuse of authenticated writes and of the open
public read. Each identity provider an application runs itself (passwords, TOTP,
recovery codes, passkeys, email codes, step-up) is a large, error-prone surface: hashing
parameters, per-account throttles across challenges, recovery code entropy, key
rotation for stored secrets, enumeration through timing.

### F6 — A permission carried in a token outlives its revocation

A signed access token that carries roles or permissions keeps granting them until it
expires, so removing a member or a role takes effect only then, unless every request
re-reads them. At this scale (a handful of editors per tenant) one indexed read per
request of the session, the membership and its roles costs nothing, and ADR-015 needs
the person and tenant per transaction anyway (ADR-017 _Tenant and person_).

### F7 — Who enforces MFA differs by provider

- **Entra:** DHCW administers the NHS Wales directory, so Conditional Access can
  require MFA (phishing-resistant for admins) for this app, and the app registration can
  require assignment, so only an assigned group can sign in at all. The token reports
  the methods used (`amr`, or an authentication context in `acrs`); which claim a v2.0
  ID token carries for this registration needs confirming in a spike.
- **Google:** a Workspace organisation can enforce 2-Step Verification. Google's ID
  token reports the time and method of a sign-in (`auth_time`, `amr`) only through its
  security bundle, for published, verified apps that enable it, and Google offers no
  documented way to force a fresh sign-in. A consumer account enforces nothing the app
  can see. DHCW has a Google Workspace, which today's editor's Google sign-in
  uses (owner, 2026-11-21).

### F8 — Sheets sign-in stays as it is until the switch-over

ADR-003's popup token model asks for the spreadsheets scope and never learns who the
user is. It stays for the Sheets adapter until the deployed editor switches to the API.
The API's sign-in is separate: it needs identity only (`openid email profile`) and no
Google API scope.

### F9 — The repository's security checks cover code style more than supply chain

The repository is public. Present or decided: ESLint, Dependabot for Actions (ADR-016
adds pnpm and uv), actionlint and zizmor (ADR-016), ruff with its security (`S`) and
banned-API rules (ADR-017), SHA-pinned actions and `contents: read` workflow
permissions; secret scanning is on. Absent: push protection, a vulnerability audit of
the lockfiles,
static analysis beyond lint (CodeQL is free for public repositories), dependency review
on pull requests, a release cooldown on new package versions, container image scanning
and an SBOM.

## Options

### Where the session lives

| Option                                                                                                              | For                                                                                                                                                                                                     | Against                                                                                                                                                                                                                |
| ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **A. The API is the OIDC client (BFF); an opaque server-side session in PostgreSQL behind an `HttpOnly` cookie** ✅ | No token in the browser (F3); revocation on the next request (F6); one cookie whatever the provider; no signing keys to rotate; the session row gives ADR-015 its person; RFC 10017's strongest pattern | Needs the editor and API on one site (F4); a database read per request (trivial at this scale); CSRF must be handled (below)                                                                                           |
| B. The editor holds the provider's tokens (MSAL, GIS) and sends them as bearer tokens                               | No sign-in code in the API                                                                                                                                                                              | Tokens in script reach (F3); two token formats to validate; a Google ID token is not meant as an API access token; revocation only at expiry                                                                           |
| C. The API mints its own access JWT and a rotating refresh token, in cookies                                        | Stateless reads; a familiar pattern                                                                                                                                                                     | Permissions stale until expiry (F6); signing keys to hold and rotate; refresh-token families, reuse detection and absolute caps to build; no second service consumes the token                                         |
| D. An identity broker (Firebase Auth / Identity Platform, Auth0, Entra External ID)                                 | One token format for many providers; hosted sign-in screens                                                                                                                                             | A third party in every sign-in; its SDK persists tokens in the browser by default (F3); the broker's user ID hides the provider's subject (F2); NHS Wales SSO goes direct to Entra anyway                              |
| E. Google Cloud IAP in front of the editor and API                                                                  | Sign-in held by infrastructure                                                                                                                                                                          | Ties identity to one cloud; does not run locally or in CI; external providers need Identity Platform (D); the public read must bypass it. Worth having for operator-only surfaces (EPC-023), not as the app's identity |

### How an invitation is redeemed (ADR-015 Option 12)

| Option                                                                                                                                                  | For                                                                    | Against                                                                            |
| ------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| **A. A single-use invitation link, and the redeeming sign-in's verified email must match the invited address, from a provider authoritative for it** ✅ | A leaked link alone admits nobody; a spoofed email alone admits nobody | The admin delivers the link (copied, or by email once the API sends it)            |
| B. The invited address alone: the first sign-in whose verified email matches is admitted                                                                | No link to deliver                                                     | Access rests on an email claim (F2); safe only where the provider is authoritative |
| C. The link alone (a bearer invitation)                                                                                                                 | Simplest                                                               | Whoever holds the link gets in; a forwarded email admits the wrong person          |

### Which Google accounts may sign in (F7)

| Option                                                                                           | For                                                                              | Against                                                                    |
| ------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| A. Workspace accounts of named domains only (`hd` allow-list, an Internal client where possible) | The organisation enforces 2-Step Verification and offboarding                    | Excludes anyone on a consumer account; needs DHCW's Google setup confirmed |
| B. Any Google account holding an invitation                                                      | Today's reach                                                                    | No MFA or offboarding the app can rely on                                  |
| C. Google until Entra lands, then retired for NHS Wales staff, kept for a tenant without Entra   | Moves staff to the directory DHCW controls; keeps Google where nothing else fits | A second migration of people's identities (linking makes it one sign-in)   |

## Recommendation

### Signing in

1. **The API is a confidential OpenID Connect client** (Option A): authorisation code
   with PKCE (`S256`), `state` and `nonce`, by a top-level redirect, never a popup. The
   browser never sees a provider token; the API keeps none after sign-in, since it
   calls no provider API.
2. **Providers are a fixed allow-list of exact issuers:** Google
   (`https://accounts.google.com`), and later the NHS Wales directory only, as a
   single-tenant app registration (`https://login.microsoftonline.com/{nhs-wales-tid}/v2.0`),
   never the `common` or `organizations` endpoints. Another provider or directory is an
   ADR amendment.
3. **ID tokens are validated in full** by a maintained library (Authlib, or joserfc for
   JOSE alone; not python-jose, which is unmaintained, and no hand-rolled parsing):
   signature against the provider's cached JWKS, an algorithm allow-list (`RS256`),
   exact `iss`, `aud` equal to our client ID, `exp` and `iat` within a minute's skew,
   `nonce`, and `azp` where present.
4. **Client authentication without a long-lived secret where the provider allows it:**
   Entra by a federated credential trusting the API's Google service account, or a
   certificate (to confirm in the Entra spike); Google by its client secret, held in
   Secret Manager and rotated.
5. **An identity is `(issuer, subject)`**: Google's `sub`; Entra's `oid` under the
   directory's issuer. Email, UPN and name are display attributes refreshed at each
   sign-in, with their verification state; no lookup, link or grant keys on them (F2).
   This refines ADR-015 Option 11's "provider and subject".
6. **The sign-in transaction is server-side:** the start endpoint stores the state,
   nonce, PKCE verifier and a return path checked against an allow-list (no open
   redirect), for ten minutes, behind a `__Host-` cookie with `SameSite=Lax` (the
   provider's redirect back is a cross-site navigation). A callback whose state does not
   match, or is reused or expired, is refused, which also defeats login CSRF.
7. **MFA belongs to the provider.** The API holds no passwords, TOTP secrets, recovery
   codes or passkeys (F5). For Entra: Conditional Access requires MFA for this app,
   assignment is required, and the API refuses a token without an MFA method. Google per
   the owner's choice (Decision D4).
8. **Local development and tests run the same code path** against a mock OIDC provider
   in Compose; there is no development-only sign-in route to leak into production.

### Sessions

9. **An opaque session row in PostgreSQL**: a 256-bit random ID in the cookie, only its
   SHA-256 hash stored, with the person, the provider and methods of the sign-in, its
   time (`auth_time`), the active tenant, last activity, an idle and an absolute expiry,
   and revocation. Found by hash through a definer function, as ADR-015's sign-in lookup
   is.
10. **The cookie is `__Host-`, `Secure`, `HttpOnly`, `SameSite=Strict`, `Path=/`, with
    no expiry attribute**, so it ends with the browser, as a shared workstation needs. A
    link followed from Teams or email loads the static page without it; the page's own
    same-origin calls then carry it.
11. **Lifetimes: idle and absolute, both enforced on the server** (ASVS 7.3); proposed 60
    minutes idle and 10 hours absolute (Decision D7). Expiry loses nothing: unpublished
    edits live in the server scratch (ADR-015 Option 3), and signing in again is one
    click while the provider's own session lasts.
12. **The session ID is replaced at sign-in, at linking an identity and at switching
    tenant**; sign-out revokes the row and expires the cookie (`Clear-Site-Data:
"cookies"` would clear every site on the registrable domain); "sign out everywhere"
    revokes every session of the person.
13. **Every request re-reads the session, the membership and its roles** (F6), sets the
    tenant and person per transaction (ADR-017), and checks the person is not disabled.
    Removing a member, a role or a person takes effect on the next request.
14. **The active tenant is held in the session**, chosen at sign-in (most people have
    one) and switched by a request that replaces the session ID; paths carry no tenant
    ID, so no route can forget to compare a path's tenant with the session's.

### Access, linking and leaving

15. **Invitations** (Option A above): a 256-bit single-use token, hashed at rest,
    expiring after seven days, naming the tenant, the invited address and the roles;
    redeemed by a signed-in person whose verified email matches, from an authoritative
    provider (the NHS Wales directory, or Google per D4). A redeemed, revoked or expired
    invitation is refused with one code.
16. **A second identity is linked only by the person**, signed in, completing a fresh
    sign-in with the other provider in the same browser. An admin may remove an
    identity, never attach one: people are shared across tenants (ADR-015), so a tenant
    admin attaching an identity could take over a person's access to another tenant.
    This narrows ADR-015 Option 11's "or by an admin" (Decision D6). The last identity
    cannot be removed.
17. **A tenant always keeps one admin:** the last admin's role cannot be removed or
    their membership ended, checked under the access scope's lock.
18. **A person can be disabled** by a platform procedure: sign-in refused, sessions
    revoked. Leavers are disabled in Entra, which stops new sign-ins; the absolute
    lifetime bounds an open session. Provisioning from Entra by SCIM is a later
    integration (EPC-023).

### Authorisation

19. **The permission catalogue is a typed enumeration in code;** a tenant's roles name
    permissions, validated against the catalogue on write and at start-up. An unknown
    name fails closed and is logged, never silently ignored.
20. **Every route declares exactly one policy**: public, signed in (a person, no tenant)
    or a named permission. A custom route class refuses to register a route without one,
    so a route without a policy fails at import, and the default is deny.
21. **Object-level checks live in services:** editing needs an assignment to the roadmap
    or the admin role (ADR-015 Options 13, 23); row-level security isolates tenants
    beneath the repositories' own tenant filter; an ID from another tenant answers 404,
    not 403, so existence does not leak.
22. **Step-up for access changes and redaction:** granting roles, inviting, removing
    members and redacting need a sign-in within the last 15 minutes, renewed by sending
    the person back to the provider with `max_age` and checking `auth_time` (provider
    support to confirm in the spikes; Decision D8).
23. **Platform operators have no web surface and no impersonation.** Creating a tenant,
    its first admin, disabling a person and redaction escalations are CLI commands run
    as Cloud Run jobs that only named Google Cloud principals may invoke; the platform
    audit log records the verified principal, not a name typed on the command line.
    Support works from what the person sees, shared by them. An operator holds no tenant
    access unless invited like anyone else.

### Logging

24. **Security events are recorded** in an append-only shared table (ADR-015's platform
    audit log, widened): sign-in succeeded or refused (with its code), signed out,
    session revoked, identity linked or removed, invitation created, redeemed or
    revoked, step-up, person disabled, and refusals by policy. Access changes are already
    change sets. The application's role cannot update, delete or truncate the table.
25. **Logs carry IDs, never tokens, cookies, codes or ID tokens**; email addresses are
    not logged; redaction is by allow-list of fields, not by a deny-list of key names.
    Events also go to stdout as structured JSON, for the alerting EPC-023 sets up.

### Rate limiting and HTTP hardening

26. **The application limits what only it can key:** writes per person (a generous
    ceiling against a runaway client or a stolen session), and sign-in callback and
    invitation failures per client, counted in PostgreSQL (no Redis at this scale,
    correct across instances). A limit answers 429 with `Retry-After` and an error code:
    with no passwords there is nothing to hide behind a disguised refusal.
27. **The client address is read from `X-Forwarded-For` only behind the known load
    balancer**, taking the entry it appends, by a configured count of trusted hops;
    never trusted by default.
28. **Per-address limits, the public read's caching and WAF rules belong to the edge**
    (EPC-023).
29. **The editor and the API share one origin** on the editor's custom domain, the load
    balancer routing `/api/` to the API: no credentialed CORS at all, which replaces
    ADR-017's allow-list for the editor's endpoints. **The public read has its own
    host**, open CORS and no cookies (ADR-017), and its routes never read a session.
30. **Unsafe methods need same-origin proof:** `Sec-Fetch-Site: same-origin`, or an
    `Origin` equal to ours where Fetch Metadata is absent, else refused; bodies must be
    `application/json`. With `SameSite=Strict`, that is OWASP's current CSRF defence
    without a token.
31. **API responses** carry `Cache-Control: no-store` when signed in, `nosniff`,
    `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'` and a
    same-origin resource policy; a body size limit; a host allow-list; validation errors
    in ADR-017's envelope without echoing the submitted input; `/docs` and the live
    OpenAPI route off in production (the committed document serves).

### Checks that prove it

32. **Tests:**
    - every route has a policy, and the public routes are a reviewed list in code;
    - a role-by-route matrix generated from the catalogue: each shipped role, a member
      with no roles, a non-member and an anonymous caller, against every route's
      expected answer;
    - a cross-tenant sweep: every tenant route called with another tenant's IDs answers
      404 and changes nothing;
    - an unassigned lead is refused every edit route;
    - every table has row-level security enabled and forced, with a policy; the
      application's role does not bypass it, owns nothing and cannot alter the security
      events;
    - the cookie's attributes, the response headers, a cross-site write refused, a
      replayed or expired state refused, a session refused after its idle and its
      absolute expiry, and after a member or role is removed;
    - ID token validation refuses each bad claim, algorithm and signature.
33. **Lint:** ruff's `S` rules (ADR-017), plus banned APIs: python-jose and
    `jwt.decode` outside the identity module, `random` for secrets, requests without a
    timeout. import-linter: only the identity module imports the OIDC library; only the
    session service writes sessions.
34. **Supply chain**, in CI on every pull request (a chore beside STY-087): GitHub
    secret scanning with push protection; CodeQL for Python and TypeScript; dependency
    review; an OSV audit of `pnpm-lock.yaml` and `uv.lock`; a release cooldown for new
    package versions (pnpm `minimumReleaseAge`, uv `exclude-newer`; exact settings to
    confirm); zizmor with every audit on. Image scanning and an SBOM arrive with the
    first container build (EPC-023).
35. **A threat model of the sign-in, session and invitation flows**, written before the
    first identity story and kept with the identity ADR; a penetration test before the
    deployed editor switches to the API.

### The editor

36. **`AuthClient` keeps its shape and loses its token** for the API data source:
    `connect()` navigates to the API's sign-in start, still synchronously in the click
    (ADR-003); the state comes from a "who am I" call; a 401 moves to `expired` and
    "Sign in again". Permissions shown in the interface are hints; the API decides. The
    Sheets adapter keeps ADR-003 until the switch-over.
37. **The editor's document headers come from its host** (EPC-023): a strict CSP with
    Trusted Types (trialled report-only first), HSTS (preload only on a registrable
    domain of the editor's own), `frame-ancestors 'none'`, a cross-origin opener
    policy and a referrer policy. The editor needs no inline script for this, and
    loses the Google script once the Sheets adapter retires.

### Rejected

- **Passwords, TOTP, recovery codes and passkeys run by the API:** the providers do
  this better, and each is a surface to get wrong (F5).
- **Linking or admitting by email alone** (F2).
- **Access tokens with embedded permissions** (F6), and refresh tokens in the browser.
- **An identity broker** and **IAP as the app's identity** (Options D, E).
- **Impersonation**, even read-only: a support convenience that breaks attribution and
  need-to-know, for a handful of editors who can share their screen.
- **A web admin surface for platform operators:** a public route to the most privileged
  actions, for a few tasks a CLI job does.
- **A development sign-in bypass:** a mock provider serves the same path.

## Decisions needed

| #   | Decision                                                                                              | Recommendation                                                      | Goes to               |
| --- | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- | --------------------- |
| D1  | Where the session lives                                                                               | Option A: the API as OIDC client, opaque PostgreSQL sessions (1–14) | Identity ADR          |
| D2  | One origin for the editor and API on a custom domain; the public read on its own host                 | Yes (29); a precondition of switching, with ADR-016                 | Identity ADR, EPC-023 |
| D3  | Entra: single-tenant NHS Wales registration, `tid`+`oid`, Conditional Access MFA, assignment required | Yes (2, 5, 7)                                                       | Identity ADR          |
| D4  | Which Google accounts may sign in, and Google's future once Entra lands                               | Owner's choice; A if DHCW uses Workspace, else C                    | Identity ADR          |
| D5  | How an invitation is redeemed, and whether the API sends email                                        | Option A (15); the link copied by the admin until email exists      | Identity ADR          |
| D6  | Who links identities: the person only; admins only remove                                             | Yes (16): amends ADR-015 Option 11                                  | Identity ADR, ADR-015 |
| D7  | Session lifetimes                                                                                     | 60 minutes idle, 10 hours absolute, ends with the browser (10, 11)  | Identity ADR          |
| D8  | Step-up for access changes and redaction                                                              | A sign-in within 15 minutes (22)                                    | Authorisation ADR     |
| D9  | Signing out of the app also signs out of the provider                                                 | No: the app only; signing out of NHS Wales Microsoft 365 surprises  | Identity ADR          |
| D10 | Platform operators: CLI jobs under cloud IAM, no web surface, no impersonation                        | Yes (23)                                                            | Authorisation ADR     |
| D11 | Route policies, the last-admin rule, disabling a person, and the test suite                           | Yes (17–21, 32)                                                     | Authorisation ADR     |
| D12 | New shared tables: sessions, sign-in transactions, security events                                    | Yes, each with RLS (9, 24): amends ADR-015 _Tenancy_                | Identity ADR, ADR-015 |
| D13 | Rate limiting split between the application and the edge                                              | Yes (26–28)                                                         | Identity ADR, EPC-023 |
| D14 | Supply-chain checks                                                                                   | Yes (34), as a chore                                                | A chore               |
| D15 | An infrastructure epic holding the protections that live outside the code                             | EPC-023, a placeholder                                              | EPC-023               |

## Outcome

The owner answered the decisions in the grilling of 2026-11-21, after an independent
review of this analysis, and answered the questions its drafts' review raised. The
answers are three ADRs, accepted by the owner on 2026-11-21:

- [ADR-018](../adr/ADR-018-sign-in-through-the-api-with-a-server-side-session.md),
  identity: D1, D3–D9, D12;
- [ADR-019](../adr/ADR-019-the-api-authorises-every-route-from-a-permission-catalogue-in-code.md),
  authorisation: D10, D11, and the permission catalogue and roles;
- [ADR-020](../adr/ADR-020-the-editor-and-the-api-share-one-origin.md), origins and the
  API's HTTP hardening: D2, D13.

D14 is [CHO-031](../backlog/chores/CHO-031-supply-chain-checks-on-every-pull-request.md);
D15 is [EPC-023](../backlog/EPC-023-hosting-and-infrastructure-security/README.md).
D8 (step-up) went to the identity ADR, not the authorisation ADR the table names; D2
and D13 went to ADR-020, split from the identity ADR.

Where the ADRs depart from the Recommendation above:

- **The tenant is named by every request**, not held in the session (14): a switch in
  one tab would silently retarget another.
- **A person record is created only when an invitation is redeemed** (15, 20): a sign-in
  with neither is refused and writes nothing. Asking for access is a later story
  (STY-094). A tenant's first and replacement admins are invited by a platform job, so
  there is no second way in.
- **The invitation token travels in a URL fragment**, posted by the editor, so it
  reaches no request log; redemption is atomic, and void once the inviter has lost
  `members:manage`. Invitations are access change sets.
- **No MFA requirement in the API** (7): the owner relies on each provider's own policy
  for now. **Entra admits any valid NHS Wales directory user**, with no app-specific
  Conditional Access or group assignment (D3, answered in the review): the invitation is
  the gate.
- **No step-up on Google** (22), which offers no documented way to force a fresh sign-in
  (F7); an Entra authentication context later.
- **Identities** (16): a tenant admin neither attaches nor removes one; the person or a
  platform operator removes one. A sign-in's purpose (sign in, link, redeem) is bound to
  its transaction, since the `Strict` session cookie does not arrive with the provider's
  redirect. Production may start on Google; then each person links Entra and signs in
  with Entra only, and Google stops for everyone on an announced date.
- **Signing out** (12) asks Google for its account picker and Entra for a fresh sign-in;
  on Google the last person's account stays one click away on a shared desk, an accepted
  risk. "Expiry loses nothing" (11) held only for saved edits: signing in again opens a
  new tab, and the original tab keeps its form only for the same person.
- **Security events go to the structured log**, exported by EPC-023, not to a database
  table (24, D12); the platform audit log stays append-only; step-up and refusals by
  policy are not separate events.
- **Platform jobs** (23) are one command each, under their own service account and
  database role; the principal comes from Cloud Run's Data Access audit logs, joined by
  execution ID.
- **Rate limits live at the edge** (26): the API counts nothing in PostgreSQL; the
  sign-in transaction table is the one write anonymous traffic can cause.
- **Origins and hardening are their own ADR** (29–31, ADR-020); before a custom domain,
  one Cloud Run service serves the editor and the API, routed by host from the public
  read.
- **`AuthClient` is reshaped** (36), losing its token, rather than keeping its shape.
- **The server's timeouts end a session** (D7, 10): the cookie still has no expiry
  attribute, but a browser that restores sessions keeps it, so it does not end with the
  browser.
- **Linking is guarded** against a session someone else is using: one identity per
  issuer, Entra only, from a session under ten minutes old, revoking the person's other
  sessions, with removal barred for seven days.
- **SCIM is dropped** (18): group assignment is not used, and the access review keeps
  memberships current.
- **Sign-in hardening added**: a callback per provider bound to its issuer, against
  mix-up; JWKS refetched on an unknown key and failing closed; the mock provider refused
  on Cloud Run.
- **The permission catalogue** gains `roadmaps:edit`, `roadmaps:edit-any` and
  `roadmaps:publish`, a Viewer role, and the shipped roles only until a tenant needs to
  edit them; co-leads are Product Leads.
