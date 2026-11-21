# STY-088: Bring the public site into the workspace, still published at its address

- **Status**: Placeholder — ADR-016 accepted (owner, 2026-11-21); promoted once its
  acceptance criteria are written
- **Type**: Refactor + Docs
- **Area**: CI/CD + Docs
- **Epic**: [EPC-022-monorepo-and-backend-foundation](README.md)
- **Depends on**: STY-087 (hard)
- **Binding ADRs**: ADR-016 §The public site, ADR-007
- **Suggested model**: Opus — a history merge and a cross-repository cut-over

## Summary

The public site's code and history move into `apps/public-site`, on the workspace's
toolchain, and `product-roadmaps` keeps publishing it at `/product-roadmaps/` from a
nightly and manual build of this repository's `main`. The public sees no change.

## Why this is a placeholder

ADR-016 is accepted (2026-11-21), but the acceptance criteria are not yet written.

## Rough shape of the work

_Not acceptance criteria._

- Freeze `product-roadmaps`. On a branch of its history, `git mv` everything into
  `apps/public-site`, then merge it with `--allow-unrelated-histories` (ADR-016 _The
  public site_), so its root files never collide with the workspace's. An owner widens
  the merge setting and the ruleset's merge methods for that pull request, or merges
  through bypass, and restores both.
- The toolchain change and the reformat commit; the root `eslint.base.ts`; its CI jobs
  (checks, E2E in its Playwright container, Lighthouse); its guide as
  `apps/public-site/AGENTS.md`.
- Compare the built output before and after. Then `product-roadmaps`' deploy and
  `check-sheet.yml` workflows check out this repository; its open Dependabot pull
  requests close; its README points here; ADR-007's amendment for the public site.
