# EPC-022: Monorepo and backend foundation — an API and its database beside the Sheets editor

- **Status**: Active — every binding ADR is accepted (owner, 2026-11-21); the
  placeholders' acceptance criteria, then the schema, identity and endpoint stories, are
  written next
- **Progress**: 0 of 10 terminal; next selectable: none; blocked on: STY-085's acceptance
  criteria
- **Binding ADRs**: ADR-015, ADR-016, ADR-017, ADR-018, ADR-019, ADR-020, ADR-002

## Summary

The editor reads and writes one Google spreadsheet, a temporary data source (ADR-002).
This epic makes the repository a monorepo, renamed `roadmaps`, that also takes in the
public site, and establishes the backend that will replace the spreadsheet: a Python
FastAPI service over the PostgreSQL 18 database ADR-015 designs, scoped by tenant,
keeping every version, with private scratch, shared drafts, publications, people, roles
and assignments. Google Sheets stays the deployed data source throughout, so Product
Leads see no change beyond the editor's new address; the API is developed, tested and run locally beside it,
and the editor can be built against either data source, as the composition root
chooses (ADR-002). The editor's new editing model (scratch, draft, permissions), the
switch of the deployed editor to the API, and the infrastructure as code for its
environments are later epics.

## Owner decisions waiting

None. ADR-016 to ADR-020 were accepted on 2026-11-21.

## Findings

Greenfield for the backend; the precedent is the editor's own seams, audited at
`93b12d4` on 2026-11-20:

- `RoadmapRepository` (`src/domain/roadmap/roadmap-repository.ts`) is the editor's only
  view of its data, and `composeApp` (`src/app/composition.ts`) the only place that
  picks an adapter, so a second adapter needs no change to features.
- The shared contract suite (`src/domain/roadmap/testing/`) is the parity check an API
  adapter runs.
- `docs/operations/replacing-google-sheets.md` is the runbook for the adapter.
- Today's repository has no call for a scratch, a draft, a discard, people, roles or
  assignments: the adapter maps today's calls onto the API, and the new calls arrive
  with the editor's new editing model.

For the repository and the public site, audited at `5d8c58d` (this repository) and
`2548219` (`product-roadmaps`) on 2026-11-21:

- The public site is a static Vite site prerendered from a snapshot of the spreadsheet,
  on npm and Node 24, published nightly and on a push to Pages at `/product-roadmaps/`.
  It parses the format the editor writes with its own parser, and the editor copies its
  fixture CSVs (`tests/fixtures/sheets/README.md`).
- GitHub Pages serves one site per repository, and `deploy-pages` publishes only to its
  own repository; every organisation site shares one origin.
- This repository's `main` is unprotected and allows only squash and rebase merges;
  `product-roadmaps` requires code-owner review on `main`.
- `product-roadmaps`' ruleset allows only squash and rebase merges, so the public site's
  history merge needs it widened for one pull request, or the owner's bypass.
- The `postgres:18` image keeps its data under `/var/lib/postgresql/18/docker` and
  refuses a mount at the old `/var/lib/postgresql/data`.
- ty, evaluated on 2026-11-21 (0.0.107 on Python 3.15.0, with SQLAlchemy 2.1.9, FastAPI
  and Pydantic), reported no false positives and the same errors as mypy strict on a
  sample of typed models, `select()` tuples, a session listener and a route.

## Design

Owner answers of 2026-11-20 (ADR-015 grilling, rounds 1–7):

