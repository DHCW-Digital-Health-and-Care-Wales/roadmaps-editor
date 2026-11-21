# Documentation

Requirements, analyses, decisions and runbooks live here; rules about code
live in the `AGENTS.md` beside that code. Never start a backlog, chore list,
spec or plan outside `docs/`, except a `wayfinder` map: it charts decisions as
GitHub issues, and its destination lands here as records.

## Layout

| Path                  | What goes in it                                                                                  |
| --------------------- | ------------------------------------------------------------------------------------------------ |
| `GLOSSARY.md`         | The domain vocabulary (`.agents/skills/domain-modeling/GLOSSARY-FORMAT.md`)                      |
| `adr/`                | One decision per `ADR-<nnn>-<kebab-title>.md`, indexed in `adr/README.md`                        |
| `backlog/README.md`   | The index: epics with status, then standalone chores and defects                                 |
| `backlog/<epic>/`     | An epic `EPC-<nnn>-<kebab-title>/`: `README.md`, `delivery-notes.md`, live stories `STY-<nnn>-…` |
| `backlog/chores/`     | Live chores `CHO-<nnn>-…`: work with no user-facing change                                       |
| `backlog/defects/`    | Live defects `DEF-<nnn>-…`                                                                       |
| `backlog/_archive/`   | Terminal records, mirroring the live tree (`<epic>/`, `chores/`, `defects/`)                     |
| `backlog/_templates/` | Templates for every record type, and the status lifecycle                                        |
| `backlog/personas/`   | Who the product is for, one file per persona; read before UX, copy or a new story                |
| `analysis/`           | Investigations written to reach a decision; `delivery-runs/` has run notes                       |
| `operations/`         | Runbooks and authoring policy for what a person or agent does by hand                            |

Put nothing else in the root of `docs/`. A record's ID is a prefix, a dash and
three digits: `EPC` epic, `STY` story, `DEF` defect, `CHO` chore (e.g.
`STY-010`; ADRs match, as `ADR-001`). Each prefix is one series across the
whole backlog, never per epic, so a story keeps its ID if it moves epic. Take
the next free number across the live tree, `_archive/` and open PRs' files
(`gh pr list --state open --limit 200 --json files --jq '.[].files[].path'`).

## Stories, chores, defects and epics

- Start from the template for the record's type in `docs/backlog/_templates/`.
  With `status-lifecycle.md` they own the file naming, metadata, section order
  and lifecycle, including what Done means and that a record is never rewritten
  or deleted. Keep the section order, so an agent can reach a section without
  reading the whole file.
- A record in a terminal status (Done, Won't fix, Won't do, Superseded) moves to
  `_archive/` in the same change that sets it, and its row in the epic or index
  is marked, not deleted. An epic whose rows are all terminal moves too.
- A record that departs from its claim says so in Delivery; an owner's change
  of mind is a Decisions entry. Never reword the Acceptance criteria.
- After any record change (an owner's answer, a moved obligation, a new or
  edited scenario), `grep` its IDs and terms across the epic, stories,
  analyses and glossary (a term of several words as
  `rg -n -U -i 'group\s+assignment' docs`, since wrapped prose splits it
  across lines), and fix every statement it makes false, including a claim
  that a field or stored state exists without naming the record that provides
  it. Search the status words as well, with their inflections
  (`rg -n -i 'undecided|no selection|still open|stay(s)? open|remain(s)? open|wait(s)? for|awaiting|unselected|not selected|not yet' docs`,
  leaving `_archive/` alone; triage the hits), since a decision leaves
  "waits for" and "undecided" claims in intros and gate paragraphs. An answer
  that changes another record's contract goes into that record's Decisions,
  not only the one it was raised in; one that makes a record need another's
  behaviour also sets its Depends on, and the epic's table and Sequencing.
- A defect found while delivering anything is recorded in its own file in
  `backlog/defects/` with Status `Needs triage`, listed under Defects in
  `backlog/README.md` (and in its epic's `## Defects`, if it belongs to one).
  Where the right outcome is a product choice rather than a fault against a
  written scenario, its Open questions say so. The owner triages it before
  anyone works on it.
- A finding a delivery declines to fix, where the owner may later pay the cost,
  becomes a chore with Status `Proposed`. An improvement idea nobody has
  accepted becomes a record with Status `Needs grilling`.
- **`delivery-notes.md`** beside an epic's `README.md` carries what only
  agents working on that epic need: a gotcha the next story will hit, a check
  its reviewers make, a fixture or seam its stories share. The first delivery
  with such a note creates it; every delivery agent and reviewer on the epic
  reads it. Keep each note a short bullet, current, not a story's history
  (that is the record's Delivery and its PR). When the epic closes, the
  delivery that archives it moves each note that holds repo-wide to its
  narrowest home (`docs/operations/authoring-agent-instructions.md`, _Where it
  goes_), handing one whose home is a guide file to its retrospective, and
  archives the file with the epic.
- The bootstrap stories in `_archive/EPC-001-bootstrap/` predate the templates and keep
  their legacy format.

## Analyses

An analysis decides nothing. It ends with options, a recommendation and a
_Decisions needed_ table; the decisions go to an ADR or a story, and the
analysis gains an _Outcome_ section saying where. A delivery run summary under
`analysis/delivery-runs/` follows that folder's `_template.md` instead.

## ADRs

- Follow `.agents/skills/domain-modeling/ADR-FORMAT.md` for an ADR's naming,
  shape, status lifecycle, supersession, in-place amendment and when a
  Proposed one may be built on.
- Record an ADR as Accepted only on the owner's word: match each decision to an
  answer the owner gave, or to a question the owner explicitly left to the
  agent, and write the ADR from those answers only. Ask the owner about the
  rest.
