"""Five fail-closed local-only safety guards for `tools.seed` (`STY-093` S4, D14).

Every entry point (`python -m tools.seed` and `run_seed`) refuses before truncating or
writing anything unless:
1. `ROADMAPS_ENV` is `local` or `test`;
2. no Cloud Run marker (`K_SERVICE`, `CLOUD_RUN_JOB`, `CLOUD_RUN_WORKER_POOL`) is set;
3. `ROADMAPS_ADMIN_DATABASE_URL` is a valid `postgresql+psycopg://` URL with no query params;
4. the URL host is a loopback IP (`127.0.0.1` or `::1`); and
5. the connected login is a superuser (`rolsuper`), checked on the same `hostaddr`-pinned
   SQLAlchemy connection used for `TRUNCATE ... CASCADE` and ORM seeding.
"""

from collections.abc import Mapping

from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.pool import NullPool

from roadmaps_api.settings import refuse
from tools.local_db import (
    ADMIN_DATABASE_URL,
    SUPERUSER_QUERY,
    invalid_local_env,
    loopback_host,
    validated_local_admin_url,
)


def validate_seed_environment(environ: Mapping[str, str]) -> None:
    """Validates guards 1-2 (`ROADMAPS_ENV` and Cloud Run markers), naming only refused keys."""
    invalid = invalid_local_env(environ, reject_cloud_run=True)
    if invalid:
        refuse(invalid)


def validated_admin_url(environ: Mapping[str, str]) -> str:
    """Validates guards 1-4 and returns the admin URL, or refuses naming only setting names."""
    return validated_local_admin_url(environ, reject_cloud_run=True)


def pinned_host(url: str) -> str:
    """Returns the validated loopback IP for `url`, or refuses naming `ADMIN_DATABASE_URL`."""
    host = loopback_host(url)
    if host is None:
        refuse([ADMIN_DATABASE_URL])
    return host


def create_pinned_admin_engine(url: str) -> Engine:
    """Creates a `NullPool` SQLAlchemy engine pinned to the URL's loopback IP via `hostaddr`."""
    host = pinned_host(url)
    return create_engine(
        url,
        poolclass=NullPool,
        hide_parameters=True,
        connect_args={"hostaddr": host},
    )


def assert_superuser(connection: Connection) -> None:
    """Guard 5: refuses on the active connection unless `current_user` is a superuser."""
    is_super = connection.execute(text(SUPERUSER_QUERY)).scalar()
    if not is_super:
        refuse([ADMIN_DATABASE_URL])
