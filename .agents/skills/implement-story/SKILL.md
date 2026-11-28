---
name: implement-story
description: Deliver a named backlog story, defect or chore, or the next logical story of an epic, through validation, independent review, a PR and one retrospective. Steps 3–6 also deliver any other change that ends in a PR.
---

# Deliver a story

The main agent owns this workflow. A named defect or chore follows it as a story
does; any other change destined for a PR reads `references/validation.md`, then
follows steps 3–6 unasked, skipping the record updates. Treat “Implement the
next logical story from Epic x” as authorization to select and deliver **one**
eligible story, push its branch and open a PR, then implement one bounded
retrospective on a separate PR. Do not start the next story automatically.

**PR policy.** By default a PR is raised, linked and left open for the owner:
do not watch, babysit or merge it. When the user asks for babysitting ("babysit
it"), step 5 follows `references/pr-watch.md` to green and stops with the PR
ready for review; only an explicit merge request ("merge when green") adds the
squash-merge. The same policy covers the retrospective PR. Explicit user constraints override these defaults.

## 1. Establish the task

Read root `AGENTS.md`, `docs/AGENTS.md`, `docs/GLOSSARY.md`, then only the
named epic's `README.md` (Stories table and sequencing) and the candidate
records' top blocks (Status, Depends on, Binding ADRs) and acceptance
criteria. Locate an epic by its folder under `docs/backlog/`, its title or a
linked ID; ask only if several matches remain plausible. A named record
bypasses selection, not prerequisite checks.

Check `git status`, branch, default branch and existing local changes. Reuse the
isolated checkout. Fetch the default branch without resetting or discarding
work; create a descriptive branch from it if the checkout is clean and no
existing task branch is intended, and start the handoff record of
`references/delegation.md` as soon as the branch exists. Preserve local work when
choosing a base.
Test read-only GitHub access before assuming credentials are missing. Check for
existing open PRs for candidate IDs when the API is available.

Select in this order:

1. Take only stories whose Status token is `Proposed` and that have no open
   implementation PR. Read the note after the token and the epic table rather
   than treating every Proposed file as ready.
2. Require prerequisite stories to be merged on the base branch and binding
   ADRs to be Accepted. A checked table row alone does not prove a
   prerequisite is merged; inspect base-branch contents and GitHub metadata
   when needed. Because PRs stay open by default, a candidate available only
   on another unmerged PR is blocked, unless the user explicitly asks for
   stacked PRs.
3. Prefer a live defect that the epic explicitly prioritises, then its stated
   sequencing, then work that unblocks other ready stories; break ties by
   table order. Choose a coherent story, not a convenient subset of its
   criteria.
4. Explain the selected ID and dependency evidence in one short update. If no
   eligible story exists, report each concrete blocker; do not invent scope or
   silently implement a placeholder.

Completion: one selected record, confirmed prerequisites, preserved work and a
branch. Keep an eligibility table only when selection is contested.

## 2. Prepare a bounded implementation

At the beginning of the delivery session, identify the UI the work will change
and capture its before screenshots per `references/screenshots.md`, before any
implementation edit. Read the record in full, its epic's `delivery-notes.md`
when there is one, its binding ADRs, the relevant personas in `docs/backlog/personas/` (`product-lead.md`,
`tenant-admin.md`, `viewer.md`, `public-reader.md`) when it changes what users
see, and the `AGENTS.md` along each affected path. Trace
the record's assumptions against the actual code and test contracts. Record
routine name, path or implementation drift and the chosen correction in its
Delivery section's Departures; preserve the original acceptance criteria.

For a gate scenario ("a new X fails CI", "the value is held by a test"), build
it at the highest rung that covers the same cases: a type error, an existing
ESLint rule (including the layer blocks in `apps/editor/eslint.config.ts`), a Vitest test,
and only then a custom script. Choosing the rung is a routine agent decision;
dropping a gate is the owner's.

Ask only about unresolved product behaviour, security or data contracts (token
handling, scopes, what is read from Google), contradictory requirements that
cannot be inferred safely, a needed new or successor ADR, or a requirement
that needs a custom layer or private internals for a corner case the framework,
library or a standard extension does not support natively, and ask the moment
the question appears, at any step. For such a corner case, propose adjusting
the requirement to stay native first, leaving a custom workaround as a rare,
explicitly agreed exception. Each option states what the build does now
and what choosing it adds, removes or moves, so the chosen answer names its
remaining work. Record each answer as an owner entry in the record's
`## Decisions`, in the owner's terms, quoting where a paraphrase would narrow or
widen it. An answer covers only what was asked: when review or later work
widens or changes what an answered decision commits to, ask again, saying what
changed; keep the answered entry as it was and add the change as an agent entry,
without the owner's acceptance, until they reply. A delegated agent heads its
handoff with the question (and, in an orchestrate run, logs it as an
`owner-question` note) and returns it to its parent once its independent work
is done, rather than calling a question tool; the parent relays it to the user
in plain chat. Continue independent work while
waiting; an unanswered question is not approval. When only work that rests on
the answer remains, hand back with it as a blocker.

Set the record's Status to `In progress — <branch or PR>`. Map each
criterion to observable verification and identify affected layers (domain,
infrastructure, features, routes, i18n catalogues, E2E fakes, CI). Read
`references/validation.md` to choose checks. For a significant new decision,
follow the ADR lifecycle in `.agents/skills/domain-modeling/ADR-FORMAT.md`.

Read `references/delegation.md` before dispatching workers. Keep exploration
reports and verbose test logs outside the main context; retain conclusions,
paths, evidence and decisions. Parallelise independent work with disjoint file
ownership; keep dependent edits and integration sequential.

Completion: an approach and verification plan covering every criterion, with
blocking decisions resolved or explicitly separated.

## 3. Implement and verify

If entering here for an ad-hoc change, capture the affected UI baselines per
`references/screenshots.md` before implementation edits, just as in step 2.

A defect fix, a change to `domain/`, a pending-edit rule (what
`apps/editor/src/features/roadmaps/editing/` keeps, shows or drops while a change is
pending), a public-site parser/sync rule (`apps/public-site/scripts/`,
`apps/public-site/src/lib/`) or an API service, repository, error, logging or
settings rule (`apps/api/`) are test-first, even when it is a review fix: write
the unit or
component regression, observe its intended failure, then implement the smallest
coherent change. Slice a large story (a new repository method, several routes, a
rewritten screen) so each such scenario's test goes red before the code that
passes it. Any other behaviour (layout, copy, a review fix) may take its test
after the code, once that test is shown red by breaking each condition the new
behaviour adds, since a condition whose break leaves the test green is untested or
dead; record the red in Delivery's Scenario evidence. Red shown by breaking finished
code proves a test discriminates, not that it came first: on a test-first
change, report it as a departure, never as TDD evidence. Undo a break from a
copy of the file saved before it: `git checkout -- <file>` puts back the last
commit, without the uncommitted work around the break. A Playwright test may
follow working code, since its selectors may not exist before; that order is no
departure.

A value with no behaviour of its own to assert (a retry count, a chunk group,
a CI job graph) is evidenced by an observed run showing its effect, recorded in
Delivery's Scenario evidence, not by a test that restates it. A
security-relevant value (an OAuth scope, a token never reaching storage) gets a
test of the property. Work that completes a migration, a rename or a one-off
verification deletes its one-off scripts and rename guards in the same PR.

Follow the owning guide and existing patterns; invoke `copywriter` before
writing user-facing copy and `domain-modeling` for terminology or ADRs when
their triggers apply, and read `.agents/skills/shadcn/SKILL.md` when adding or
composing UI components. Place each test, E2E included,
where the root `AGENTS.md` and the app's guide set; update the editor's GIS and
Sheets fakes in `apps/editor/tests/e2e/` when its UI or Sheets contract changes. Use deterministic
scripts for simple textual replacements; use a cheaper worker when each site
needs inspection. The main agent integrates and checks the result.

Run the planned checks, inspect actual counts and results and diagnose
failures. Keep passed, skipped and unrun checks distinct. Fix environment
failures where possible; never weaken checks or disable assertions to finish.

Write the record's Delivery section (departures, the contract for dependents,
each scenario's evidence) and tick its acceptance criteria. Give each learning
its narrowest home by the ladder in
`docs/operations/authoring-agent-instructions.md` (_Where it goes_). When
implementation and verification are complete, set Status `Done`, move the
record to `docs/backlog/_archive/<epic>/` and mark its epic row, leaving merge
state to the PR (`docs/backlog/_templates/status-lifecycle.md`, _Done moves
with the PR_). When this record closes the epic, sweep its `delivery-notes.md`
as `docs/AGENTS.md` says before archiving the epic. A record delivered in part
or handed back blocked returns to `Proposed` (or
`Needs grilling`), with a Decisions entry naming what remains. Commit only intended files with a conventional commit
message (`feat(scope): …`); preserve unrelated work and generated outputs
(commit `apps/editor/src/routeTree.gen.ts` when routes change).

Completion: acceptance criteria covered, appropriate checks complete, tracked
changes reviewed and a reviewable commit. An external blocker can leave a draft
PR and explicit outstanding checks, never a claimed pass or completed story.

## 4. Review and open the PR

Read `references/pull-requests.md`. Pin the base and head SHAs and dispatch
**a separate reviewer with fresh context per review**, following `code-review`,
`quality-review` or `threat-review` in the lanes, rounds and runtimes
`references/delegation.md` sets. Supply requirements and evidence, not
the implementer's self-assessment. Reviewers inspect their own relevant
callers and rules; they do not edit or switch the shared checkout. Keep their
reports separate. Resolve findings, fixing each at its cause and wherever it
recurs, rather than only for the reported trigger or at the reported line:
ask what else reaches that cause and test it too; for a changed term or
label, search the changed files and both catalogues for the old form; for a
changed behaviour, search the code, tests and records for lines that describe
the old behaviour and correct them. When a fix moves or merges tests into a lower
seam, break each value the wiring test above passes down, such as a setting or a
flag, and see that test fail. Run the checks `references/validation.md` sets for
a fix between review rounds, commit the fixes and re-review the new head in the
lanes and rounds `delegation.md` sets; the gate `validation.md` sets for a pushed
head waits for the push.
An unavailable reviewer is a stated limitation, not an invented independent
review.

After the review fixes, capture the after screenshots per
`references/screenshots.md`. Push the branch and create the PR using
`.github/pull_request_template.md` once the review gates pass, following its
comments, with actual verification and the Review record in its For agents
block, and the screenshots attached in its Screenshots section. If the runtime can
link a PR to the session, do so as the next call. Then fill the record's
`Delivered` field with the PR URL in one more commit and push it; that
record-only commit needs no further review. Confirm the PR URL and that its
head SHA equals your local head. If GitHub access blocks delivery, finish
local work, prepare the exact PR body, and report the needed access without
asking for a raw token in chat.

A delivery subagent hands the open PR and current task record to its
top-level parent here, per `references/delegation.md`'s _PR handoff_. The
parent owns steps 5–6.

Completion: a real PR for the reviewed head, or a concrete external blocker
with a committed local result and prepared PR body.

## 5. Hand the PR to the owner (or babysit it when asked)

By default, read the PR's checks once after opening it and report: the PR URL,
its head, the checks' current state and that it awaits the owner's review. Do
not watch the PR for events, answer later review comments or merge. A check
that has already failed on the head is diagnosed and, when it is an in-scope
defect, fixed, re-verified and pushed under the review rules in
`delegation.md`; otherwise report it.

When the user asked for babysitting or merging, read `references/pr-watch.md`
and follow it instead: watch the PR to done, fix actionable failures and
findings in scope, and squash-merge when the user authorized merging.

Completion: the PR open and reported with a current-head checks snapshot; or,
when babysitting was requested, merged with its merge SHA recorded, done and
left unmerged at the user's request, or blocked with its blocker reported.
Never call an unfinished or blocked PR done.

## 6. Run one retrospective

After step 5, read `.agents/skills/retro/SKILL.md`. Review the session's actual
friction and implement its evidence-based improvements on a new branch from the
default branch. Keep the original PR unchanged. Use a new PR when there is an
independent improvement; a no-op is valid with evidence.

Retro PRs receive validation, the same independent reviews and the same PR
policy (raised and left open unless merging was requested), but **no further
retro**. Explicit later requests can run one. If the platform cannot branch
safely without losing work, preserve a handoff and report the blocker.

Completion: a separate reviewed retro PR, or a documented no-op or external
blocker. Report both PRs, actual checks, screenshot paths, remaining
limitations and follow-ups. End the task; do not loop into another story.
