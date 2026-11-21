# Delegation and context

Skills define procedures; agents provide execution boundaries. A persona file
alone creates neither independence nor expertise. Use a worker when its bounded
output saves the main agent context, improves verification or costs less than
having the main agent inspect every site. Do small edits directly.

| Work                                                      | Model                                                        | Context and handoff                                                         |
| --------------------------------------------------------- | ------------------------------------------------------------ | --------------------------------------------------------------------------- |
| File inventory, search, bounded exploration               | Economy (Haiku or equivalent)                                | Read-only; paths, evidence, uncertainties and short conclusion              |
| Mechanical edits requiring per-site reading               | Economy (`mechanical-worker`) with constrained brief         | Disjoint files, explicit pattern/exceptions, changed paths and verification |
| Architecture, auth/token handling, ambiguous requirements | Main agent or a stronger worker                              | Relevant domain context and trade-offs; main retains decision               |
| Correctness review                                        | **Opus** (`code-reviewer`) **and Sol** (Codex `gpt-6.1-sol`) | Fresh pinned scope; `code-review` skill; two independent reviews            |
| Maintainability and conventions review                    | **Sonnet**, high effort (`quality-reviewer`)                 | Fresh pinned scope; `quality-review` skill                                  |
| Security review, on a security-relevant PR                | **Fable 5.2**, high effort (`security-reviewer`)             | Fresh pinned scope; `threat-review` skill                                   |

Model names in Claude agent frontmatter are Claude-specific preferences. At
runtime inspect the available providers and models; choose the cheapest capable
one for ordinary work, then escalate after a concrete failure or when reasoning
risk warrants it. The reviewers' models are fixed: never substitute another model
for one silently, claim an unavailable model ran, or downshift
security-sensitive judgement just for cost. A record's Suggested model is a
tier hint: Haiku is economy, Sonnet standard, Opus stronger; a runtime without
Claude models picks its nearest model per tier. Select the provider and model
explicitly when it differs from yours; a role name alone does not select its
cost tier.

## Worker contract

Supply the objective, exact file/search boundary, applicable guides, allowed
edits, shared-checkout constraint, output location, verification and stop
condition. Workers read their own scoped rules. A child started through a
delegation tool receives only its brief, not `.claude/agents/`, so a read-only
worker's or reviewer's brief carries its shared-checkout constraint in full:
leave HEAD, the branch, the index, the stash and the files as found; read other
revisions with `git show <sha>:<path>` and `git diff <base> <head>`; never run
`git checkout`, `switch`, `reset`, `stash`, `commit` or `fetch`. Assign one
owner per file; concurrent readers are safe, concurrent writers to the same
file are not.

Have workers store verbose logs and reports under a task-specific temporary
path and return findings, file locations, commands/results and open decisions.
Ask read-only workers and reviewers for their report as their final message;
reviewers write no report files. Do not relay raw search dumps or whole
transcripts into the main context.

Use a fresh reviewer with only the brief for each review. Rebase the branch
onto the current base (`pull-requests.md`, _Update a branch_), re-run the
checks `validation.md` sets for that head, and only then pin the SHAs, or the
base-to-head diff shows work that merged meanwhile as a revert. Include the user requirements and record, base/head SHAs, the diff command, relevant
verification results, PR metadata the reviewer cannot fetch itself, and the
authoritative skill path. Omit the implementation conversation and claimed
verdict. A reviewer must inspect requirements and surrounding code before
judging. Two labels on one review are not two independent reviewers.
Cross-review handoffs contain evidence, not instructions to accept another
verdict. Ask for findings ranked by severity, each with a _realistic trigger_:
the input or workflow in this repository that produces it. A finding without
one is a decline candidate. Ask too for each part of the pinned diff the
reviewer left unread, by path and lines, which Dispatch step 5 gives to a
fresh reviewer: a reviewer not asked may report a diff it read in part as
read. Tell a delivery PR's reviewers to report each incidental guide change
in its diff as a blocker (P1 or 🔴), and to check that each correction to a
guide file changes no rule, as
`docs/operations/authoring-agent-instructions.md` defines them (_Where it
goes_).

For role-specific briefs, use `.claude/agents/mechanical-worker.md`,
`.claude/agents/quality-reviewer.md`, `.claude/agents/code-reviewer.md` and
`.claude/agents/security-reviewer.md`. A reviewer started on another provider gets
its brief's body in full (Sol the `code-reviewer` body; Fable, from Codex, the
`security-reviewer` body), since a child on another provider does not read Claude
agent files. Exploration gets a fresh read-only brief per
the Worker contract.

