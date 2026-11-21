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
independent security review, which found the worst gaps; neither correctness reviewer
had found them. The question: should a pull request that records a security decision
(authentication, sessions, tokens, tenancy isolation, infrastructure-held protections)
get a security review lane by default, on which model, and at what cost?

## Measurement

PR #222, heads `17482b7` (round 1) and `0e032cd` (round 2):

| Reviewer                    | Its High or P1 findings, and who else raised them                                                                                                                                                                                                                                                 |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Security (Fable 5.2, extra) | The callback cannot see the `Strict` session, so linking and redemption were unbound (H1): no one else. A hijacked session linking an identity to lock the person out (N1): no one else. Platform jobs' database path and separability (H3): Opus correctness raised the missing procedures as P3 |
| Correctness (Opus, Sol)     | Platform-issued invitations refused by the inviter check (round 2): both, and the security reviewer as Low                                                                                                                                                                                        |

The security reviewer's brief asked for threats, wrong protocol claims and
proportionality; the correctness briefs asked for requirement fidelity and
contradictions. Both found real issues; the lanes overlapped little.

## Acceptance criteria

_Written after grilling._

## Decisions

## Out of scope

- Code pull requests: `code-review`'s security lens already covers them.
