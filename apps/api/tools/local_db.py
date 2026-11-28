"""Shared local-only superuser guards, table-teardown metadata and SQLAlchemy truncate helper.

`tools.bootstrap_database` and `tools.seed` share the environment/URL/superuser guards here;
`tests.harness.empty_tables` and `truncate_public_tables` share `VERSION_TABLE` and
`PUBLIC_TABLES_QUERY`.
"""

import ipaddress
from collections.abc import Mapping
from typing import Final

from sqlalchemy import Connection
from sqlalchemy.engine import make_url

from roadmaps_api.settings import CLOUD_RUN_MARKERS, ENV, Environment, is_database_url, refuse

ADMIN_DATABASE_URL: Final = "ROADMAPS_ADMIN_DATABASE_URL"
LOCAL_ENVIRONMENTS: Final = frozenset({Environment.LOCAL.value, Environment.TEST.value})
VERSION_TABLE: Final = "alembic_version"

SUPERUSER_QUERY: Final = "SELECT rolsuper FROM pg_roles WHERE rolname = current_user"
PUBLIC_TABLES_QUERY: Final = (
    "SELECT tablename FROM pg_tables"
    " WHERE schemaname = 'public' AND tablename <> %s"
    " ORDER BY tablename"
)


def loopback_host(url: str) -> str | None:
    """Returns the literal loopback IP host for a query-free psycopg URL, else `None`."""
    if not is_database_url(url):
        return None
    parsed = make_url(url)
    # No query parameters: libpq could otherwise override host, hostaddr or service.
    if parsed.query or parsed.host is None:
        return None
    try:
        if not ipaddress.ip_address(parsed.host).is_loopback:
            return None
    except ValueError:
        return None
    return parsed.host


def invalid_local_env(environ: Mapping[str, str], *, reject_cloud_run: bool = False) -> list[str]:
    """Returns disallowed environment or Cloud Run marker names, never their values."""
    invalid: list[str] = []
    if environ.get(ENV) not in LOCAL_ENVIRONMENTS:
        invalid.append(ENV)
    if reject_cloud_run:
        invalid.extend(marker for marker in CLOUD_RUN_MARKERS if marker in environ)
    return invalid


def validated_local_admin_url(environ: Mapping[str, str], *, reject_cloud_run: bool = False) -> str:
    """Validates local environment and loopback admin URL, or refuses naming only setting names."""
    invalid = invalid_local_env(environ, reject_cloud_run=reject_cloud_run)
    url = environ.get(ADMIN_DATABASE_URL, "").strip()
    if loopback_host(url) is None:
        invalid.append(ADMIN_DATABASE_URL)
    if invalid:
        refuse(invalid)
    return url


def truncate_public_tables(connection: Connection) -> None:
    """Truncates every `public` table except `alembic_version`, then restores `'origin'` mode."""
    tables = list(connection.exec_driver_sql(PUBLIC_TABLES_QUERY, (VERSION_TABLE,)).scalars())
    if not tables:
        return
    quote = connection.dialect.identifier_preparer.quote
    targets = ", ".join(f"public.{quote(table)}" for table in tables)
    # Replica mode is scoped strictly to teardown so immutable history tables can be cleared;
    # origin mode is restored immediately before any write.
    connection.exec_driver_sql("SET LOCAL session_replication_role = 'replica'")
    connection.exec_driver_sql(f"TRUNCATE {targets} CASCADE")
    connection.exec_driver_sql("SET LOCAL session_replication_role = 'origin'")
