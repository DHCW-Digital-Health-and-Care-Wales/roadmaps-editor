# STY-086: Move the editor into apps/editor in one pnpm workspace

- **Status**: Placeholder — ADR-016 accepted (owner, 2026-11-21); promoted once its
  acceptance criteria are written
- **Type**: Refactor + Docs
- **Area**: CI/CD + Docs
- **Epic**: [EPC-022-monorepo-and-backend-foundation](README.md)
- **Depends on**: STY-085 (hard)
- **Binding ADRs**: ADR-016 §Layout and name, §Agent guides, ADR-007
- **Suggested model**: Opus — one mechanical change with a wide blast radius

## Summary

Today's app moves to `apps/editor` under a pnpm workspace root, unchanged for Product
Leads. It is one change (EPC-022 _Design_ 1): code, configs, CI paths, guides, skills
and worktree scripts move together, so no half-moved state lands on `main`.

## Why this is a placeholder

ADR-016 is accepted (2026-11-21), but the acceptance criteria are not yet written.

## Rough shape of the work

_Not acceptance criteria._

- `git mv` the app, its configs, `tests/`, `build/` and `public/`; a root
  `package.json` and `pnpm-workspace.yaml`; root scripts delegating with
  `pnpm --filter`.
- CI paths and the Pages artifact path; `t3.json`, the session-start hook, the
  worktree script and `.env*` locations; `components.json`.
- The root `AGENTS.md` split: repo-wide rules and a routing table at the root, the
  editor's rules in `apps/editor/AGENTS.md`; live records, skills and references
  (implement-story's `validation.md` and `screenshots.md`) follow; archived records
  keep their citations.