## Dispatch and completion

Start the reviewers of a round together so they run concurrently: a
reviewer on your own provider through the runtime's native subagent tool with
the model and effort set explicitly (Opus; Sonnet at high effort; Fable 5.2 at
high effort for the security lane), and one on another provider (Sol; or Opus,
Sonnet at high effort and Fable 5.2 at high effort, when you run on Codex) through a
cross-provider delegation tool.
Start any background delegation first, then the foreground ones, so nothing
waits on another.

Where the runtime offers asynchronous delegation with completion
notifications, use this lifecycle at every nesting level:

1. Start each worker with a complete Worker contract, sharing the current
   checkout for read-only reviews; request a separate checkout only when one is
   authorized. A child receives its brief, not your history.
2. Save each worker's task identifier, link, assigned lane, model and pinned
   head in the task handoff. Follow any instructions the tool returns.
3. After independent work is exhausted, save pending tasks and end the turn;
   completion wakes the direct parent, including a delivery agent that is
   itself a subagent. Ending the turn yields; it does not finish the delivery.
   Tell the user what is pending and its pinned head; give an expected
   duration only from observed runs.
4. On notification, consume the result, match it to the saved task and
   reviewed head, and update the handoff. Act on findings. If another required
   review is pending, yield again; continue once every required review has
   passed the required head.
5. Treat failed, cancelled or interrupted workers, pending questions and
   approvals, and any part of the pinned diff a reviewer reports unread, as
   unresolved work, never a passing review. Surface the exact blocker; route
   a child's question to the user. Give an unread part to a fresh reviewer on
   the same model, in the same round. On a reported usage limit,
   rerun a Sol review with the same brief on `gpt-6.1-sol` through the other
   provider that serves it (Codex or GitHub Copilot), naming that provider in
   the PR's Review record; for any other worker, or when both are limited, save
   its reset time (or unknown), pending tasks and next action. Once the worker
   is terminal, resume it by messaging it where the runtime can, since it
   keeps its context; a message the limit still refuses is sent again after
   the reset. Replace the worker from that handoff only when the runtime
   cannot message it. Completion grants no approval rights.

Without asynchronous delegation, run reviewers in the foreground and wait for
them. Never poll a running delegate, sleep, or set scheduled check-ins as a
workaround for a missing notification. The fallback wake `orchestrate` defines
is not a check-in: it guards one stalled wait and is removed once that wait
ends.

A worker is **terminal** only when the runtime's status for its task shows it
neither running, nor waiting on children of its own, nor holding a pending
run, whatever its last message or a `failed` notification says: a runtime
that resumes a worker itself when a usage limit resets reports it failed
until then. Read that status before replacing a worker. Cancel a superseded
worker; replace one only once it is terminal or cancelled, so one checkout
never has two writers.

Every review or re-check is a new reviewer, briefed as "Review rounds" sets;
never restart a reviewer that has reported by messaging it.

If delegation is unavailable, report that independent reviews are unavailable
and complete useful local checks; a main-agent reread is not an independent
pass.

## Review rounds

