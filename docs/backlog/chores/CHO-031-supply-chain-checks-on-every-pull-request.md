# CHO-031: Supply-chain checks run on every pull request, and leaked secrets are refused at push

- **Status**: Proposed — agreed in the identity and authorisation grilling (owner,
  2026-11-21, D14), to deliver beside STY-087
- **Type**: Chore
- **Area**: CI/CD
- **Epic**: [EPC-022-monorepo-and-backend-foundation](../EPC-022-monorepo-and-backend-foundation/README.md)
- **Depends on**: none; it changes `ci.yml` and `.github/dependabot.yml`, as STY-087 and
  STY-090 do, so whichever lands later rebases
- **Binding ADRs**: none
- **Suggested model**: Sonnet — configuration with known shapes, observed in runs
- **Delivered**: _(add on delivery)_

## Summary

The repository is public and is about to gain a Python API, a second app and an
identity layer, but nothing checks its dependencies for known vulnerabilities, holds
back a just-published package version, scans the code statically beyond lint, or stops
a secret at push. STY-087 adds actionlint, zizmor and Dependabot for pnpm, STY-090
Dependabot for uv (ADR-016), and ADR-017 ruff's `S` rules; this chore adds the rest, for what the repository holds
when it is delivered, so the API's first dependencies arrive under the checks (analysis
[identity and authorisation](../../analysis/identity-and-authorisation.md), F9). Done
means each check below runs on a pull request, or is a repository setting that is on,
observed once.

## Measurement

At commit `86afe40`, 2026-11-21 (`gh api repos/DHCW-Digital-Health-and-Care-Wales/roadmaps-editor`
`--jq .security_and_analysis`, `.github/`):

| Area                         | Measurement                                                     | Verdict |
| ---------------------------- | --------------------------------------------------------------- | ------- |
| Secret scanning              | enabled                                                         | keep    |
| Push protection              | disabled                                                        | turn on |
| Dependabot security updates  | disabled; `dependabot.yml` updates GitHub Actions only, monthly | turn on |
| CodeQL                       | default setup not configured                                    | add     |
| Dependency review on PRs     | none in `ci.yml`                                                | add     |
| Lockfile vulnerability audit | none for `pnpm-lock.yaml`; no `uv.lock` yet                     | add     |
| Release cooldown             | none in Dependabot, pnpm or uv                                  | add     |

## Acceptance criteria

### S1: A secret pushed to the repository is refused

Secret scanning's push protection is on, and a test push of a provider-pattern secret
on a scratch branch is blocked; the run of it is recorded in Delivery.

### S2: A pull request that adds a vulnerable dependency fails

The dependency review action runs on every pull request that changes a lockfile and
fails on a known vulnerable version, observed on a scratch pull request. An OSV audit of
every lockfile the repository holds runs weekly and on `main`, so a vulnerability
disclosed in an existing dependency is found too.

### S3: The code is scanned statically

CodeQL runs for every language the repository holds (JavaScript/TypeScript and GitHub
Actions; Python once the API exists), on pull requests and on `main`.

### S4: A just-published version waits before it is taken

Dependabot's `cooldown`, pnpm's `minimumReleaseAge` (set in minutes) and, once the API
exists, uv's `exclude-newer` (with the uv version pinned, since relative values are
recent) hold back a newly published version for a stated number of days. A security
update younger than the window still lands: Dependabot's cooldown exempts security
updates, and pnpm's `minimumReleaseAgeExclude`, or a manual bump, covers its side.

### S5: Dependabot raises security updates

Dependabot security updates are on in the repository's settings.

## Decisions

- **D1** (owner, 2026-11-21, identity and authorisation grilling D14): a chore now,
  delivered beside STY-087, over folding it into STY-087 or deferring it to the API's
  first release.

## Out of scope

- zizmor with every audit on, and Dependabot's pnpm and uv ecosystems: STY-087 and
  STY-090 (ADR-016).
- Container image scanning, an SBOM and build provenance: with the first container
  build (EPC-023).
- Mutation testing.
