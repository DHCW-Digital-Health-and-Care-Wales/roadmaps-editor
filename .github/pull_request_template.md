<!--
The owner reads everything above the For agents block, often on a phone, to
judge what users now see and which trade-offs were made, and tells an agent
what to change. Agents read all of it. Text sections are bullets, never
tables, so they wrap on a phone; only a before/after screenshot pair is a
table. Delete each section, heading included, that has nothing to say.
-->

Delivers `<record path>` (<epic>) · <binding ADRs, or "no binding ADR">

## Summary

<!--
At most three sentences: what users can now see or do. For a change no user
sees, start with "No user-visible change:" and say what changed and why, then
skip Behaviour, Screenshots and Copy.
-->

## Behaviour

<!--
One bullet per scenario of the record. Evidence cites a screenshot by its
label ("S1 · desktop", or "S1, S3 · phone" for one capture showing several
scenarios) or names a test.
-->

- **S1 <scenario>:** <what users now see>. _Evidence:_ S1 · desktop.
- **S2 <scenario>:** <what users now see>. _Evidence:_ S2 · phone.

## Screenshots

<!--
Each capture's caption is bold, above it, and starts with the label Behaviour
cites: its scenarios and viewport, then the screen, state, theme and language.
A before/after pair sits side by side in a two-column table; a new screen or
state is one full-width image, its caption ending "· new". Reference local
files; gh --attach uploads them
(.agents/skills/implement-story/references/screenshots.md).
-->

**S1 · desktop · <screen> · <state> · light · en**

| Before                          | After                         |
| ------------------------------- | ----------------------------- |
| ![Before: <screen>](before.png) | ![After: <screen>](after.png) |

**S2 · phone · <screen> · <state> · dark · en · new**

![<screen>, <state>](new.png)

## Copy

<!--
Only the strings the owner would judge, in English with the Welsh beside it:
titles, empty states, errors and action labels a user meets. Put every other
changed string in the collapsed list. Welsh is machine-assisted until a fluent
speaker reviews it.
-->

- `<key>`: <English> · _cy:_ <Welsh>

<details>
<summary>Other changed strings</summary>

- `<key>`: <English> · _cy:_ <Welsh>

</details>

## Decisions

<!--
One bullet per choice another engineer could reasonably have made
differently. Beyond each decision's Cost, add a "Risk:" bullet only for a
change to authentication, token handling, OAuth scopes, what is read from or
written to Google, or the deployment.
-->

- **<decision>:** <what was chosen>, over <the alternative>. _Why:_ <reason>.
  _Cost:_ <cost or risk>. _Reversible:_ <yes, or how not>.

## What's next

<!--
Link each record. Added: the defects, chores and follow-ups this PR records.
Needs you: open questions, grilling, defects to triage, a Proposed ADR, the
merge itself. Unblocked: the work this PR lets start. Write "none" after a
label with nothing, or delete the section when all three have nothing.
-->

- **Added:**
- **Needs you:**
- **Unblocked:**

<details>
<summary>For agents</summary>

### Verification

<!--
Each check run, with its result and counts (typecheck, lint, format:check,
test, build, test:e2e, and any other); each check not run, and why; each
exception to a rule, with its reason.
-->

### Review record

<!--
Per reviewer (correctness: Opus and Sol; quality: Sonnet; security: Fable, on a
security-relevant PR, or why it did not run): rounds and pinned
heads; each finding with its fix, or its decline and reason; the fixes after
the review cap; whether the final fresh pass ran, and why.
-->

### How to see it

<!-- The route (e.g. #/roadmaps/<id>) and the fake GIS/Sheets state that
reach the change, or the E2E spec that does. -->

### Operations

<!-- Environment variable names (never values), Google Cloud or GitHub Pages
settings, manual steps, rollback. -->

### Story record

<!-- Where the departures and the contract for dependent work are recorded:
the record's Delivery section, and the epic's delivery-notes.md for anything
only that epic's later stories need. -->

</details>
