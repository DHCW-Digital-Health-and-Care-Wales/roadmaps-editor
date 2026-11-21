---
name: threat-review
description: >-
  Security review of a diff, branch or PR, code or design record: threats, trust
  boundaries, sign-in, sessions, tokens, authorisation, tenant isolation, untrusted
  input, secrets, CI and infrastructure-held protections. Use beside code-review and
  quality-review on a security-relevant PR; correctness belongs to code-review.
user-invocable: true
---

# Threat review

Judge whether the change keeps every asset safe from every actor who can reach it,
and whether each security claim it makes is true. `code-review` owns requirements and
regressions, `quality-review` maintainability; this review owns the attacker's view,
under its own verdict. It runs as the security lane that
`.agents/skills/implement-story/references/delegation.md` sets: on Fable 5.2 at high
effort (`.claude/agents/security-reviewer.md`), concurrently with the others.

Invoke as `/threat-review [target]`, with targets as `code-review` takes them. Report
in the conversation only: do not post, change code or files, merge, contact anyone, or
probe a real service, account or secret.

## Working order

1. **Pin the scope** as `code-review`'s step 1 does, and read every changed line,
   docs included.
2. **Model the change's threats.** From the diff and the records it cites, write down,
   briefly, before judging:
   - **Assets** it touches: a session, a token or ID token, an invitation, a person's
     identity, a tenant's drafts and scratch (unpublished), a published roadmap's
     integrity, staff names and emails, a secret, CI's cloud identity.
   - **Actors** who can reach them: anyone on the internet; a person in the NHS Wales
     directory or DHCW's Workspace who is not a member; a Viewer; a Product Lead not
     assigned to the roadmap; an admin of another tenant; whoever sits at a shared
     workstation left signed in; someone holding a stolen cookie or a forwarded link;
     a platform operator; a compromised dependency, action or workflow.
   - **Boundaries** it crosses: browser and API, API and provider (OIDC), API and
     database (row-level security, definer functions), the public read, CI and the
     cloud, the edge and the service.
3. **Read the binding security decisions** the change reaches, from `docs/adr/` (index
   in its `README.md`): today's Sheets token (ADR-003), the database's isolation and
   history (ADR-015), the repository's ruleset (ADR-016), the API stack (ADR-017), sign-in
   and sessions (ADR-018), authorisation (ADR-019), origins and HTTP hardening
   (ADR-020); infrastructure-held protections in
   `docs/backlog/EPC-023-hosting-and-infrastructure-security/README.md`; the root
   `AGENTS.md` rules on tokens and untrusted data. Each ADR's _Accepted risks_ are the
   owner's: not findings unless the change widens them.
4. **Apply the lenses**: every general lens, then each area lens the change reaches.
   For each asset and actor, show the control that stops the actor, or report its
   absence.
5. **Verify each finding** as an attack path: the actor, where they enter, each step,
   and what they gain. Check every claim about a protocol, provider or platform
   (OAuth, OIDC, Google, Entra, browsers, PostgreSQL, Cloud Run, GitHub Actions) against
   its primary documentation, cite it, and state your confidence when you cannot. A
   focused test or reproduction may run with its outputs under `/tmp`, as `code-review`
   step 5 allows.
6. **Filter.** Report what the change introduces, exposes or claims wrongly, tied to a
   changed line or an affected boundary. Drop theoretical attacks with no actor who
   can reach them. List a correctness or maintainability point, or an existing
   unrelated weakness, under _Handed off_.

## General lenses

- **Every path to a protected asset.** For each asset, enumerate every route, job,
  function, file and log that can read or change it, and show each one's control:
  each route's declared policy (ADR-019), each definer function's grant, each place a
  token or identifier is written.
- **Fail closed.** A missing setting, an unknown permission, an absent tenant, an
  unreachable key set or a parse failure refuses rather than allows; a default is the
  production rule (ADR-017).
- **Secrets and personal data.** No secret, token, code, cookie or email in source,
  config, a URL, browser storage, a log, an error, a test fixture or the PR; personal
  data minimised and its retention stated (ADR-018).
- **Abuse and availability.** What an anonymous caller can make the service write,
  compute or send; what limits it (the edge, ADR-020); what a provider outage stops.
- **Proportionality.** A control's cost against this tool's scale (a handful of editors
  per tenant): a cheaper control with the same assurance is a finding; a missing
  expensive one with no realistic actor is not.

## Area lenses

- **Sign-in and sessions** (ADR-018): the sign-in transaction's binding (state, nonce,
  PKCE, issuer, purpose) and the one state-changing `GET`; ID token validation and key
  rollover; the identity key never an email; invitation tokens out of URLs that are
  logged, hashed, single-use and atomic; linking guarded against a session someone
  else holds; cookie attributes, session replacement, idle and absolute expiry,
  revocation on the next request; the mock provider unreachable in a deployed
  environment.
- **Authorisation and tenancy** (ADR-015, ADR-019): every route declares a policy and
  the default is deny; the request's tenant checked against membership; object checks
  (assignment, retired); another tenant's IDs answer 404; row-level security forced,
  settings per transaction, definer functions narrow and owned by a role without DDL;
  platform jobs one command each, with their principal recorded.
- **The browser** (ADR-020, ADR-003): same-origin proof on every write; no
  credentialed CORS; no HTML built from untrusted text; CSP and framing; redirects
  only to an allow-list; while the Sheets adapter lives, the Google token in memory
  only.
- **Untrusted input**: parsed at the boundary (Zod in the editor, Pydantic in the API);
  SQL only through bound parameters; sizes and counts bounded; patterns safe from
  catastrophic backtracking.
- **CI and supply chain** (ADR-016, CHO-031): workflow permissions, triggers that run
  untrusted code (`pull_request_target`, `workflow_run`), actions pinned by SHA, cloud
  identity conditioned on repository, ref and environment; a new dependency's
  maintenance, provenance and release age.
- **Infrastructure** (EPC-023): least-privilege IAM, no service account keys, private
  database, logs that record who did what and who may read them, no real data outside
  production.
- **A design record** (an ADR, epic, analysis or story that records a security
  decision): every actor and boundary in step 2 has a stated control or a named,
  owner-accepted residual risk; every technical claim is verified (step 5); the
  record's own rules do not contradict one another or an accepted ADR.

## Grading

| Priority | Meaning                                                                                                                                 |
| -------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| P0       | Exploitable now by an anonymous or other-tenant actor: a leaked secret or token, an authentication bypass, a cross-tenant read or write |
| P1       | A signed-in actor gains beyond their role, or a control the design relies on is missing or cannot work as written                       |
| P2       | A defence-in-depth gap with a plausible actor, or a security claim in code or a record that is wrong                                    |
| P3       | Hardening, an unstated residual risk, or a disproportionate control                                                                     |

Choose priority from what the actor gains and how easily they reach it. No quota:
return no findings when none is established.

## Report format

```text
Threat review — <target>
Scope: <base/head SHAs, diff command>
Threat model: <assets, actors, boundaries the change reaches, in a few lines>
Verdict: <security assessment and verification limits>

Findings
- [P#] <title> — path:line
  Actor and path: <who, where they enter, each step, what they gain>
  Control: <the control that is missing, wrong or unverified; the record or ADR it breaks>
  Evidence: <code trace, primary source with link, or check run; confidence>
  Fix: <smallest control that closes it, and the test or record that proves it>

Verification: <sources and checks actually used; what could not be verified>
Handed off: <correctness or quality points, existing weaknesses; or None>
```

When re-reviewing, state whether each earlier finding is fixed, partly fixed or still
open, then review the changed scope.
