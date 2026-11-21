# STY-092: The OpenAPI contract and the editor's generated schemas

- **Status**: Placeholder — ADR-017 accepted (owner, 2026-11-21); promoted once its
  acceptance criteria are written
- **Type**: Feature
- **Area**: API + Infrastructure
- **Epic**: [EPC-022-monorepo-and-backend-foundation](README.md)
- **Depends on**: STY-090 (hard)
- **Binding ADRs**: ADR-017 §Errors, §The contract with the editor, ADR-016 §Layout and
  name, ADR-002
- **Suggested model**: Sonnet — generation and drift checks with known tools

## Summary

The API's OpenAPI document is committed and checked for drift, and
`packages/api-types` generates the editor's types and `zod/mini` schemas from it. The
editor's build then fails if the API emits an error code its adapter does not map.

## Why this is a placeholder

ADR-017 is accepted (2026-11-21), but the acceptance criteria are not yet written.

## Rough shape of the work

_Not acceptance criteria._

- A command writes the document, with every error code enumerated; CI fails on drift.
- `packages/api-types` created with Hey API's openapi-ts; knip arrives with it.
- The adapter's typed code-to-`AppError` table, started with the skeleton's codes.
- The editor's import rules forbid `domain/`, `features/` and `components/` from
  importing `packages/api-types`.
- Proposed default: `params` in camelCase.
