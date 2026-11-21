# ADR-016: One pnpm workspace holds the editor, the public site and the API

- Status: Accepted — owner, 2026-11-21; drafted from the owner's answers in the
  EPC-022 monorepo grilling (2026-11-21). ADR-007 is amended by the stories that make
  each part true (_Consequences_).
- Date: 2026-11-21

## Context

EPC-022 turns this repository into a monorepo for the editor and a FastAPI service
(ADR-015, ADR-017). The public site lives in its own repository, `product-roadmaps`,
and parses the spreadsheet format the editor writes: the format is a contract kept in
step by hand across two repositories, and the editor already copies the site's fixture
CSVs. Both sites are static and published on GitHub Pages, which serves one site per
repository from one origin for the whole organisation
(`https://dhcw-digital-health-and-care-wales.github.io`). The editor's `main` is
unprotected; `product-roadmaps` protects its `main` with code-owner review. ADR-015
moves the public site to the API's read later, with each tenant under its own address.

## Decision

### Layout and name

- **The repository is renamed `roadmaps`** before the workspace move, as a change of
  its own. The editor's address becomes `/roadmaps/`; the old `/roadmaps-editor/` gets
  no redirect, and Product Leads are told the new address.
- **One pnpm workspace:**

  ```
  apps/editor/        the editor (Pages: /roadmaps/)
  apps/public-site/   the public site (Pages: /product-roadmaps/, published by product-roadmaps)
  apps/api/           the FastAPI service (ADR-017)
  packages/api-types/ the API's generated types and zod/mini schemas (ADR-017), from STY-092
  ```

### The public site

- **Its code joins now, with its history.** On a branch of `product-roadmaps`' history,
  its files are moved with `git mv` into `apps/public-site`; that branch is then merged
  with `--allow-unrelated-histories`, keeping the original signed commits and SHAs. For
  that one pull request the repository setting and the ruleset's merge methods allow a
  merge commit, or the owner merges through bypass; both are restored afterwards.
- **It adopts the workspace's toolchain:** pnpm, Node 26 (`.nvmrc`) and the root
  Prettier style; the reformatting commit is listed in `.git-blame-ignore-revs`.
- **`product-roadmaps` becomes the public site's deploy repository.** Its deploy
  workflow runs nightly and by hand, checks out this repository's `main` at its head,
  builds `apps/public-site` and publishes it, keeping today's split: the build job holds
  no Pages permission and the deploy job runs no project code. Its base path stays
  `/product-roadmaps/`. There is no cross-repository trigger and no secret, so a merged
  change goes public at the next nightly or manual run. Its `check-sheet.yml` stays
  there for sheet editors, rewritten to check out this repository in the same way.
- **The editor and the public site share one copy of the spreadsheet fixtures,** read by
  both apps' tests, so a format change fails both in one pull request. No contract
  package: ADR-015 retires the format when the public site reads the API.

### Who may change `main`

- **A ruleset on `main`, copied from `product-roadmaps`' and applied to the whole
  repository:** a pull request, one code-owner approval, approval of the last push,
  stale approvals dismissed, no force-push and no deletion; plus required CI checks and
  signed commits. `CODEOWNERS` names the owners for `*`. The owner keeps bypass.

### Workspace tooling

- **pnpm alone runs tasks** (`pnpm -r`, `pnpm --filter`); no Turbo.
- **pnpm's default resolution, never `shamefully-hoist`,** with shared versions named
  once as pnpm `catalog:` entries in `pnpm-workspace.yaml`.
- **One root Prettier config**, the editor's style. **Each app keeps its own
  `eslint.config.ts`**, found by ESLint's lookup nearest each file; the settings both
  React apps share sit in one root `eslint.base.ts`, extracted when the public site
  arrives.
- **Git hooks:** on commit, Prettier, the touched app's ESLint and ruff on staged files;
  before a push, the TypeScript typecheck and ty.
- **knip** checks unused files and exports, from `packages/api-types` onwards.
- **Dependabot** updates GitHub Actions, pnpm and uv, each grouped monthly.

### CI

- **One `ci.yml`**: a `changes` job picks the jobs for a pull request by path (editor,
  public site, API, docs-only); pushes to `main` and manual runs run every job. The
  ruleset requires fixed job names.
- **Workflow files are linted** with actionlint and zizmor.
- **End-to-end tests live in each app** and run against that app alone; a root `e2e/`
  workspace arrives with the first journey that crosses apps or the real API.

### Agent guides

- **The root `AGENTS.md` keeps the rules that hold across the repository** and gains a
  routing table from each area to its guide. The editor's rules move to
  `apps/editor/AGENTS.md`; `apps/public-site/AGENTS.md`, `apps/api/AGENTS.md` and
  `apps/api/tests/integration/AGENTS.md` are added.
- **Live records and guides follow the move;** archived records keep their old `src/…`
  citations, since a record is never rewritten.

### Rejected

- **The public site joining later, with the API read:** the format would stay two pull
  requests in two repositories until then.
- **Both sites on one Pages site:** the public address would change now.
- **A cross-repository deploy trigger** (a GitHub App or a personal token): a secret and
  an App to run, for deploys the nightly and manual runs already cover.
- **A redirect repository at the old name:** taking the name ends GitHub's redirect of
  the repository's own links, issues and pull requests.
- **`git filter-repo` for the import:** rewrites every SHA, losing the signatures.
- **Moving `check-sheet.yml` here:** sheet editors would lose the place and link they
  use.
- **Turbo:** no package builds, so its task graph and cache have little to do.
- **`shamefully-hoist`:** imports work that a package never declared, until the wrong
  copy resolves.
- **A shared ESLint package:** an abstraction before there is duplication to share.

## Consequences

- **Accepted risks:**
  - The nightly deploy builds `main`'s head whatever its state, and the owner's bypass
    can merge past failing checks.
  - GitHub disables a public repository's scheduled workflow after 60 days without
    activity, and `product-roadmaps` will have none. Then neither merged changes nor
    published sheet edits reach the public site until someone re-enables it or the move
    to Google Cloud lands; the owner accepts this.
  - Required signatures apply to agents too: a cloud agent that cannot sign its commits
    cannot have them merged.
- **The shared Pages origin** cannot tell the editor from the public site, which loads a
  third-party analytics script, or from any other organisation site. Tokens stay in
  memory only, and a custom domain for the editor is a precondition of switching the
  deployed editor to the API: an input to the identity ADR (ADR-018, with ADR-020).
- **ADR-007 is amended by the stories that make each part true:** STY-085 the base path
  `/roadmaps/`, STY-087 CI as jobs per app, STY-088 the public site's publishing from
  `product-roadmaps`; `docs/operations/github-pages-deployment.md` follows each.
- **Follow-on work** (EPC-022): STY-085 (rename), STY-086 (workspace move), STY-087
  (tooling and the ruleset), STY-088 (the public site joins), STY-089 (shared fixtures).
