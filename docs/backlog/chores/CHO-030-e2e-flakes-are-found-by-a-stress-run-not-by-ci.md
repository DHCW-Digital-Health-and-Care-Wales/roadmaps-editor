# CHO-030: E2E flakes of one kind are found by an audit and a stress run, not one CI failure at a time

- **Status**: Needs grilling — raised on the owner's question after STY-081's retrospective
  (DEF-024); it adds a guide rule and, if the owner chooses (Q1 b), a stress script
- **Type**: Chore
- **Area**: E2E + Docs
- **Epic**: standalone
- **Depends on**: none; DEF-024 (Needs triage) fixes `publishOnce` first, and until it
  does the audit counts that flake as known
- **Binding ADRs**: none
- **Suggested model**: Sonnet — a search over `tests/e2e`, a stress script run, and one
  guide line, once the owner chooses
- **Delivered**: _(add on delivery)_

## Summary

E2E tests that act before the UI has settled have been found one CI failure at a time.
Three are confirmed flakes: DEF-016 (the item dialog's focus tour counted a focus guard,
found in local runs), DEF-024 (`publishOnce` returns before the publish notice takes
focus; cause suspected, not proven) and DEF-025 (a side panel test measures the panel
before its slide has run; fixed in #218 by `settledBoxes`, `tests/e2e/fixtures/layout.ts`,
which a popup's geometry read now uses). The same kind has shown in component tests (DEF-013 a
dialog's opening focus; DEF-022 under load, not seen in CI; CHO-018 once in CI, on a
clock tick), and `side-panel.spec.ts:256` (session warning) was seen to flake three
times in CI, with no record. In CI, 11 of 29 E2E runs had a flaky test (Measurement).
DEF-021 was a real layout defect, not a test. Each flake costs a failed run, a retry and
a retrospective. Done: the owner has chosen whether to look for the rest of the E2E kind
on purpose, and the E2E guide says how a helper must settle. Component tests are out of
scope here (Out of scope).

## Measurement

The audit is not done yet: it is the first step. At the delivery's commit, run these and
judge each hit by whether the next assertion can run before the thing it needs has
finished (a notice taking focus, an animation ending, a menu opening):

| Area              | Search or run                                                                                                                                                                                                       | How to judge a hit                                                                           |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Shared helpers    | read each export of `tests/e2e/fixtures/` that triggers a close, publish or navigation                                                                                                                              | it returns before the focus or notice its action causes has arrived                          |
| Focus right after | `rg -n -B3 -e '\.focus\(\)' -e toBeFocused tests/e2e`                                                                                                                                                               | the line before is a click, keypress or helper that moves focus on its own                   |
| Popups' boxes     | `rg -l animate-in src/components/ui` lists the popups that animate in (dialog, alert dialog, sheet, menus, tooltip); then `rg -n -e 'boundingBox\(' -e getBoundingClientRect tests/e2e` in each spec that opens one | the box is read by a call other than `settledBoxes`, or two boxes are read in separate calls |
| Load              | `./node_modules/.bin/playwright test <spec> --repeat-each=20 --workers=12` per spec on an 8-core host (DEF-024's Reproduce used 40 repeats of one case); 44 specs at `843acf2`, so time it on one first             | any failure that `--workers=4` does not show                                                 |

Seen in CI so far: every finished CI run with an E2E job, 2026-11-19 18:14 to
2026-11-20 17:09 UTC (29 runs, `gh run list --workflow ci.yml -L 60`), read from each
E2E job's check-run annotations. All 11 runs with a flaky test passed on retry. Line
numbers are the spec's at that run:

| Test                                                   | Runs with it flaky | Failure                                                               | Record                                        |
| ------------------------------------------------------ | ------------------ | --------------------------------------------------------------------- | --------------------------------------------- |
| `moved-travel.spec.ts:207` (keyboard "far down")       | 3                  | focus not on Move                                                     | DEF-024                                       |
| `item-tags.spec.ts:282` (compact row, title wraps)     | 4                  | "Not laid out" (`fixtures/layout.ts` `boxOf`)                         | none                                          |
| `side-panel.spec.ts:261`, then `:256` (S9)             | 3                  | the session warning still shown after it should close                 | none                                          |
| `pinned-dialog.spec.ts:303` (long title added)         | 3                  | a dialog part not in view (line 328)                                  | none; #218 settled its reads, cause not shown |
| `roadmap-controls.spec.ts:271` (Publish roadmap)       | 1                  | timeout waiting for a stuck row's button (`fixtures/roadmap-page.ts`) | none                                          |
| `side-panel.spec.ts:134` (tall screen, form that fits) | 1                  | the panel measured mid-slide                                          | DEF-025 (fixed, #218)                         |

A load run does not find every kind: DEF-025 passed 205 loaded runs, and only holding
the page's animations at their start showed it (its Reproduce). Its sweep found the
navigation drawer's reads (`shell-navigation.spec.ts`, `unpublished-changes.spec.ts`) only
after two reviewers had: a search by spec missed a popup, a search by component (the
Popups' boxes row) does not.

## Acceptance criteria

### S1: The audit and the stress run have been done once

**Given** the default branch **When** the searches above are run and each hit judged
**Then** each flake they find is fixed in its helper, or recorded as a defect, and the
Delivery lists what was searched and found

### S2: The E2E guide names the rule

**Given** `tests/e2e/AGENTS.md` **When** an agent writes a helper that closes a dialog or
publishes **Then** it says the helper returns only once the focus or notice its action
causes has arrived

## Open questions

- **Q1**: Is a stress run part of delivering a test change, or a one-off?
  - (a) One-off, with the guide rule (recommended): the audit finds the existing cases and
    the rule stops new helpers adding more.
  - (b) A script (`pnpm test:e2e:stress`) a delivery runs on the specs it touched. It
    catches new cases before CI, and adds a command and minutes to every test change.

## Decisions

## Out of scope

DEF-024's own fix to `publishOnce`, DEF-025's to the side panel spec's helpers, the CI
runner's package mirror (CHO-029), and Vitest component tests (DEF-013, DEF-022,
CHO-018 were their own cases).

## Delivery _(add on delivery; as in `story.md`)_
