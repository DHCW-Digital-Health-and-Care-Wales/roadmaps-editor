---
name: code-review
description: >-
  Review a diff, branch or PR for correctness: requirements coverage, regressions,
  async state, security, untrusted data and runtime contracts. Use for a code review
  and before raising a PR; maintainability belongs to quality-review.
---

# Code review

Judge whether the change does the right thing and preserves existing behavior.
`quality-review` owns standards and maintainability under a separate verdict.

Invoke as `/code-review [target] [--comment]`. The target is the current branch
against `origin/main` with staged, unstaged and relevant untracked files (the
default); a PR number; a branch, commit or tag against its merge-base with
`origin/main`; or an explicit base and head. For a PR number or `--comment`,
read `references/pr-target.md`. Otherwise report in the conversation only: do
not post, change code, merge or message other people as part of reviewing.

## Working order

1. **Pin the scope.** Take the base/head SHAs and diff command the brief
   supplies (`.agents/skills/implement-story/references/delegation.md`);
   otherwise resolve the target to SHAs against the merge-base, with
   working-tree and untracked files when defaulted, which a three-dot diff
   misses. Keep the checkout read-only; read other revisions with
   `git show <sha>:<path>`. A bad ref is a scope error; an empty scope is
   "nothing to review", not a pass. Read every changed line of the scope, docs
   included, a file or a directory at a time. An output too long for one
   command is cut or saved to a file, and one record's diff can be that long:
   read the saved file with the file-reading tool, or the same diff a range of
   lines at a time, until every line has arrived whole. A diff read through
   `head`, `cut` or a pattern filter still has lines unread.
2. **Find the requirements.** Read the user's instructions and the linked
   story, defect or chore (`docs/backlog/`, ids `STY-<nnn>`, `DEF-<nnn>`, `CHO-<nnn>`) with
   its acceptance criteria, the PR body and the binding ADRs in `docs/adr/`,
   following commit and PR references. Read the root `AGENTS.md`, the
   `AGENTS.md` along each changed path's directory ancestry and the shared
   conventions files those guides point to, the epic's `delivery-notes.md`
   when there is one, and each _Repo contract_ below the diff reaches; repo
   invariants outrank generic preferences. Without a spec, say what could not
   be verified and continue with regressions and contracts.
3. **Trace behavior.** Open touched files beyond the hunks, their callers,
   hooks, providers, adapters, schemas and tests, and follow inputs through
   state, caches and rendered output. Read a definition before assuming a
   name, type, CSS class, fake or comment proves behavior. Trace quality-review
   handoffs too.
4. **Apply the lenses** (general, then each area the diff reaches), labelling requirements and regression
   findings separately. The docs a diff changes, which is all of a docs-only
   one, are reviewed against `docs/AGENTS.md` (the records guide): do the
   records agree with the code and each other, is a status or acceptance claim
   true, and does each test a record, PR body or commit cites as evidence
   exist under that name and assert what is claimed? Open it: a neighbour that
   renders or calls the same code without asserting the claim is a gap. Invent
   no other risk.
5. **Verify plausible findings** with a concrete trigger and an observed or
   code-derived failure path. Run a focused test, minimal reproduction or
   computed-style check when useful, keeping scratch outputs and caches under
   `/tmp`:
   - Editor or public site: `cd apps/<editor|public-site> && ./node_modules/.bin/vitest related --run <files> --no-cache --fsModuleCachePath /tmp/<dir>`.
     Run binaries from `./node_modules/.bin/`, never through pnpm (`pnpm exec`
     or a `pnpm <script>`), which can reinstall the checkout's `node_modules`
     under the agent that shares it.
   - API: `cd apps/api && uv run --locked pytest -o cache_dir=/tmp/pytest-cache <test_file>`
     (only when no database container or repo write is needed).

   Never run a command that changes state (a commit, a push, a deploy, a merge).
   Passing tests are evidence, not proof; never claim a check you only read.

6. **Filter.** Report defects the change introduces or materially exposes, tied
   to a changed line or affected contract, after ruling out an intentional
   exception. A rule ESLint, TypeScript strict or the i18n catalogue types
   already enforce (see _Tooling already enforces_) is not a finding unless the
   change disables or evades it. List an unrelated existing defect under
   _Handed off_. Drop hypothetical, preference-only and duplicate findings.

## Requirements