- **Lanes**: _correctness_, with two reviewers (Opus and Sol), each following
  `code-review`; _quality_, with one reviewer (Sonnet, high effort) following
  `quality-review`; and, on a security-relevant PR, _security_, with one reviewer
  (Fable 5.2, high effort) following `threat-review`. Each reviewer is its own track
  for re-checks. A docs-only PR, one that changes only Markdown under `docs/` or
  `.agents/skills/` or an `AGENTS.md`/`CLAUDE.md` (an agent definition under
  `.claude/agents/` or a skill's script is config or code, not docs), takes the
  correctness lane alone (Opus and Sol), with the security lane when it is
  security-relevant. Its briefs add the record sweep (`docs/AGENTS.md`)
  and, for an instruction file, `.agents/skills/writing-for-agents/SKILL.md`
  and `docs/operations/authoring-agent-instructions.md`, whose recur bar and
  replace-or-sharpen rule the reviewers apply to every added line. Its cap is
  round 1 and one re-check per reviewer, with no final fresh pass.
- **Security-relevant**: a PR that records a decision on, or implements or changes
  code or configuration that handles, authentication (sign-in included), sessions,
  tokens, OAuth scopes, authorisation, tenant isolation, secrets, untrusted input at a
  trust boundary, browser hardening (origin checks, CORS, CSP, redirects), personal
  data in logs, the identity and permissions CI or a deploy runs with, what CI runs
  from untrusted input (triggers, action pinning), a new runtime dependency, or
  infrastructure-held protections. A PR that only tunes CI (a timeout, a cache) is
  not. The delivering agent judges; the PR body's
  Review record says whether the lane ran, and why not when it did not.
- **Round 1**: the PR's reviewers, fresh and concurrent, briefed as the
  Worker contract sets.
- **Round 2, the re-check**: only for a reviewer whose round 1 found anything
  above P3 (correctness or security) or a 🔴 or 🟡 (quality); a CI finding that arrives
  first joins it. Start a fresh reviewer on the same model and effort. Supply
  its previous findings and how each was addressed, the head last reviewed, the
  new head and the diff command between them. A rebase since the last round
  moves the base too: re-pin both SHAs and supply
  `git range-diff <old base>..<old head> <new base>..<new head>`, since a diff
  between the heads shows the base's new work as the fix. The re-checker
  confirms or reopens each finding and reviews the changed lines and the code
  they affect. A fix that answers only P3 or 💭 findings or wording, and a
  rebase whose range-diff shows the branch's own commits unchanged, get no
  re-check: list them in the PR body's Review record.
- **Final fresh pass**: when a fix changes runtime behaviour (logic, data, auth
  or UI behaviour), not only wording, docs, tests or renames, start one fresh
  reviewer over the whole diff in the lane that owns that behaviour: Sol for
  correctness, Sonnet at high effort for quality. A fix to a security control on a
  PR whose security lane ran also gets a Fable 5.2 pass at high effort. A fix for a
  CI finding counts.
  The pass is its own task beside its lane's re-checks, briefed as a first
  round at the new head with the requirements and pinned SHAs, and asked to
  judge from those and the pinned diff alone, not the PR's body or comments. Its
  own findings that would trigger a re-check get one, unless the pass ran after
  the cap. Record in the PR body's Review record whether the pass ran and why.
- **Cap**: two rounds per reviewer, round 1 and its re-check, plus the final
  fresh pass and its re-check when they run. A reviewer reaches its cap once
  its re-check has run or been skipped because round 1 found nothing that
  triggers one. Any other review of a fix is a round, and none runs past the
  cap.
- **After the cap**: every later finding, from a reviewer, a human or CI, is
  triaged:
  - _must fix_: P0/P1, a realistic input or workflow gives a wrong result or
    skips a check that should have run, or an acceptance criterion fails;
  - _should fix_ when cheap and local;
  - otherwise _decline_ with a one-line reason, on its thread where one
    exists and else in the PR body's Review record: no realistic trigger in
    this repository, belongs to a later feature, or the cost exceeds the
    impact. A decline with a cost the owner may want to pay later also gets a
    chore record (`docs/backlog/chores/`, Status `Proposed`) in the same PR.

  Fix a must-fix or should-fix that is in scope and easily reversed (a
  one-commit revert with no external effect), rerun the affected checks and
  list it in the PR body's Review record, with no further review beyond a
  final fresh pass its runtime change triggers when none has run; that pass's
  findings are triaged here, with no re-check. Take any other must-fix to the
  owner and decline any other should-fix as above. The rule covers every PR
  the workflow raises, retro PRs included.

- **Human reviewers**: answer each comment on its thread, when babysitting was
  requested or the user asks.

## PR handoff from a delegated agent

Child completion and PR events have different owners. A reviewer's completion
wakes its delivery parent; anything that follows the PR belongs to the
top-level session. A delivery child finishes all actionable local work, links
each PR to the session immediately after creating or pushing it when the
runtime supports that, and returns the URL, head, checks/reviews snapshot and
remaining work in its handoff. Its last line is
`PR <full URL>, head <SHA>, checks and reviews <state>`. Delegated children
never watch a PR; when babysitting was requested, the top-level session follows
`pr-watch.md`.

## Handoff and compaction

Keep a compact task record outside tracked source, e.g.
`/tmp/roadmaps-<record-id>-handoff.md`: selected record and why, requirements,
branch/base/head, owned files, decisions, verification results and log paths,
the screenshot manifest, review dispositions per reviewer and round, PR URL,
the PR policy (left open, or babysit/merge requested), last inspected head,
retro state, blockers and the next concrete command. Never include
credentials. Update it at phase boundaries and before compaction or an
interruption.

On resume, re-read applicable rules and revalidate the git and PR head.
Retain this record and decisions; discard transient search output and resolved
debugging detail. A durable handoff does not itself complete any workflow step.
