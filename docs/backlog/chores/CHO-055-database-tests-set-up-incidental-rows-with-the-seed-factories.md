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
exercise with `apps/api/tools/seed/factories.py`. The fixtures of two suites older than
the factories still insert tenants, people, roles and memberships in SQL, and are the
nearest examples for a new database test. Done is those fixtures using the factories
wherever the SQL is not what the suite tests, and saying why where it stays.

## Measurement

_At commit `2868b58b`, lines matching
`INSERT INTO (tenants|people|roles|role_permissions|memberships|invitations)`, setup and
SQL under test together:_

| Area                                                    | Measurement | Verdict                                 |
| ------------------------------------------------------- | ----------- | --------------------------------------- |
| `apps/api/tests/integration/test_rls_isolation.py`      | 17 lines    | Read each: the two-tenant fixture seeds |
| `apps/api/tests/integration/test_access_change_sets.py` | 15 lines    | Read each: the access fixture seeds     |

`test_schema_and_privileges.py` matches too, but tests the schema through its SQL.

## Acceptance criteria

### S1: Incidental setup comes from the factories

- **Given** the two suites' fixtures
- **When** a row they insert is not what a test of theirs exercises
- **Then** a factory makes it, and any SQL that stays has a comment saying why
- **And** the suites' tests pass, each assertion unchanged

## Decisions