For each relevant requirement, distinguish implemented, partial, missing and
unverifiable; quote it for a mismatch and show the implementation path.

- Trace each scenario through every applicable state (for the editor: auth states
  `initializing`, `ready`, `connecting`, `connected`, `expired`, `error`; for the
  public site: JS-off prerender and hydrated states; for the API: unauthenticated,
  invalid, not-ready and failure paths), width, language, theme and entry point it
  names to the control or response the caller meets, including what completes a
  branch that hands off or defers. Where a change replaces a surface, carried-over
  behavior may be what the story changes.
- Look for omitted refusal and expiry branches, empty and loading states, a
  failed read shown as "no results", an error shown as an empty list, mobile
  layouts that drop a control (in the editor, the header's account menu offers
  Connect or Reconnect, but a signed-out page still needs its own), and behavior
  beyond the request. Scope growth is a finding only when it creates a concrete
  risk or contradicts the request.

## Tooling already enforces

Do not spend findings on rules CI already enforces; inspect the touched app's
config (`eslint.base.ts`, `apps/editor/eslint.config.ts`,
`apps/editor/build/design-token-lint.ts`, `apps/editor/build/e2e-lint.ts`,
`apps/public-site/eslint.config.ts`, `apps/api/pyproject.toml`,
`apps/api/tools/check_transactions.py`) and flag only evasions (`eslint-disable`,
`# noqa` without reason, `@ts-expect-error`, casts, re-exports, moved files) and
these blind spots:

- **Literal copy**: `i18next/no-literal-string` checks JSX and configured
  attributes in `src/**/*.tsx`, not `.ts` files, non-configured props or strings
  built in hooks; catalogue parity checks keys, not Welsh translation accuracy.
- **Design tokens**: `apps/editor/build/design-token-lint.ts` checks default
  class/style sites, not class strings stored outside configured variable names
  or style objects passed under non-`style` props.
- **API checks**: `apps/api/tools/check_transactions.py` matches direct
  `.commit()`/`.rollback()`/`.begin()` calls in routes and repositories, not
  renamed wrappers; `ruff` and `ty` do not verify log-value provenance or
  uvicorn-only behaviour.

## Lenses

Apply every general lens below, then read each area's lenses the diff reaches:

- `references/auth.md`: editor sign-in, session, access token or anything that sends it.
- `references/data.md`: editor repository, adapter, parser, query or mutation.
- `references/ui.md`: editor route, component, copy, styles or base path.
- `references/public-site.md`: anything under `apps/public-site/`.
- `references/api.md`: anything under `apps/api/`.

General lenses:

