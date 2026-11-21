# CHO-032: A pull request that records a security decision gets a security review, not only correctness

- **Status**: Done — owner, 2026-11-21 (D1–D3); archived
- **Type**: Chore
- **Area**: Docs
- **Epic**: standalone
- **Depends on**: PR #222 (hard: the skill cites ADR-018 to ADR-020, accepted there;
  merge it first)
- **Binding ADRs**: none
- **Suggested model**: Opus — a new review skill, its agent and the lane rules
- **Delivered**: https://github.com/DHCW-Digital-Health-and-Care-Wales/roadmaps-editor/pull/223

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

### S1: A security review skill exists, invoked beside correctness and quality

- [x] `.agents/skills/threat-review/SKILL.md` reviews a diff, code or design record,
      for threats, trust boundaries and security claims, under its own verdict, and
      `.claude/agents/security-reviewer.md` runs it on Fable 5.2 at high effort.

### S2: A security-relevant PR takes the security lane

- [x] `.agents/skills/implement-story/references/delegation.md` sets the security lane
      (Fable 5.2, high effort, `threat-review`) for a PR that records or implements a
      security decision, docs-only included, concurrent with the other lanes, with the
      same re-check and final-pass rules.

### S3: The Review record says whether the lane ran

- [x] `.github/pull_request_template.md`'s Review record names the security reviewer,
      or why it did not run.

## Decisions

- **D1** (owner, 2026-11-21): a new skill for security-specific reviews, invoked in
  parallel with the quality and correctness reviews, over leaving the lane to the
  owner's request or widening the correctness brief.
- **D2** (owner, 2026-11-21): it runs on Fable 5.2 at high effort, a different model
  family from the correctness pair.
- **D3** (owner, 2026-11-21, choosing the option that named this list when asked which
  PRs get the lane): it runs on
  security-relevant PRs, code or docs, those
  handling authentication, sessions, tokens, OAuth scopes, authorisation, tenant
  isolation, secrets, CI or deploy identity, or infrastructure-held protections, judged
  by the delivering agent; over every PR, or only when asked.
- **D4** (agent, 2026-11-21): named `threat-review`, since the runtime already offers a
  built-in `security-review`.

## Delivery

### Departures

- The lane's cost was not measured before the owner decided (Measurement): the owner
  chose on PR #222's evidence.
- The security-relevant list in `delegation.md` widens D3's to code or configuration
  that handles those concerns, untrusted input at a trust boundary, personal data in
  logs, browser hardening, what CI runs from untrusted input and a new runtime
  dependency (agent, from review; for the owner's agreement), so a PR carrying no new
  decision but touching a protected asset still takes the lane.

### Scenario evidence

| Scenario | Held by                                                                                                            |
| -------- | ------------------------------------------------------------------------------------------------------------------ |
| S1       | `.agents/skills/threat-review/SKILL.md`, `.claude/agents/security-reviewer.md`; the skill is listed by the runtime |
| S2       | `.agents/skills/implement-story/references/delegation.md` (_Review rounds_, the table)                             |
| S3       | `.github/pull_request_template.md` (_Review record_)                                                               |
