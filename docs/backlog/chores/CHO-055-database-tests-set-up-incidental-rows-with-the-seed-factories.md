# CHO-055: Database tests set up incidental rows with the seed factories

- **Status**: Proposed — found by the retrospective after `STY-105`
- **Type**: Refactor
- **Area**: Infrastructure
- **Epic**: standalone
- **Depends on**: none
- **Binding ADRs**: none
- **Suggested model**: Sonnet — each fixture needs reading to tell setup from the SQL
  under test
- **Delivered**: _(add on delivery)_

## Summary

`apps/api/tests/integration/AGENTS.md` has a test set up the rows it does not itself
exercise with `apps/api/tools/seed/factories.py`. Three suites older than the factories
still insert such rows in SQL, in fixtures, a shared helper and test bodies, and are the
nearest examples for a new database test. Done is each of those rows coming from a
factory, or from an ORM row where no factory fits, with a comment saying why wherever
SQL stays.

## Measurement

_At commit `2868b58b`, lines matching
`INSERT INTO (tenants|people|roles|role_permissions|memberships|invitations)`, setup and
SQL under test together. All paths are in `apps/api/tests/integration/`:_

| Area                            | Measurement | Verdict                                                                                                    |
| ------------------------------- | ----------- | ---------------------------------------------------------------------------------------------------------- |
| `test_rls_isolation.py`         | 17 lines    | Setup: all are in the `two_tenants` fixture                                                                |
| `test_access_change_sets.py`    | 15 lines    | 10 are setup in `access_env`; judge the 5 in three test bodies                                             |
| `test_schema_and_privileges.py` | 24 lines    | 3 are setup in `_seed_tenant_person_role`; judge the other 21, keeping the SQL whose refusal a test checks |

The factories do not make every such row as it stands (an ended membership, a `google`
invitation).

## Acceptance criteria

### S1: Incidental setup comes from the factories

- **Given** the three suites' fixtures, helpers and test bodies
- **When** they insert a row that the test it serves does not exercise
- **Then** a factory makes it, or an ORM row over `harness.admin_session()` where no
  factory fits, and any SQL that stays has a comment saying why
- **And** the suites' tests pass, each assertion unchanged

## Decisions
