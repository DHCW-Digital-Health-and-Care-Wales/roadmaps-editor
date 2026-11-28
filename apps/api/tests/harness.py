"""The database test harness (STY-091 S9, ADR-017 _Tests_; `tests/integration/AGENTS.md`).

Once per run the controller builds a template database through the code
`pnpm api:migrate` runs, then adds the probe table; each pytest-xdist worker clones its
own database from it, owned by the owner role and given the bootstrap file's
database-scoped part, and its tests connect as a login of the application's role.
Between tests a superuser connection, which exists only here, empties every table but
`alembic_version`.
"""

import os
import uuid
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Final

import psycopg
from psycopg import sql
from sqlalchemy import Connection, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from roadmaps_api.database import TENANT_POLICY
from roadmaps_api.migrate import upgrade
from roadmaps_api.roles import APP_ROLE, OWNER_ROLE, database_scoped_sql
from tools.bootstrap_database import (
    APP_LOGIN,
    LOCAL_PASSWORD,
    MIGRATION_LOGIN,
    PLATFORM_LOGIN,
    PURGE_LOGIN,
    libpq_url,
)
from tools.local_db import ADMIN_DATABASE_URL, PUBLIC_TABLES_QUERY, VERSION_TABLE

# Owned by the owner role, under forced row-level security with the policy ADR-015's
# tenant-owned tables use (STY-091 D13, D33). Not a migration's: the drift check leaves
# it out.
PROBE_TABLE: Final = "harness_probe"
# Where a test that needs `/ready` to find no version table moves it (`versions`).
MOVED_VERSION_TABLE: Final = "alembic_version_moved"
# A test that leaves a connection holding a lock fails the emptying, not the run.
LOCK_TIMEOUT: Final = "5s"


def admin_url(database: str | None = None) -> str:
    """Compose's superuser, from `ROADMAPS_ADMIN_DATABASE_URL`, on the database."""
    url = os.environ.get(ADMIN_DATABASE_URL)
    if not url:
        msg = f"Run the tests with pnpm api:test, which sets {ADMIN_DATABASE_URL}."
        raise RuntimeError(msg)
    parsed = make_url(url)
    return parsed.set(database=database or parsed.database).render_as_string(hide_password=False)


def login_url(login: str, database: str, password: str = LOCAL_PASSWORD) -> str:
    """A login's SQLAlchemy URL for the database, on the admin's server."""
    return (
        make_url(admin_url(database))
        .set(username=login, password=password)
        .render_as_string(hide_password=False)
    )


def app_url(database: str) -> str:
    return login_url(APP_LOGIN, database)


def migration_url(database: str) -> str:
    return login_url(MIGRATION_LOGIN, database)


def platform_url(database: str) -> str:
    return login_url(PLATFORM_LOGIN, database)


def purge_url(database: str) -> str:
    return login_url(PURGE_LOGIN, database)


@contextmanager
def admin(database: str | None = None) -> Generator[psycopg.Connection]:
    """A superuser connection, committing each statement."""
    with psycopg.connect(libpq_url(admin_url(database)), autocommit=True) as connection:
        yield connection


@contextmanager
def admin_connection(database: str) -> Generator[Connection]:
    """A SQLAlchemy superuser connection with `LOCK_TIMEOUT` set, disposed on exit."""
    engine = create_engine(admin_url(database), hide_parameters=True)
    try:
        with engine.connect() as connection:
            connection.execute(text(f"SET lock_timeout = '{LOCK_TIMEOUT}'"))
            connection.commit()
            yield connection
    finally:
        engine.dispose()


@contextmanager
def admin_session(database: str) -> Generator[Session]:
    """A SQLAlchemy superuser session with `LOCK_TIMEOUT` and `autoflush=False`.

    `autoflush=False` ensures factory tests prove each factory flushes for itself.
    """
    with (
        admin_connection(database) as connection,
        Session(bind=connection, autoflush=False) as s,
    ):
        yield s


