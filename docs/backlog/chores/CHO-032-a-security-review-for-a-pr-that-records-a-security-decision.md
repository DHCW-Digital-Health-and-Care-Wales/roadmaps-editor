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
independent security review (Fable 5.2, with its own brief), which found three gaps no
correctness reviewer raised, two of them in sessions and linking; each lane raised one
of round 2's two must-fix findings. The
question: should a pull request that records or implements a security decision get a
security review lane by default, on which model, and at what cost? Done: `delegation.md`
says which pull requests take the lane and on which model, or the owner declines it,
with the lane's measured cost quoted when the owner decides.

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
contradictions. The lanes overlapped little, but PR #222 changed the model and the brief
together, so it cannot say which mattered.

The lane's cost is not recorded in the repository, and measuring it comes before
grilling: the security reviewer's tokens and wall time per round against one correctness
reviewer's, on PR #222, from the delivering session's log
(`node .agents/skills/retro/scripts/session-timeline.mjs <session.jsonl>`) and the agent
runtimes' usage records. A security round costing no more than a correctness round is
cheap; one costing more than both correctness reviewers together needs the owner's
weighing.

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
- **Q2**: Which model runs it? Example: the security reviewer on the ingress ADR is
  Fable, while Opus and Sol review correctness.
  - (a) A different model family from the correctness pair (recommended) — PR #222
    changed both model and brief, so it cannot separate them; a different family keeps
    both levers; one more provider to have available.
  - (b) Opus — no new provider; overlaps the Opus correctness reviewer's blind spots.
- **Q3**: Which PRs count as recording a security decision? Example: the story that
  builds ADR-018's sign-in, a code PR, raised after its ADR was reviewed.
  - (a) A PR that records or implements a decision on authentication, sessions,
    tokens, authorisation, tenancy isolation or infrastructure-held protections
    (recommended) — a list in the brief, judged by the delivering agent.
  - (b) Only a docs PR that records one — fewer reviews; the code that implements
    ADR-018 gets the correctness lane's auth lens alone.
  - (c) Any ADR — simpler to judge; more reviews of ADRs with no security content.

## Decisions
