"""Bootstraps the slot's local database: four password logins, then the roles' file.

`scripts/api.sh` runs it (`pnpm api:db:up`, and so `api:dev`, `api:migrate` and
`api:test`), as `python -m tools.bootstrap_database`, with `ROADMAPS_ENV` and
`ROADMAPS_ADMIN_DATABASE_URL`, Compose's superuser. In one transaction it creates the
migration, application, platform and purge logins, with fixed local passwords, runs
`roadmaps_api/bootstrap.sql`, then makes each login a member of exactly one of the four
caller roles. A second run changes nothing, so an existing volume is brought up to date in
place.

It refuses, naming the setting and never its value, unless `ROADMAPS_ENV` is local or
test, the admin URL's host is a loopback address and its login is a superuser, which no
Cloud SQL login is (STY-091 D3, D30): where the API is hosted, EPC-023 creates the logins
and runs the file.
"""

import logging
import logging.config
import os
import sys
from collections.abc import Mapping
from typing import Final

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

from roadmaps_api.logs import log_config
from roadmaps_api.roles import (
    APP_ROLE,
    MIGRATION_ROLE,
    PLATFORM_ROLE,
    PURGE_ROLE,
    bootstrap_sql,
)
from roadmaps_api.settings import SettingsError, refuse
from tools.local_db import (
    ADMIN_DATABASE_URL,
    SUPERUSER_QUERY,
    validated_local_admin_url,
)

logger = logging.getLogger("roadmaps_api.bootstrap")

# The local logins and the one role each is a member of. The passwords are for the
# slot's container alone, reachable only from this machine (apps/api/compose.yaml).
MIGRATION_LOGIN: Final = "roadmaps_migrator_login"
APP_LOGIN: Final = "roadmaps_app_login"
PLATFORM_LOGIN: Final = "roadmaps_platform_login"
PURGE_LOGIN: Final = "roadmaps_purge_login"
LOCAL_PASSWORD: Final = "roadmaps"  # noqa: S105 - the local container's, as Compose's own
LOGINS: Final = {
    MIGRATION_LOGIN: MIGRATION_ROLE,
    APP_LOGIN: APP_ROLE,
    PLATFORM_LOGIN: PLATFORM_ROLE,
    PURGE_LOGIN: PURGE_ROLE,
}


def admin_url(environ: Mapping[str, str]) -> str:
    """The admin URL, or logs and raises `SettingsError` naming each refused setting."""
    return validated_local_admin_url(environ)


def libpq_url(url: str) -> str:
    """The SQLAlchemy URL as psycopg takes it, without the driver's name."""
    return make_url(url).set(drivername="postgresql").render_as_string(hide_password=False)


def bootstrap(url: str) -> None:
    """Makes the logins and the roles in the URL's database, or changes nothing."""
    # At the URL's own address, whatever libpq's environment (`PGHOSTADDR`) says.
    with psycopg.connect(libpq_url(url), hostaddr=make_url(url).host) as connection:
        row = connection.execute(SUPERUSER_QUERY).fetchone()
        if not (row and row[0]):
            refuse([ADMIN_DATABASE_URL])
        for login in LOGINS:
            exists = connection.execute(
                "SELECT FROM pg_roles WHERE rolname = %s", (login,)
            ).fetchone()
            if exists is None:
                connection.execute(sql.SQL("CREATE ROLE {}").format(sql.Identifier(login)))
            connection.execute(
                sql.SQL(
                    "ALTER ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION "
                    "NOBYPASSRLS PASSWORD {}"
                ).format(sql.Identifier(login), sql.Literal(LOCAL_PASSWORD))
            )
        connection.execute(bootstrap_sql().encode())
        for login, role in LOGINS.items():
            for other in set(LOGINS.values()) - {role}:
                connection.execute(
                    sql.SQL("REVOKE {} FROM {}").format(
                        sql.Identifier(other), sql.Identifier(login)
                    )
                )
            connection.execute(
                sql.SQL("GRANT {} TO {}").format(sql.Identifier(role), sql.Identifier(login))
            )


def main(environ: Mapping[str, str] | None = None) -> int:
    # No line holds a message: the admin URL is not one to write.
    logging.config.dictConfig(log_config())
    try:
        bootstrap(admin_url(os.environ if environ is None else environ))
    except SettingsError:
        # The setting's name is logged.
        return 1
    except psycopg.errors.RaiseException as refused:
        # The file's own refusal, naming the roles or objects it found, for the developer.
        print(refused.diag.message_primary, file=sys.stderr)  # noqa: T201 - its report
        return 1
    except Exception:
        logger.exception("bootstrap.failed")
        return 1
    logger.info("bootstrap.done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
