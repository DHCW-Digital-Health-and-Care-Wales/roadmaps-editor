# EPC-024 delivery notes

What agents delivering or reviewing this epic's (and EPC-025's) API stories need; carried
from EPC-022 when the backend work moved here. See `docs/AGENTS.md`.

- **A thread keeps the request's trace only if it is given it**: a service that starts a
  thread runs it in `contextvars.copy_context()`, as `ReadinessService.check` does, or
  its queries leave the request's trace and its log lines lose the request ID. FastAPI's
  own telemetry stays off in `create_app` (its spans carry the query string), so a
  FastAPI bump re-reads `fastapi/telemetry/` for a new way it could turn on.
- **Row-level security does not cover `TRUNCATE` or `REFERENCES`**: PostgreSQL applies
  neither to policies, so `STY-103`'s enforcement suite also proves `roadmaps_app` holds
  neither on any table.
- **Before a route takes a request model, read `ApiRequestModel`'s docstring**
  (`apps/api/src/roadmaps_api/wire.py`): which keys FastAPI gives a query, header,
  cookie or body model decides what its `extra="forbid"` refuses.
- **A local API's log lines hold messages**: `ROADMAPS_ENV=local` writes an exception's
  and a third party's message (ADR-018 _STY-101 amendments_), so an API test that
  asserts no planted value reaches the log runs under test's or production's rules
  (`apps/api/tests/conftest.py`'s `lines` fixture, or production's settings).
- **The first migration that inserts seed/lookup rows must teach both teardown sites
  (`apps/api/tests/harness.py:empty_tables` and `apps/api/tools/local_db.py:truncate_public_tables`)
  to put them back** after each `TRUNCATE … CASCADE`, with a test (carried from EPC-022
  _The API's conventions_ / STY-091 D15; extended for `STY-093`).
- **Public-repo security hygiene (`STY-102` D7, D9, D12)**: never publish unfixed
  security gaps in an accepted design or in merged/deployed code, threat/risk
  severity or exploitability ratings for the product, internal WAF/rate-limit
  thresholds, reviewer PII or internal ticket references in tracked files, commit
  messages, PR bodies, Review records, review threads or Delivery sections. If delivery
  or review discovers such a gap, report it to the owner in chat first before writing it
  to any public surface. (Standard P0–P3 PR review grades for defects fixed within the
  PR's own unmerged diff are unaffected.)
- **Keep `docs/analysis/identity-threat-model.md` in step**: when a story delivers and
  tests a control marked `Mitigated by design`, promote that threat row to `Mitigated`
  with its test citation. Never edit the **Cyber security sign-off** table (owner-only),
  and alert the owner if a change materially alters a signed-off phase's flows or
  controls.
- **Migrating `SECURITY DEFINER` routines onto a dedicated definer owner role**: create
  the routine, run `REVOKE ALL … FROM PUBLIC` and `GRANT EXECUTE` (and `CREATE TRIGGER`
  for trigger functions) as `roadmaps_owner` first, then temporarily `GRANT CREATE ON
SCHEMA public TO <definer>`, run `ALTER FUNCTION … OWNER TO <definer>`, and `REVOKE
CREATE ON SCHEMA public FROM <definer>` before commit. If `roadmaps_owner` itself also
  needs `EXECUTE` on an internal definer routine, grant it after ownership transfer via
  `SET LOCAL ROLE <definer>` then `SET LOCAL ROLE roadmaps_owner`.
- **Role-conditional trigger exemptions use `CREATE TRIGGER … WHEN (current_user <> …)`**:
  inside a `SECURITY DEFINER` trigger function, `current_user` is the trigger function's
  owner (`roadmaps_history_definer`), not the statement's caller; put caller-role checks
  in the trigger's `WHEN` clause (as `invitations` does for `roadmaps_auth_definer`'s
  purge `DELETE`).
- **Every API router sets `route_class=PolicyAPIRoute` and every route declares one
  policy** (`public()`, `signed_in()`, `tenant_member()`, or
  `tenant_permission(Permission.…)`): `create_app` calls `verify_app_routes` and fails
  closed on missing/duplicate policies, include-time dependencies or non-policy router
  dependencies placed ahead of a route's policy, plain `APIRoute`s, mounts, hosts,
  `frontend()` routes, tenant routes lacking `{tenantSlug}` or unlisted `public()` routes.
- **Every new route needs a `CALL_SPECS` entry** in
  `apps/api/tests/integration/test_authorisation.py` (failing the standing role-by-route
  matrix, cross-tenant sweep, non-`GET` same-origin sweep and read-only `GET` suite
  immediately if omitted). A new `public()` route also requires a reviewed entry in
  `PUBLIC_ROUTES` (`apps/api/src/roadmaps_api/authz/routing.py`); the future OIDC
  callback also registers in `READ_ONLY_GET_EXEMPTIONS`.
- **State-changing API test calls send same-origin and person-assertion headers**:
  non-`GET` requests need `Sec-Fetch-Site: same-origin` (or `Origin: <editor_origin>`),
  `Content-Type: application/json` for routes declaring a body parameter, and
  `X-Roadmaps-Person-Id` when authenticated. Inject test principals by overriding
  `app.dependency_overrides[get_current_principal]`. In `STY-107`, keep `fetch`'s default
  mode (not `no-cors` under `no-referrer`) so the browser never sends `Origin: null`, and
  open the local editor on `localhost:<DEV_PORT>` rather than `127.0.0.1`.