- **Every path to an invariant.** For each invariant the change relies on or
  alters (a layer boundary, the auth-scoped key root, the `enabled` gate, the
  token-in-memory rule, a feature's error mapping), enumerate every path that
  reaches it and show each one's handling: each caller that can raise
  `unauthenticated`, each query that fetches with the token, each place that
  reads `AuthState`, each test or fake naming a removed export.
- **Logic and contracts.** Trace branching, null/empty/zero values, boundaries,
  ordering, absent versus explicit-empty fields, and runtime response shapes
  against callers. Types prove neither the endpoint's answer nor the business
  decision (a Sheets response with no `sheets`, a hidden sheet, a zero-length
  title, an id that is not an integer); preserve intentional status and error
  mappings.
- **A Product Lead's work is never lost or misrepresented.** For a change that
  edits roadmaps or roadmap items, trace a failed or partial publish,
  navigation away with pending edits, two tabs or two Product Leads on one
  roadmap, an expired session mid-edit, and a stale read overwriting a newer
  publish. Each ends with the edits kept or the loss stated, never silently
  dropped. Check that nothing reaches the data source before Publish, and that
  what the editor shows as published is what the data source holds.
- **The public site reads the same data.** The data source is shared with a
  separate public-site app, so a change to what is written, its shape or its
  location is a contract change: the record and PR must say so, and existing
  rows written before the change must still read correctly in both apps.
- **Async state and lifecycle.** Consider navigation A→B before A resolves,
  out-of-order responses, unmount, token expiry mid-request, reconnect during a
  fetch, retries with back-off (a 5xx or network error shows only after about
  3 s), duplicate submission and React StrictMode double effects (dev aborts and
  repeats the first fetch). Check effect dependencies, cleanup, and
  `useSyncExternalStore` snapshots (identity changes only on change; a
  selector returning a fresh object each call loops). A reaction keyed on an
  event (focus arriving, a mount, a transition ending) is edge-triggered: check
  it also runs when the state the event would signal already holds as it is
  armed. Where a dialog, menu, open form or pending action outlives the read
  that opened it, a refetch, expiry or route change must neither unmount it,
  swap the record it acts on, nor leave what it shows stale or at odds with what
  it will submit. Every value an open form can hold keeps an option naming it
  (options from the read its value came from, or one kept for a value its list
  has lost), since a native `<select>` shows its first enabled option for a
  value it lacks.
- **Evidence covers less than its claim.** Where code or a test infers a fact
  from indirect evidence (a first fetch, a status badge, a refusal that more
  than one check returns, a fake that always grants, "all tests pass" when E2E
  was skipped, a Welsh string the author cannot read), name a realistic input
  that makes it lie, and check the code reads the effect itself or reports the
  result as unknown. A test of one check fails without it: its case gets past
  every earlier one, and it asserts what no other path produces. The fakes
  agree with Google only as far as they were written to: a new Sheets or GIS
  call needs the fake extended, and the live behavior stays unverified until
  the manual check in `docs/operations/google-cloud-setup.md`.
- **Tests (ADR-006).** Vitest and Playwright specs exercise the failure path
  through real contracts and fail before a behavioral fix. Component tests go
  through `renderWithProviders` (real `AppProviders`, fake `AuthClient`,
  in-memory repository) and query by role and name, scoped to `main`/`banner`;
  adapters run the shared repository contract; deferred responses expose races
  immediate mocks hide; fake timers are paired with `vi.setSystemTime`. E2E
  imports from `./fixtures/test` only, uses the fakes (`gis`, `sheets`), has no
  sleeps, navigates with relative URLs, and extends the fakes rather than
  loosening the hermetic guard or the token-persistence recorder. Report tool
  diagnostics only if they mask a defect.

## Repo contracts

Read each where the diff reaches it; this skill does not restate them.

- `apps/editor/AGENTS.md`, `apps/public-site/AGENTS.md`, `apps/api/AGENTS.md`,
  and `apps/typescript-react-conventions.md`: each app's layering and conventions.
- `apps/editor/tests/e2e/AGENTS.md` and `apps/editor/src/styles/AGENTS.md`:
  editor E2E fixture API, hermetic guard and design-token rules.
- `docs/adr/` (index in its `README.md`): binding architecture decisions across
  all three apps. A deviation updates or supersedes the ADR in the same change.
- The epic's `delivery-notes.md`: checks that hold only for that epic.
- `docs/AGENTS.md`: the records guide, for backlog, ADR and run records.
- `docs/backlog/`: the story, defect or chore being delivered, with its
  acceptance criteria and status.

## Findings and grading

Give each finding every field of the report format below. State any
uncertainty; never present an unverified theory as an observed failure.

| Priority | Meaning                                                               |
| -------- | --------------------------------------------------------------------- |
| P0       | Immediate broadly applicable security/data-loss/outage defect         |
| P1       | Serious reachable failure that should block this change               |
| P2       | Concrete correctness defect with limited reach or an ordinary trigger |
| P3       | Minor but reproducible correctness issue                              |

A token written to storage or a URL, or one sent to another origin, is P0 or
P1. Choose priority from impact and reach, not from how strongly a rule is
worded. No quota: return no findings when no actionable defect is established.

## Report format

```text
Code review — <target>
Scope: <base/head SHAs, working-tree scope, diff command>
Requirements: <sources, coverage and unavailable requirements>
Verdict: <correctness assessment and any verification limits>

Requirements findings
- [P#] <title> — path:line
  Requirement: <quote/source>
  Trigger → failure: <concrete path and impact>
  Evidence: <code trace or actual check>
  Fix/test: <smallest useful correction and regression case; in a hand-written
  parser or scanner, first whether a structured tool (a Zod schema, a type, an
  existing linter, a parsed config) covering the same cases replaces it>

Regression findings
- <same evidence format, or None>

Verification: <checks actually run/read; relevant checks unavailable>
Handed off: <quality concerns or unrelated existing defects; or None>
```

When re-reviewing, state whether each earlier finding is fixed, still open or
unsupported, then review the changed scope. The implementer acts on findings as
`.agents/skills/implement-story/references/pull-requests.md` sets.
