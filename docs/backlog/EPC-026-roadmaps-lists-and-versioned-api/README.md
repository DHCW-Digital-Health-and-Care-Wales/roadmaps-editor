# EPC-026: Roadmaps, lists and versioned API — the full data model behind the API

- **Status**: Needs grilling — placeholder epic opened from the owner's incremental API
  decomposition (2026-11-25); designed once EPC-024 and EPC-025's core tenancy, sign-in
  and membership flows are in place
- **Progress**: 0 of 0 terminal; next selectable: none; blocked on: EPC-024 and EPC-025
- **Binding ADRs**: ADR-015, ADR-017, ADR-018, ADR-019, ADR-020

## Summary

EPC-024 and EPC-025 establish tenancy, sign-in, sessions, route authorisation,
invitations and member management across the database, API and editor, while existing
roadmap and family screens fail cleanly against a stub repository in API mode. This epic
implements the roadmap domain in PostgreSQL and FastAPI (ADR-015): tenant-scoped lists
(families, categories, tags, organisations), roadmaps, items, assignments, private
scratches, shared drafts, three-way field merges, publications, immutable snapshots and
change summaries, restore across schema versions, retire/reinstate, redaction, and the
scratch-expiry scheduled job. Editor screens that consume these endpoints live in
[EPC-027](../EPC-027-editor-roadmap-editing-on-the-api/README.md).

## Owner decisions waiting

- Story split and incremental delivery order within this epic (lists first, then roadmaps
  and items read, then scratch/draft/save/publish, then history/restore/retire/redaction)
- Exact payload shapes and conflict-response contract for three-way merges (ADR-015 Option 25) and CHO-005 (Last updated date format)

## Findings

Greenfield for the roadmap tables and endpoints; audited against ADR-015, ADR-017 and
ADR-019 on 2026-11-25:

- `EPC-024` establishes `tenants`, `people`, `identities`, `roles`, `memberships`,
  `change_sets` (access scope), the commit function, `platform_audit_log`, the
  authorisation framework and the deterministic seeder (`STY-093`).
- Noted after `STY-105`: `tenant_permission`
  (`apps/api/src/roadmaps_api/authz/policies.py`) names one permission. ADR-019's
  roadmap rules need more: editing takes `roadmaps:edit` with an assignment to the
  roadmap, or `roadmaps:edit-any`, and publishing takes `roadmaps:publish` as well. The
  editing stories design how a route declares and checks that.
- ADR-015 already settles the core database rules: normalised working tables with
  `tenant_id` foreign keys and forced RLS, integer positions rewritten per placement,
  details as format-checked bilingual text, private JSONB scratch per person per roadmap,
  one shared draft per roadmap, three-way field-level merge, commit-built snapshots and
  change summaries, retiring instead of deleting with reserved names, audited admin
  redaction, and scratch expiry (30 days, warned at 23).

## Design

_Candidate scope, to be grilled and split into stories when this epic is planned:_

1. **Tenant lists schema and API**: families, categories, tags and organisations (bilingual
   names, colours, national flag, retire/reinstate, reserved names, `lists:edit` and
   `tags:edit` policies, list-scope change sets and snapshots, seeder factories).
2. **Roadmaps, items and assignments schema and read API**: normalised roadmaps, items,
   item-tag and item-organisation join tables, assignments (`assignments:manage` and
   co-lead rules from ADR-019), current published/draft read endpoints, retired roadmaps
   visibility, seeder factories.
3. **Private scratch, shared draft, save and publish API**: per-person JSONB scratch
   (owner-only RLS, optimistic version check), three-way field merge and placement order
   versions, save, "save and publish" (two change sets in one transaction), publish,
   unpublish, discard draft, retire/reinstate roadmap, idempotency keys, commit-built
   snapshots and change summaries, plus ADR-015's full database enforcement proofs.
4. **History, restore, redaction and scratch expiry**: reading change sets and snapshots
   (with list names resolved at the snapshot's list revision), restoring past snapshots
   across schema versions (flagging retired list entries), audited `content:redact`
   procedure, and the scratch-expiry scheduled CLI job (30 days, warned at 23).

## Shared assumptions and contracts

Inherits the API conventions from
[EPC-022](../_archive/EPC-022-monorepo-and-backend-foundation/README.md) and the tenancy,
authorisation and error-envelope contracts of
[EPC-024](../EPC-024-tenancy-sign-in-and-optional-api-mode/README.md).

## Stories

None yet: written when the epic is grilled.

## Sequencing

Follows [EPC-024](../EPC-024-tenancy-sign-in-and-optional-api-mode/README.md) (tenancy,
commit function, authorisation, seeder) and
[EPC-025](../EPC-025-tenant-members-and-invitations/README.md) (members and invitations).
Stories here can land incrementally alongside
[EPC-027](../EPC-027-editor-roadmap-editing-on-the-api/README.md): as each API slice
lands (lists, then roadmap reads, then editing), the matching editor slice wires it in
place of the stub.

## Out of scope

- Editor UI and `ApiRoadmapRepository` wiring:
  [EPC-027](../EPC-027-editor-roadmap-editing-on-the-api/README.md).
- Public read endpoints (no auth, open CORS), Sheets import and switch-over:
  [EPC-028](../EPC-028-public-read-api-sheets-migration-entra-and-switch-over/README.md).
- Hosting, Cloud SQL and Cloud Scheduler provisioning:
  [EPC-023](../EPC-023-hosting-and-infrastructure-security/README.md).

## Defects

None.

## Related

- [ADR-015](../../adr/ADR-015-the-roadmap-database-is-postgresql-tenant-scoped-and-versioned.md),
  [ADR-017](../../adr/ADR-017-the-api-is-synchronous-fastapi-over-sqlalchemy-and-psycopg.md),
  [ADR-019](../../adr/ADR-019-the-api-authorises-every-route-from-a-permission-catalogue-in-code.md)
- [EPC-024](../EPC-024-tenancy-sign-in-and-optional-api-mode/README.md),
  [EPC-025](../EPC-025-tenant-members-and-invitations/README.md),
  [EPC-027](../EPC-027-editor-roadmap-editing-on-the-api/README.md),
  [EPC-028](../EPC-028-public-read-api-sheets-migration-entra-and-switch-over/README.md)
- [CHO-005](../chores/CHO-005-send-last-updated-to-the-api-in-utc.md)
- [STY-048](../EPC-011-adding-roadmaps-and-items/STY-048-remove-a-roadmap.md)
