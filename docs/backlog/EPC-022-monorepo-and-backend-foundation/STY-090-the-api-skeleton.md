# STY-090: The API skeleton runs locally and in CI

- **Status**: Placeholder — ADR-017 accepted (owner, 2026-11-21); promoted once its
  acceptance criteria are written
- **Type**: Feature
- **Area**: API + CI/CD
- **Epic**: [EPC-022-monorepo-and-backend-foundation](README.md)
- **Depends on**: STY-086 (hard), STY-087 (preferred order)
- **Binding ADRs**: ADR-017, ADR-016 §Workspace tooling, §CI
- **Suggested model**: Opus — the conventions every later API story copies

## Summary

`apps/api` starts: a FastAPI service on Python 3.15 that a developer runs with one
command beside a local PostgreSQL 18, answering health and readiness, refusing with
coded errors, logging JSON and tracing locally, with lint, types and tests in CI. It
holds no roadmap data yet.

## Why this is a placeholder

ADR-017 is accepted (2026-11-21), but the acceptance criteria are not yet written.

## Rough shape of the work

_Not acceptance criteria._

- ADR-017 _Runtime and project_, _Layering_ (import-linter and the transaction check),
  _Errors_ (the envelope and the domain errors), _Tooling_ and _Operation_ (settings,
  logs, health, tracing, local running).
- Proposed defaults, not binding: pydantic-settings; a Jaeger Compose profile; the
  editor's Vite dev server proxying to the API; ruff's selection starting from `ALL`,
  each exclusion with its reason.
- Compose `postgres:18` and the worktree script's API port and database container;
  `t3.json`; root `api:*` scripts.
- ruff in lint-staged and ty before push; the API's CI job, added to the ruleset's
  required checks; Dependabot for uv; `apps/api/AGENTS.md`.
