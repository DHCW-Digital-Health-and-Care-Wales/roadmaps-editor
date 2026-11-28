# AGENTS.md — the API

Rules for work under `apps/api/`, beside the root `AGENTS.md`. Paths are from the
repository root.

## What this is

A synchronous FastAPI service over PostgreSQL, through SQLAlchemy and psycopg (ADR-017).
The editor reaches it on its own origin: its dev server proxies `/api` here (ADR-020).
Contract routes live under `/api/v1`; the platform's probes, `/health` and `/ready`, at
the root, unversioned (ADR-017's amendments).

## Layering (ADR-017)

- A route calls a service; a service calls repositories; nothing imports a layer above
  it (highest first: `roadmaps_api.routes`, `.services`, `.authz`, `.repositories`;
  `roadmaps_api.app` composes them). Routes stay thin and synchronous (`def`).
- Only a service ends a transaction; a route, `authz` module or repository never calls
  `commit()`, `rollback()` or `begin()` on a session. `/ready` is the worked example
  (`apps/api/src/roadmaps_api/routes/probes.py`, with its service and repository under
  `services/` and `repositories/` beside it), its service given to the route as a
  dependency.

## The database (ADR-015, ADR-017)

- The API connects as a login of `roadmaps_app`, the application's role; migrations
  connect as a login of `roadmaps_migrator`, which switches to `roadmaps_owner`, the
  owner of schema objects except `SECURITY DEFINER` routines (owned by dedicated definer
  roles, ADR-015). `apps/api/src/roadmaps_api/bootstrap.sql` makes the database roles;
  locally `apps/api/tools/bootstrap_database.py` runs it, and the hosting infrastructure
  runs it where the API is hosted.
- A schema change is a revision in `apps/api/src/roadmaps_api/migrations/versions/`,
  numbered next in the line (`NNNN_<slug>.py`, its revision ID the file's name), drafted
  by autogenerate and finished by hand (`[tool.alembic]` in `apps/api/pyproject.toml`).
  It upgrades only, stays compatible with the version before it, which serves while a
  deploy migrates, and grants `roadmaps_app` exactly what each object it creates needs,
  routines included. Give each tenant-owned table forced row-level security with
  `TENANT_POLICY` (`apps/api/src/roadmaps_api/database.py`); `alembic_version` is the
  one table without it.
- A test that reaches the database follows `apps/api/tests/integration/AGENTS.md`.

## The contract (ADR-017)

- JSON on the wire is camelCase. Every model a request reaches, nested ones included,
  inherits `ApiRequestModel`, and a response's inherits `ApiResponseModel`
  (`apps/api/src/roadmaps_api/wire.py`). A plain query parameter takes
  `Annotated[Model, Query()]` or an explicit `alias`, and `ApiError.params` keys are
  camelCase.
- For recursive shapes in `ApiRequestModel`, use discriminated unions (never
  undiscriminated recursive unions), and add an explicit depth validator if a recursive
  request model is ever introduced (ADR-020).
- Bound every collection in `ApiRequestModel`, nested collection type arguments included,
  using concrete builtins (`list`, `dict`, `set`, `frozenset`, variadic `tuple` — not
  `Sequence` or `Mapping`): set `Field(max_length=…)` on every `list`, pair `FailFast()`
  with `Field(max_length=…)` on every `dict`, `set`, `frozenset` and variadic `tuple`, and
  bound every `dict` key with `Annotated[str, StringConstraints(max_length=…)]` (ADR-020).
- `apps/api/openapi.json` and `packages/api-types/src/generated/` are generated and
  committed, never edited by hand. After a change to a route, a wire model or
  `ErrorCode`, run `pnpm api:contract`, which needs no database, and commit what it
  writes. CI fails on drift: `pnpm api:openapi:check` for the document,
  `pnpm api-types:check` for the generated source.

## Errors and responses

- Refuse with `ApiError(ErrorCode.…)` (`apps/api/src/roadmaps_api/errors.py`). Add each
  new code to `ErrorCode` with its status and detail, and map it in
  `apps/editor/src/infrastructure/roadmaps-api/api-error.ts`, which fails the editor's
  typecheck until it does (ADR-017 _Errors_).
- Never put submitted input, an exception's text or a traceback in a response, and send
  no CORS header (`apps/api/src/roadmaps_api/middleware.py`, ADR-020).

## Logs (ADR-018 _Records and retention_)

- Log a constant event name with allow-listed `extra` fields
  (`ALLOWED_EXTRA_FIELDS` in `apps/api/src/roadmaps_api/logs.py`, which drops anything
  else). Add a field to the allow-list only when it is an ID, a code, a type, a name or
  a number, never a value a caller or person supplied.
- Name a request in a log line by its route template (or `unmatched`) and a defined HTTP
  method, never as the caller sent them (`apps/api/src/roadmaps_api/access_log.py`).
- Log exceptions with `logger.exception` or `exc_info` rather than formatting them into
  the message. Never set a database function's SQLSTATE, constraint name or other
  diagnostic field from a data value, since the log writes them.

## Settings

- Read settings from environment variables only
  (`apps/api/src/roadmaps_api/settings.py`), never a `.env` file; give each of the
  API's own the `ROADMAPS_` prefix. Fail closed on an invalid or missing required
  value, naming the setting and never its value; an unset `ROADMAPS_ENV` takes
  production rules.

## Commands and checks

- The `api:` scripts need the environment `uv sync --locked` makes in `apps/api`
  (`pnpm worktree:setup` runs it); `pnpm api:dev`, `pnpm api:migrate` and
  `pnpm api:test` start and bootstrap the slot's database themselves, in Docker, and
  `pnpm api:dev` migrates it first.
- Run Python through uv from `apps/api` (`uv run --locked …`); add a dependency with
  `uv add`, which resolves only releases a week old.
- The seams of the root guide's test rule, lowest first: a pure helper, a repository or
  service, FastAPI's `TestClient` (`apps/api/tests/support.py`), then the real uvicorn
  server (`apps/api/tests/test_server.py`) only for server-level behaviour such as its
  own logging.