def unique_name(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def one_uuid(
    connection: psycopg.Connection, query: str, params: tuple[object, ...] = ()
) -> uuid.UUID:
    """Runs a SQL query returning one UUID column and asserts its type."""
    row = connection.execute(query.encode(), params).fetchone()
    assert row is not None
    assert isinstance(row[0], uuid.UUID)
    return row[0]


def create_database(name: str, template: str | None = None) -> None:
    """A database owned by the owner role, with the bootstrap's database-scoped part."""
    statement = sql.SQL("CREATE DATABASE {} OWNER {}").format(
        sql.Identifier(name), sql.Identifier(OWNER_ROLE)
    )
    if template is not None:
        statement += sql.SQL(" TEMPLATE {}").format(sql.Identifier(template))
    with admin() as connection:
        connection.execute(statement)
    with admin(name) as connection, connection.transaction():
        connection.execute(database_scoped_sql().encode())


def drop_database(name: str) -> None:
    with admin() as connection:
        connection.execute(
            sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name))
        )


def build_template(name: str) -> None:
    """The template: migrated as `pnpm api:migrate` does, plus the probe table."""
    create_database(name)
    upgrade(migration_url(name))
    with admin(name) as connection, connection.transaction():
        connection.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(OWNER_ROLE)))
        connection.execute(
            sql.SQL(
                "CREATE TABLE {table} ("
                " id uuid CONSTRAINT {key} PRIMARY KEY DEFAULT uuidv7(),"
                " tenant_id uuid NOT NULL)"
            ).format(table=sql.Identifier(PROBE_TABLE), key=sql.Identifier(f"pk_{PROBE_TABLE}"))
        )
        connection.execute(
            sql.SQL("ALTER TABLE {} ENABLE ROW LEVEL SECURITY, FORCE ROW LEVEL SECURITY").format(
                sql.Identifier(PROBE_TABLE)
            )
        )
        connection.execute(
            sql.SQL("CREATE POLICY tenant ON {} USING ({policy}) WITH CHECK ({policy})").format(
                sql.Identifier(PROBE_TABLE), policy=sql.SQL(TENANT_POLICY)
            )
        )
        connection.execute(
            sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON {} TO {}").format(
                sql.Identifier(PROBE_TABLE), sql.Identifier(APP_ROLE)
            )
        )


def empty_tables(connection: psycopg.Connection) -> None:
    """Empties every table in `public` but `alembic_version`, so the revision stays."""
    tables = connection.execute(PUBLIC_TABLES_QUERY, (VERSION_TABLE,)).fetchall()
    if tables:
        # Superuser-only replica mode bypasses immutability BEFORE TRUNCATE triggers
        # during test teardown without adding any superuser backdoor to production SQL.
        with connection.transaction():
            connection.execute("SET LOCAL session_replication_role = 'replica'")
            connection.execute(
                sql.SQL("TRUNCATE {} CASCADE").format(
                    sql.SQL(", ").join(sql.Identifier("public", table) for (table,) in tables)
                )
            )


def open_admin(database: str) -> psycopg.Connection:
    """The worker's superuser connection for emptying, failing on a held lock."""
    connection = psycopg.connect(libpq_url(admin_url(database)), autocommit=True)
    connection.execute(sql.SQL("SET lock_timeout = {}").format(sql.Literal(LOCK_TIMEOUT)))
    return connection


def holding(*revisions: str) -> Callable[[psycopg.Connection], None]:
    """Changes `alembic_version` to hold these rows, for the `versions` fixture to put back."""

    def change(connection: psycopg.Connection) -> None:
        connection.execute("DELETE FROM alembic_version")
        for revision in revisions:
            connection.execute("INSERT INTO alembic_version VALUES (%s)", (revision,))

    return change


def without_the_version_table(connection: psycopg.Connection) -> None:
    connection.execute(f"ALTER TABLE alembic_version RENAME TO {MOVED_VERSION_TABLE}".encode())
