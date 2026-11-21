# Review and publish a branch

1. Collect the screenshot manifest per `screenshots.md`; keep image files out
   of commits. The PR's base is the remote default branch, or the
   prerequisite's branch in a stacked delivery the user asked for; resolve its
   full SHA. Record the merge-base with it and the implementation head.
   Confirm the worktree is clean after committing the intended changes;
   include untracked files deliberately if reviewing before the commit. Every reviewer gets the same snapshot.
2. Dispatch the reviewers `delegation.md` sets, each reading its skill. Store their reports
   independently. Resolve every actionable finding or record its
   evidence-backed disposition in the PR. A reviewer's _Handed off_ items take
   the same: fix one in scope, give one outside it a backlog record
   (`docs/AGENTS.md`), or decline it with a one-line reason in the Review
   record. An unresolved P0/P1 from either
   correctness reviewer, or from the security reviewer, blocks a passing verdict. Re-review the
   final head after fixes, in the rounds `delegation.md` sets.
3. Write the PR body to a temporary file from
   `.github/pull_request_template.md`, following its comments. The title is a
   conventional commit subject naming the record, e.g.
   `feat(roadmaps): STY-010 show each roadmap's owner`.
4. Push the task branch, rebased per _Update a branch_ when its base has
   moved. Do not create a duplicate if a PR already exists. Create the PR with
   `gh pr create --base <base branch> --head <branch> --title '<title>' --body-file <body-file>`,
   adding one `--attach` per screenshot (`screenshots.md`), then read back the
   hosted image URLs. Link the PR to the session as the next call when the
   runtime supports it. Confirm the returned URL, and that the PR's head SHA
   (`gh pr view <n> --json headRefOid`) equals the reviewed local head
   (`git rev-parse HEAD`). A mismatch means the push sent another commit: a
   commit made on a detached HEAD reaches no branch.
5. Stop there by default (SKILL step 5). Merge only through `pr-watch.md`, when
   the user asked for merging, and never when the user said to leave it
   unmerged. Never approve, deploy, or change branch protections. If required
   checks or independent reviews are unavailable, report them and create only
   a draft PR (`--draft`) with accurate limitations; a draft is never merged.

## Update a branch

Bring a branch up to date with its base by rebasing, even when its PR is
open, so its history stays linear; never merge the base in.

1. Read the branch's remote head before rebasing, the lease: your last push,
   or the PR's `headRefOid` when you take the branch over. Make the local
   branch contain it (`git merge-base --is-ancestor <lease> HEAD`), or the
   push removes the commits it lacks: start a taken-over branch with
   `git checkout -B <branch> <lease>`, and rebase your own work onto a lease
   it lacks.
2. Rebase onto `origin/<base branch>`. When a stacked prerequisite has been
   squash-merged, replay only your own commits:
   `git rebase --onto origin/<new base> <prerequisite's last head>`.
3. Re-run the verification and re-pin the reviewers' SHAs (`delegation.md`).
4. Push with `git push --force-with-lease=<branch>:<lease>`, never a plain
   `--force`, so a push made since you read the lease is refused rather than
   overwritten. After a refusal, start again at step 1.

Git push access and GitHub API access are distinct. Test the specific
operation before requesting configuration. A CLI login error or an unset raw
token is not proof that Git access is missing. Reuse injected authentication;
never extract credentials or request raw credentials in chat.

A rejected network operation is a blocker to diagnose. Finish and commit useful
local work, retain the prepared body and review reports, and report the exact
missing destination or permission. Retest after a meaningful configuration
change. No retro branch should discard or contaminate unpublished primary work.