1. **Layout**: `apps/editor` (today's app, moved), `apps/public-site`, `apps/api` and
   `packages/api-types` (ADR-016, amended 2026-11-21 from `apps/editor` and `apps/api`).
   The move is one mechanical change, with docs, skills, configs, worktree scripts and
   CI paths updated together, chosen over keeping the editor at the root; the rename
   comes before it.
2. **The editor's API adapter and a build-time data source switch are in this epic**,
   running the shared contract suite against the API; Sheets stays the deployed source.
3. **The database is ADR-015**, delivered with its enforcement suite (ADR-015 _What
   enforces this_).
4. **Live presence and real-time updates are out of scope**; saves and conflicts carry
   correctness.
5. **The adapter publishes through the scratch**: a scratch write, then "save and
   publish" (ADR-015 Option 28), so the scratch is exercised from the first delivery.
6. **Scratch expiry**: after 30 days without activity, with a warning at 23 (ADR-015
   Option 24), run by a scheduled API job (Option 29).

Owner answers of 2026-11-21 (monorepo grilling), drafted into ADR-016 and ADR-017:

7. **The public site joins now** (ADR-016 _The public site_), and `product-roadmaps`
   keeps publishing it, nightly and by hand, from this repository's `main` head.
8. **The repository is renamed `roadmaps` first**, on its own; the old editor address
   gets no redirect, and leads are told the new one.
9. **`main` is protected** by `product-roadmaps`' ruleset, applied repository-wide, with
   required checks and signed commits; the owner keeps bypass.
10. **Workspace tooling, CI and agent guides**: ADR-016 _Workspace tooling_, _CI_,
    _Agent guides_.
11. **The API stack**: ADR-017, including the public read (no key, open CORS, OGL v3.0,
    current publications only) and the seeder, which starts right after the migrations.

Owner answers of 2026-11-21 (identity and authorisation grilling, and the review of
its drafts), from the
[identity and authorisation analysis](../../analysis/identity-and-authorisation.md):

12. **Sign-in**: through the API, with DHCW's Google Workspace first and Entra next,
    after which Google is retired; an opaque server-side session; a person exists only
    once an invitation is redeemed (ADR-018); asking for access later (STY-094).
13. **Authorisation**: a permission catalogue in code, Admin, Product Lead and Viewer,
    every route declaring a policy, every request naming its tenant (ADR-019).
14. **Origins**: the editor and the API on one origin in every environment, the public
    read on its own host (ADR-020).
15. **Supply-chain checks**: CHO-031, beside STY-087.
16. **Infrastructure-held protections**: EPC-023, a placeholder.

_The schema, identity and endpoint stories are written next, from ADR-015 and ADR-018 to
ADR-020._

## Shared assumptions and contracts

### Workspace commands

Root scripts delegate to an app with `pnpm --filter <app>`; the API's run through uv
from its own directory. A story that adds a command adds its root script.

### The API's conventions

Every API story follows ADR-017's layering, error envelope and test harness. A story
that adds an error code maps it in the editor's API adapter (ADR-017 _Errors_), with
copy in English and Welsh when it needs a new `AppError` kind, and adds factories to
the seeder for any table it creates.

## Stories

| ID      | Story                                                                                               | Area                   | Depends on  | State |
| ------- | --------------------------------------------------------------------------------------------------- | ---------------------- | ----------- | ----- |
| STY-085 | [Rename the repository to roadmaps](STY-085-rename-the-repository-to-roadmaps.md)                   | CI/CD + Docs           | —           |       |
| STY-086 | [Move the editor into apps/editor](STY-086-move-the-editor-into-a-pnpm-workspace.md)                | CI/CD + Docs           | STY-085     |       |
| STY-087 | [Workspace tooling and the ruleset](STY-087-workspace-tooling-and-the-main-ruleset.md)              | CI/CD                  | STY-086     |       |
| STY-088 | [Bring the public site in](STY-088-bring-the-public-site-into-the-workspace.md)                     | CI/CD + Docs           | STY-087     |       |
| STY-089 | [One copy of the spreadsheet fixtures](STY-089-one-copy-of-the-spreadsheet-fixtures.md)             | Infrastructure + CI/CD | STY-088     |       |
| STY-090 | [The API skeleton](STY-090-the-api-skeleton.md)                                                     | API + CI/CD            | STY-086     |       |
| STY-091 | [Migrations, tenant listener, test harness](STY-091-migrations-tenant-listener-and-test-harness.md) | API                    | STY-090     |       |
| STY-092 | [The OpenAPI contract and schemas](STY-092-the-openapi-contract-and-generated-schemas.md)           | API + Infrastructure   | STY-090     |       |
| STY-093 | [A deterministic seeder](STY-093-a-deterministic-seeder.md)                                         | API                    | STY-091     |       |
| STY-094 | [Ask for access to a tenant](STY-094-ask-for-access-to-a-tenant.md)                                 | API                    | invitations |       |

_All Placeholders until their acceptance criteria are written: ADR-016 (STY-085–STY-089)
and ADR-017 (STY-090–STY-093) are accepted.
STY-094 is a Placeholder until the invitation story exists.
Candidate scope, to split next: the first schema
and its enforcement suite; people, identities, memberships, roles, assignments and
invitations, with ADR-019's authorisation suite; the threat model, then sign-in with
Google and the mock provider, sessions and signing out (ADR-018); the scratch, draft,
save, publish and restore path; the API's endpoints for the roadmap repository's calls
and for the public read; the import of the spreadsheet's data; and the editor's API
adapter with its build-time switch, signing in through the API. Entra, with its spike,
is a later story._

## Sequencing

The rename (STY-085) comes first, then the workspace move (STY-086), which stays one
change. Then two tracks run in parallel: the repository's (STY-087, then STY-088 into
a protected `main`, then STY-089) and the API's (STY-090, then STY-091 and STY-092 in
either order, with STY-093 after STY-091). STY-090 and STY-087 both change `ci.yml`
and the Dependabot file: whichever lands second rebases onto the other, and so does
CHO-031 (supply-chain checks), delivered beside STY-087. The threat model comes before
any identity story (ADR-018); STY-094 follows the invitation story. The schema
stories follow STY-093, adding their factories; the editor's adapter follows STY-092.

