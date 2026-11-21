# CHO-032: A pull request that records a security decision gets a security review, not only correctness

- **Status**: Needs grilling — a retro proposal from PR #222; whether to add a review
  lane is the owner's call
- **Type**: Chore
- **Area**: Docs
- **Epic**: standalone
- **Depends on**: none
- **Binding ADRs**: none
- **Suggested model**: Sonnet — an edit to one skill reference, once decided
- **Delivered**: _(add on delivery)_

## Summary

A docs-only pull request takes the correctness lane alone
(`.agents/skills/implement-story/references/delegation.md`, _Review rounds_). PR #222
recorded the identity and authorisation ADRs. On the owner's request it also had an
independent security review, which found two session and linking gaps no correctness
reviewer raised; the correctness lane found the most severe finding by priority. The
question: should a pull request that records or implements a security decision get a
security review lane by default, on which model, and at what cost? Done: `delegation.md`
says which pull requests take the lane and on which model, or the owner declines it.

## Measurement

PR #222, heads `17482b7` (round 1) and `0e032cd` (round 2), from its body's Review
record and the reviewers' reports in the delivering session:

| Finding                                                                                        | Raised by                                       |
| ---------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| The callback cannot see the `Strict` session, so linking and redemption were unbound (round 1) | Security only (High)                            |
| A hijacked session could link an identity and lock the person out (round 2, must-fix)          | Security only (High)                            |
| The invitation token travelled in a URL that request logs record (round 1)                     | Security only (High)                            |
| Platform jobs had no defined database path and were not separable (round 1)                    | Security (High); Opus correctness, in part (P3) |
| Platform-issued invitations were refused by the inviter check (round 2, must-fix)              | Sol (P1), Opus correctness (P2), security (Low) |

The security reviewer's brief asked for threats, wrong protocol claims and
proportionality; the correctness briefs asked for requirement fidelity and
contradictions. The lanes overlapped little. Its cost (one reviewer per round, its
duration and tokens) is not recorded in the repository: measuring it, from the agent
runtimes' session logs, is part of this chore.

## Acceptance criteria

_Written after grilling._

## Open questions _(while Needs grilling; delete once answered)_

- **Q1**: Does a docs-only PR that records a security decision get a security review
  lane? Example: the infrastructure epic's ADR on Cloud Run ingress is raised; today
  only Opus and Sol review it, for requirement fidelity.
  - (a) Yes, one security reviewer beside correctness, by default (recommended) —
    `delegation.md` _Review rounds_ gains the lane and a brief; one more reviewer per
    such PR, with its re-check.
  - (b) Only when the owner asks, as on PR #222 — no change; the lane depends on the
    owner remembering.
  - (c) No: widen the correctness brief with a threat lens — no new reviewer; the
    briefs grow, and PR #222 suggests the lenses compete for attention.
- **Q2**: Which model runs it?
  - (a) A different model family from the correctness pair (recommended) — the
    independence PR #222 showed; one more provider to have available.
  - (b) Opus — no new provider; overlaps the Opus correctness reviewer's blind spots.
- **Q3**: Which PRs count as recording a security decision?
  - (a) A PR that records or implements a decision on authentication, sessions,
    tokens, authorisation, tenancy isolation or infrastructure-held protections
    (recommended) — a list in the brief, judged by the delivering agent.
  - (b) Only a docs PR that records one — fewer reviews; the code that implements
    ADR-018 gets the correctness lane's auth lens alone.
  - (c) Any ADR — simpler to judge; more reviews of ADRs with no security content.

## Decisions

## Out of scope

- Which code pull requests take the lane: Q3 decides whether implementing a security
  decision counts, as recording one does.
