---
name: retro
description: Run a retrospective after a delivered PR is raised, merged or blocked, or on request, and implement improvements to future agent runs in one separate PR, which gets no retrospective of its own.
---

# Session retrospective

Improve the coding agent's **environment** for future runs, from evidence in
the specified session (default: this one). An automatic retrospective starts
once the primary PR is raised and left for the owner (the default), merged
when merging was requested, or blocked, once per primary task. Its PR gets no
retrospective of its own.

## Find improvements

Read `.agents/skills/writing-for-agents/SKILL.md`,
`docs/operations/authoring-agent-instructions.md`, the primary task's compact
handoff (`/tmp/roadmaps-<record-id>-handoff.md`, or the run folder's in an
orchestrated run) and the relevant session evidence. Use only available logs;
do not search unrelated personal sessions or secrets. For orchestrated work,
read the run summary and collection rules in
`.agents/skills/orchestrate/references/run-summary.md`. Inspect currently
available reviews/comments on the primary PR, including bot findings; record
actionable unresolved findings in the owning backlog. This is a snapshot, not
a promise to monitor indefinitely for later findings.
Trace each piece of friction to its cause, checking these categories:

- **Navigation**: did finding the right file take long? Is there a hidden
  dependency between files that a **navigation pointer** would expose?
- **Automated checks**: could a type, lint or test check have caught a
  mistake the agent made? Read the existing config first (`tsconfig*.json`,
  `eslint.config.ts`, `vite.config.ts`'s `test` block, `playwright.config.ts`,
  `.github/workflows/ci.yml`): an existing check that is unwired or silently
  broken is the finding, not a reinvention.
- **Coding standards**: did a reviewer miss a mistake? A **mechanical**
  violation (a syntactic pattern, banned API, import shape, file location)
  earns a deterministic check with a regression case. Build it at the highest
  rung that works: a type error; an existing ESLint rule, or a new
  `no-restricted-imports` or `no-restricted-syntax` rule in
  `eslint.config.ts`; a Vitest test; only then a custom script. Put its
  incident and a review date about 90 days out in a comment at its head.
  A slip that is not mechanical goes where the next reader of that code meets
  it: a comment at the site, or nowhere when the code already says it.
  Change a review skill (`code-review`, `quality-review`, `threat-review`) only to add or
  sharpen a general lens, a class of defect that recurs across many kinds of
  diff; one review's miss is evidence for a lens, never a check of its own.
- **Agent guides**: would a rule have prevented the friction? Give it the
  first rung that holds it on the authoring guide's _Where it goes_ ladder; a
  guide line must pass its recur bar and replace or sharpen a line there. Most
  retros end with no guide edit. Delete any guide line the session showed
  stale, wrong or ignored.
- **Tool economy**: were tool calls expensive or noisy (large dumps, repeated
  polling, work a cheaper delegated worker should have done)?
- **No-ops**: which instructions did not change the agent's behaviour?
- **Information access**: was a crucial fact unavailable (logs, CI output, a
  runtime capability, the real Google services the E2E suite fakes)?
- **Wall-clock time**: where did the elapsed time go? Run
  `node .agents/skills/retro/scripts/session-timeline.mjs [session.jsonl]`
  (`--help` for its options) on the primary task's Claude Code session log;
  the current directory's newest is the default, so pass the primary log when
  the retro runs in a later session. It times only what the session ran:
  milestones, commands by kind (Vitest and Playwright runs, builds, type
  checks, lint, dev or preview server start-up), what the test runners
  reported, background work and the waits between. Where no such log exists,
  use commit, PR, CI and review timestamps through `git` and `gh`. For the
  largest phases, find what would start them sooner, run them in parallel, or
  remove them, and give the measurements behind each finding.

Implement every justified improvement that fits one coherent PR. Do not
manufacture a finding to ensure a PR exists; a no-op report is valid when
nothing justified remains. Record larger or unrelated work in the owning
backlog using `docs/AGENTS.md`, as a chore (Status `Proposed`); do not start
an unbounded cleanup. A proposal beyond the retro's scope that the owner has
not accepted becomes a record with Status `Needs grilling` instead.

## Deliver separately

1. Confirm the primary PR's outcome (open for review, its merge SHA, or its
   blocker), capture its head and preserve unrelated work. Fetch the remote
   default branch with `--prune`, then branch from it in the same isolated
   checkout, without a worktree by default:
   - Pushes free: create `<prefix>/retro-<record-id>` with the runtime's usual
     prefix (`claude` for Claude).
   - Pushes restricted to one assigned branch, primary PR merged: reuse that
     branch name, reset to the default, per
     `.agents/skills/implement-story/references/pr-watch.md` "Merge".
   - Pushes restricted to one assigned branch, primary PR still open (the
     default outcome): that branch carries the open PR, so leave it alone.
     Ask for a second branch, or record the retro as deferred with its
     findings.
2. Inspect each proposed improvement on that base: the primary PR is usually
   still unmerged. Keep only independent changes. If an improvement requires
   that unmerged PR, record a deferred finding instead of copying its
   implementation or quietly creating a stacked PR. If primary delivery was
   blocked, preserve that branch and complete its delivery when access is
   restored first.
3. Implement the improvement and its relevant checks. Show the failing case
   for a new deterministic guard, and verify existing valid cases remain valid.
   Record context/rationale in a short PR body or an owning docs record; keep
   persistent rules free of the session narrative.
4. Follow `.agents/skills/implement-story/references/pull-requests.md`: pin the
   final diff, review it in the lanes `delegation.md` sets, resolve findings,
   fill the body from `.github/pull_request_template.md` and open the separate
   PR, linking it to the session where the runtime can. Leave it open for the
   owner, like the primary; babysit it per `pr-watch.md` only when the user
   asked for babysitting or merging, and squash-merge it only when they asked
   for merging. Set `retro: complete`
   in the task handoff; do not recursively invoke this skill for that PR.
5. Report the improvements and evidence, both PR URLs (and merge SHAs where
   merged), and any outstanding limitations. For a no-op or deferral, state
   why with evidence. Return the outcome and measurements to the top-level
   collector; a no-op does not suppress the orchestration run summary.

A saved instruction, scheduled wake-up or planned command is not evidence of
executed work.
Never describe an unavailable review or missing PR as done.
