# ADR-017: The API is synchronous FastAPI on Python 3.15, over SQLAlchemy and psycopg 3

- Status: Accepted — owner, 2026-11-21; drafted from the owner's answers in the
  EPC-022 monorepo grilling (2026-11-21). Python 3.15 and PostgreSQL 18 were fixed by
  the owner on 2026-11-20 (ADR-015). Amended by ADR-020 (_ADR-020 amendments_).
- Date: 2026-11-21 (amended by ADR-020: CORS, serving the editor, response rules)

## Context

ADR-015 binds the database: PostgreSQL 18, forced row-level security keyed on a tenant
and a person set per transaction, history written only by the commit function and the
redaction procedure, keys from `uuidv7()` or supplied by the client, and tests as the
application's own role. This ADR binds the service that writes to it, `apps/api`
(ADR-016). The scale is dozens of roadmaps and a handful of editors per tenant. The
editor reaches the API only through the roadmap repository (ADR-002), parses what it
receives with `zod/mini`, and chooses copy from `AppError.kind` (ADR-002, ADR-008).

## Decision

### Runtime and project

- **Python 3.15 and FastAPI**, one uv project in `apps/api`.
- **psycopg 3 under synchronous SQLAlchemy 2.1:** routes are plain `def`, run in
  FastAPI's thread pool. Models are typed `Mapped[]`; queries are `select()`
  statements.
- **Relationships are `lazy="raise"`:** every load is explicit, so nothing relies on
  lazy loading and a later move to async is mechanical.

### Layering

- **Route → service → repository.** Routes are thin and raise domain errors. Services
  hold the logic and end transactions. Repositories hold every query and never end a
  transaction; a tenant-owned table's repository is built with the session and the
  tenant, a shared table's with the session alone. "Ending a transaction" means a SQL
  commit or rollback, not ADR-015's commit function, which services call through
  repositories.
- **ADR-015's atomic operations stay one transaction:** "Save and publish" writes both
  change sets before the service commits once. "Save all" across roadmaps may commit one
  transaction per roadmap, which ADR-015 leaves to the editing-model epic.
- **Enforced** by import-linter's `layers` contract, plus one check that fails a route
  or repository that commits or rolls back. Both run in the API's lint.

### Tenant and person

- **A session `after_begin` listener** applies the request's tenant and person with
  `set_config(…, true)` and bound parameters at the start of every transaction the
  session begins, so a service that ends one transaction and starts another keeps both.
- **Either may be absent:** the sign-in lookup has neither, a person's memberships are
  read before a tenant is chosen, and the public read has a tenant and no person. An
  absent value is left unset, so policies that need it fail closed. ADR-015's tests
  prove neither setting outlives its transaction.

### Schema conventions

- One naming convention for every constraint and index; enums stored as text with a
  CHECK, never native enum types; `timestamptz`, with sessions in UTC; every foreign key
  states its `ondelete`; keys from `uuidv7()` server defaults or supplied by the client
  and validated (ADR-015).

### Errors

- **Every refusal is `{detail, code, params}`**, with a stable `code`
  (`roadmap.short_name_taken`). FastAPI's own 404, 405 and 422 are wrapped in the same
  envelope; `HTTPException` is banned by ruff's banned-API rule.
- **The OpenAPI document enumerates every code.** The editor's API adapter maps each
  code to an `AppError` kind, with the params its copy needs, in one table typed
  `Record<ApiErrorCode, …>`: a code the API adds breaks the editor's build until it is
  mapped. Copy stays keyed by `AppError.kind`, and several codes may share one; ADR-002
  and ADR-008 stand unchanged.

### The contract with the editor

- **The OpenAPI document is committed**, and CI fails when it drifts from the code.
- **Hey API's openapi-ts generates the types and `zod/mini` schemas** into
  `packages/api-types`. Only the editor's `infrastructure/` imports it; `domain/`,
  `features/` and `components/` never do (ADR-002).

### The public read

- **Public, read-only endpoints with no key** serve each tenant's current publications
  and its list of roadmaps, never drafts, scratch, people or history. The tenant comes
  from its public address (ADR-015 Option 5) and no person is set.
