# STY-094: Someone not yet invited asks the API for access, and a tenant admin approves or declines it

- **Status**: Placeholder — the owner's future story (2026-11-21); designed once the
  invitation story exists
- **Type**: Feature
- **Area**: API
- **Epic**: [EPC-022-monorepo-and-backend-foundation](README.md)
- **Depends on**: the invitation story (not yet written; hard)
- **Binding ADRs**: ADR-018 §Getting in, ADR-019 §What members and assigned leads may do
- **Suggested model**: Opus — a write path from a signed-in identity with no membership,
  amending ADR-018

## Summary

A valid NHS Wales user (or, before Entra, a DHCW Workspace user) who signs in without an
invitation sees "You haven't been invited" and can ask for access to an organisation.
The request waits for a tenant admin, who approves it, admitting them as an invitation
would, or declines it. Today such a sign-in is refused and writes nothing (ADR-018).
This story is the API side; the admin's pending join requests screen comes with the
editor's members screens in the editing-model epic.

## Why this is a placeholder

The invitation flow it extends is not yet written. It also amends ADR-018: §Getting in
(an uninvited sign-in "writes nothing but a log line") and §The sign-in transaction (the
transaction table is "the only database write anonymous traffic can cause"), and
ADR-020's rule that unauthenticated failures never reach the database. The owner raised
it in the review of the identity ADRs (2026-11-21).

## Rough shape of the work

_Not acceptance criteria._

- How the caller is proven for the request: a short-lived, single-purpose proof from
  the refused callback, bound to the `(issuer, subject)` the provider returned, never a
  session.
- What a request stores before a person exists: that identity and the name and verified
  email the provider issued (never free text), and the tenant asked; the requester names
  the tenant by a code its admin shares, so the list of tenants cannot be enumerated.
- Approval binds the identity, with a role the admin alone chooses, as an access change
  set by the approving admin; declining removes the request.
- Abuse: one pending request per identity, a global cap, and a purge of declined and
  stale requests, with retention counted in the data protection assessment.

## Out of scope

- The pending join requests screen: the editing-model epic, with the members screens
  (ADR-019 _Consequences_).
