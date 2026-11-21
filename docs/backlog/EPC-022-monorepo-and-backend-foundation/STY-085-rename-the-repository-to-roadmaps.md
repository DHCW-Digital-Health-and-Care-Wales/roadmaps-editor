# STY-085: Rename the repository to roadmaps, and tell leads the editor's new address

- **Status**: Placeholder — ADR-016 accepted (owner, 2026-11-21); promoted once its
  acceptance criteria are written
- **Type**: Docs
- **Area**: CI/CD + Docs
- **Epic**: [EPC-022-monorepo-and-backend-foundation](README.md)
- **Depends on**: none
- **Binding ADRs**: ADR-016 §Layout and name, ADR-007
- **Suggested model**: Sonnet — a settings change and a sweep of names and addresses

## Summary

The repository becomes `roadmaps`, ahead of the workspace move, so the editor opens at
`/roadmaps/` instead of `/roadmaps-editor/`. Product Leads are told the new address; the
old one gets no redirect. Nothing in the editor changes.

## Why this is a placeholder

ADR-016 is accepted (2026-11-21), but the acceptance criteria are not yet written, and the rename is hard to reverse once leads have the new address.

## Rough shape of the work

_Not acceptance criteria._

- An owner renames the repository in GitHub's settings; GitHub keeps redirecting the
  repository's own links.
- One pull request updates every name and address: README badge and links, docs and
  runbooks, the worktree registry path, the E2E base path and the base-path guard's
  expectations.
- ADR-007's amendment for the new base path (ADR-016 _Consequences_); leads are sent
  the new address.