- **Cross-origin reads are open (`*`) on those endpoints only;** they take no
  credentials. The editor's endpoints keep a strict allow-list.
- **Published roadmap data is licensed under the Open Government Licence v3.0**, stated
  on the public site and in the API's documentation.
- Abuse is met by caching and rate limiting where the API is hosted.

### Migrations

- **Alembic, sequential.** Migrations run as their own step before a version serves,
  locally by a command, never at start-up: the runtime role has no DDL rights
  (ADR-015).

### Tests

- **A real PostgreSQL 18:** the migrations build a template database once; each pytest
  worker clones its own; tests connect as the application's role; between tests a
  separate superuser connection empties the tables with `TRUNCATE … CASCADE`. That
  connection exists only in the test harness.

### Tooling

- **Ruff formats and lints with as many rules as are sensible from the start,** its
  security (`S`) and banned-API rules among them; every rule left out is listed with
  its reason beside the selection. No bandit.
- **ty, pinned to an exact version** and bumped deliberately; pyright strict is the
  fallback if a ty release blocks work (evaluation: EPC-022 _Findings_).

### Operation

- **Settings fail closed:** an unset environment gets production rules.
- **JSON logs on stdout;** `/health` answers for the process, `/ready` for the database.
- **OpenTelemetry from the start,** sending local traces to an optional Jaeger
  container; tests and CI export nothing.
- **Local running:** the API runs natively through uv; PostgreSQL 18 runs in Compose,
  one container per worktree slot.
- **A deterministic seeder** fills a local database with plausible fake data, in English
  and Welsh, the same on every run; it starts right after the migrations and grows with
  each schema story.
- **Scheduled jobs are CLI commands** an external scheduler calls (scratch expiry,
  ADR-015 Option 29); no scheduler runs inside the API.

### Rejected

- **Async SQLAlchemy, or asyncpg:** concurrency this scale does not need, at the cost of
  async fixtures and no lazy loading; `lazy="raise"` keeps the door open.
- **One transaction per request:** it would rule out the per-roadmap transactions
  ADR-015 leaves open for "Save all".
- **A savepoint rolled back per test:** wrong where services commit and where ADR-015's
  proofs need two connections. **Tests as a superuser:** the row-level security and
  immutability proofs would prove nothing. **A clone per test:** slower for no gain.
- **Native enum types:** adding or renaming a value needs a careful migration.
- **Migrating at start-up:** races between instances, and needs DDL rights at runtime.
- **RFC 9457 problem details:** more to map for one client that wants a code.
- **`AppError` carrying the API's code:** API vocabulary would reach the UI, and the
  catalogue would follow the API instead of what leads need to read.
- **Hand-written `zod/mini` schemas:** code to keep in step with the generated types.
- **mypy:** slower, and ty met the same bar.
- **An API key for the public read:** a secret to rotate for data that is public.
- **An in-process scheduler:** every instance would run it, and scale-to-zero hosting
  misses runs.

### ADR-020 amendments

- **The editor's endpoints send no CORS headers**, replacing _The public read_'s strict
  allow-list: the editor and the API share one origin (ADR-020).
- **The API serves the editor's built files and sets their document headers** in hosted
  environments, before and after the load balancer fronts the same service (ADR-020).
- **Every response that is not public** carries `Cache-Control: no-store`; every
  response carries `nosniff`, `Content-Security-Policy: default-src 'none';
frame-ancestors 'none'` and a same-origin resource policy; requests
  have a body limit; validation errors leave out the submitted input; production has no
  `/docs` or live OpenAPI route (ADR-020).
- Everything else here stands.

## Consequences

- Every route, service and repository is synchronous; moving to async touches each of
  them, mechanically.
- ty's 0.0.x releases can change rules; a bump is a deliberate change with its fixes.
- `docs/operations/replacing-google-sheets.md` changes with the adapter: its responses
  are parsed by the generated schemas, not hand-written ones.
- Follow-on work (EPC-022): STY-090 (the API skeleton), STY-091 (migrations, the tenant
  listener and the test harness), STY-092 (the OpenAPI contract and `packages/api-types`),
  STY-093 (the seeder). The public endpoints and the licence statement arrive with the
  public read, in EPC-022's later stories.