## Out of scope

- The editor's new editing model: a server scratch, a shared draft, permissions and
  assignments in the interface (ADR-015 _Consequences_). A later epic, once this one's
  API exists.
- Switching the deployed editor to the API, retiring the Sheets adapter, and moving
  the public site to the API's read: after an environment exists.
- Infrastructure as code, provisioned environments, Google Cloud hosting and custom
  domains: [EPC-023](../EPC-023-hosting-and-infrastructure-security/README.md), handed
  a service that runs locally and in CI. A cross-repository deploy trigger was rejected
  (ADR-016), not deferred.
- Live presence and real-time updates.

## Defects

None.

## Related

- [ADR-015](../../adr/ADR-015-the-roadmap-database-is-postgresql-tenant-scoped-and-versioned.md),
  [ADR-016](../../adr/ADR-016-one-pnpm-workspace-for-the-editor-public-site-and-api.md),
  [ADR-017](../../adr/ADR-017-the-api-is-synchronous-fastapi-over-sqlalchemy-and-psycopg.md),
  [ADR-018](../../adr/ADR-018-sign-in-through-the-api-with-a-server-side-session.md),
  [ADR-019](../../adr/ADR-019-the-api-authorises-every-route-from-a-permission-catalogue-in-code.md),
  [ADR-020](../../adr/ADR-020-the-editor-and-the-api-share-one-origin.md),
  [ADR-002](../../adr/ADR-002-layered-architecture-and-repository-boundary.md)
- [Identity and authorisation analysis](../../analysis/identity-and-authorisation.md)
- [EPC-023](../EPC-023-hosting-and-infrastructure-security/README.md) — hosting and
  infrastructure security, a placeholder
- [Replacing Google Sheets](../../operations/replacing-google-sheets.md)
- [STY-048](../EPC-011-adding-roadmaps-and-items/STY-048-remove-a-roadmap.md) —
  removing a roadmap, bound by ADR-015 Option 8
- [CHO-005](../chores/CHO-005-send-last-updated-to-the-api-in-utc.md)
- [CHO-031](../chores/CHO-031-supply-chain-checks-on-every-pull-request.md) —
  supply-chain checks, beside STY-087
