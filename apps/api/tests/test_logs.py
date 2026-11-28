"""JSON lines on stdout, allow-listed fields only, tied to the response by its ID.

An exception's line tells one failure from another by codes and names; only a
developer's local API writes messages, and uvicorn's information lines with them.
"""

import contextlib
import io
import json
import logging
import sys
import uuid
from collections.abc import Callable
from typing import Any

import psycopg
import pytest
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from starlette.routing import Route, Router
from starlette.types import ASGIApp

from roadmaps_api.app import create_app
from roadmaps_api.database import create_database_engine
from roadmaps_api.logs import JsonFormatter, StdoutHandler, exception_chain
from roadmaps_api.settings import Environment, Settings, SettingsError, load_settings
from tests.harness import PROBE_TABLE
from tests.support import (
    DOWN_DATABASE_URL,
    PLANTED,
    SAME_ORIGIN_HEADERS,
    ConfigureLogging,
    Lines,
    make_settings,
    mounted_app,
    serving,
)


def test_an_access_line_holds_the_allow_listed_fields_and_the_response_s_id(
    client: TestClient, lines: Lines
) -> None:
    response = client.get(f"/nowhere?token={PLANTED}", headers={"X-Request-ID": PLANTED})

    [line] = lines.read()
    request_id = response.headers["X-Request-ID"]
    assert len(request_id) == 32
    assert set(line) == {
        "time",
        "level",
        "logger",
        "message",
        "request_id",
        "trace_id",
        "span_id",
        "method",
        "route",
        "status",
        "duration_ms",
    }
    assert line["message"] == "request"
    assert line["request_id"] == request_id
    assert (line["method"], line["route"], line["status"]) == ("GET", "unmatched", 404)
    assert isinstance(line["duration_ms"], float)


ROUTES = {
    "a route with a path parameter": (
        lambda c: c.get(f"/test/items/{PLANTED}"),
        200,
        "/test/items/{item_id}",
    ),
    "a route of a router included in another": (
        lambda c: c.get(f"/test/nested/{PLANTED}"),
        200,
        "/test/nested/{item_id}",
    ),
    "a route of a router included under a prefix": (
        lambda c: c.get(f"/test/admin/things/{PLANTED}"),
        200,
        "/test/admin/things/{thing_id}",
    ),
    "an included route whose own path is a probe's": (
        lambda c: c.get("/test/admin/health"),
        200,
        "/test/admin/health",
    ),
    "an unknown path": (lambda c: c.get(f"/{PLANTED}"), 404, "unmatched"),
    "a redirect to the path without its trailing slash": (
        lambda c: c.get(f"/test/items/{PLANTED}/", follow_redirects=False),
        307,
        "unmatched",
    ),
    "a method the path does not take": (lambda c: c.delete("/test/echo"), 405, "/test/echo"),
    "a body that fails validation": (
        lambda c: c.post(f"/test/echo?{PLANTED}=1", json={}, headers=SAME_ORIGIN_HEADERS),
        422,
        "/test/echo",
    ),
    "an unexpected error": (lambda c: c.get("/test/boom"), 500, "/test/boom"),
    "a probe that fails": (lambda c: c.get("/ready"), 503, "/ready"),
}


@pytest.mark.parametrize(("send", "status", "route"), ROUTES.values(), ids=ROUTES)
def test_the_access_line_names_the_route_by_its_template_never_the_path(
    client: TestClient,
    lines: Lines,
    send: Callable[[TestClient], Response],
    status: int,
    route: str,
) -> None:
    assert send(client).status_code == status

    [access] = [line for line in lines.read() if line.get("message") == "request"]
    assert (access["route"], access["status"]) == (route, status)


def plain_app() -> ASGIApp:
    return PlainTextResponse("raw")


def starlette_router() -> ASGIApp:
    return Router([Route("/items/{item_id}", lambda _request: PlainTextResponse("item"))])


# Where an app is mounted, the app, and a path it answers. A mount at the root takes
# what no route of the API does; the last row's path, under the mount, is the API's own
# live OpenAPI route's.
MOUNTS = {
    "a FastAPI app under a template": (
        "/tenants/{tenant}",
        mounted_app,
        f"/tenants/{PLANTED}/items/1",
    ),
    "a FastAPI app at the root": ("/", mounted_app, f"/items/{PLANTED}"),
    "a Starlette router under a path": ("/sub", starlette_router, f"/sub/items/{PLANTED}"),
    "a Starlette router at the root": ("/", starlette_router, f"/items/{PLANTED}"),
    "an app with no routes at the root": ("/", plain_app, f"/items/{PLANTED}"),
    "an app with no routes, at a path the API routes": (
        "/raw",
        plain_app,
        "/raw/api/v1/openapi.json",
    ),
}


@pytest.mark.parametrize(("path", "mounted", "request_path"), MOUNTS.values(), ids=MOUNTS)
def test_a_request_a_mounted_app_handled_is_unmatched(
    lines: Lines, path: str, mounted: Callable[[], ASGIApp], request_path: str
) -> None:
    app = create_app(make_settings(environment=Environment.LOCAL))
    app.mount(path, mounted())
    with TestClient(app) as client:
        assert client.get(request_path).status_code == 200

    [access] = [line for line in lines.read() if line.get("message") == "request"]
    assert access["route"] == "unmatched"


def test_the_access_line_names_the_live_openapi_route(lines: Lines) -> None:
    with serving(make_settings(environment=Environment.LOCAL)) as client:
        assert client.get("/api/v1/openapi.json").status_code == 200

    [access] = [line for line in lines.read() if line.get("message") == "request"]
    assert access["route"] == "/api/v1/openapi.json"


@pytest.mark.parametrize(
    ("method", "logged"), [("GET", "GET"), ("PATCH", "PATCH"), (PLANTED, "_OTHER")]
)
def test_the_access_line_names_only_a_method_http_defines(
    client: TestClient, lines: Lines, method: str, logged: str
) -> None:
    client.request(method, "/nowhere")

    [access] = [line for line in lines.read() if line.get("message") == "request"]
    assert access["method"] == logged


def test_each_request_gets_its_own_id(client: TestClient) -> None:
    ids = {client.get("/health").headers["X-Request-ID"] for _ in range(3)}

    assert len(ids) == 3


def test_a_500_logs_the_exception_s_type_and_frames_never_its_message(
    client: TestClient, lines: Lines
) -> None:
    response = client.get("/test/boom")

    failure, access = lines.read()
    request_id = response.headers["X-Request-ID"]
    assert failure["level"] == "error"
    assert failure["message"] == "request.failed"
    assert failure["request_id"] == request_id
    assert failure["exception_type"] == "builtins.ValueError"
    assert any(frame.endswith(" in boom") for frame in failure["stack"])
    assert access["request_id"] == request_id
    assert access["status"] == 500


def test_ready_s_503_logs_a_warning_with_the_code_and_the_exception_s_type(
    client: TestClient, lines: Lines
) -> None:
    response = client.get("/ready")

    warning, access = lines.read()
    assert warning == {
        "time": warning["time"],
        "level": "warning",
        "logger": "roadmaps_api.services.readiness",
        "message": "readiness.failed",
        "request_id": response.headers["X-Request-ID"],
        "trace_id": response.headers["X-Request-ID"],
        "span_id": warning["span_id"],
        "code": "service.not_ready",
        "cause": "readiness.no_connection",
        "exception_type": "sqlalchemy.exc.OperationalError",
        "exception_causes": ["psycopg.OperationalError"],
        "stack": warning["stack"],
    }
    assert (access["route"], access["status"]) == ("/ready", 503)


def test_a_probe_that_succeeds_writes_no_access_line(lines: Lines, database_url: str) -> None:
    with serving(make_settings(database_url)) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 200

    assert lines.read() == []


def test_another_library_s_message_and_arguments_are_dropped(lines: Lines) -> None:
    logging.getLogger("uvicorn.error").warning(f"Error loading ASGI app. {PLANTED}")  # noqa: G004 - a library's f-string
    logging.getLogger("sqlalchemy.pool").warning("Lost %s", PLANTED)
    logging.getLogger("roadmaps_api.anything").info("event %s", PLANTED)
    logging.getLogger("roadmaps_api").info(ValueError(PLANTED))

    foreign, foreign_args, own, own_object = lines.read()
    assert foreign == {"time": foreign["time"], "level": "warning", "logger": "uvicorn.error"}
    assert "message" not in foreign_args
    assert own["message"] == "event %s"
    assert "message" not in own_object


def test_the_engine_hides_sql_parameters(database_url: str) -> None:
    engine = create_database_engine(database_url)

    with engine.connect() as connection, pytest.raises(SQLAlchemyError) as raised:
        connection.execute(text("SELECT 1 / 0 WHERE :value = :value"), {"value": PLANTED})

    assert PLANTED not in str(raised.value)
    engine.dispose()


def test_the_handler_writes_to_stdout_as_it_is_at_each_line(
    lines: Lines, monkeypatch: pytest.MonkeyPatch
) -> None:
    replaced = io.StringIO()
    monkeypatch.setattr(sys, "stdout", replaced)
    logging.getLogger("roadmaps_api").info("replaced")
    monkeypatch.undo()
    logging.getLogger("roadmaps_api").info("restored")

    assert json.loads(replaced.getvalue())["message"] == "replaced"
    assert [line["message"] for line in lines.read()] == ["restored"]


def test_a_broken_stdout_drops_the_line_without_raising(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class Broken:
        def write(self, _text: str) -> None:
            raise OSError

    handler = StdoutHandler()
    handler.setFormatter(JsonFormatter())
    monkeypatch.setattr("sys.stdout", Broken())

    handler.emit(logging.makeLogRecord({"name": "roadmaps_api", "msg": "x"}))

    monkeypatch.undo()
    assert capsys.readouterr().err == ""


VALID = {
    "ROADMAPS_DATABASE_URL": DOWN_DATABASE_URL,
    "ROADMAPS_ALLOWED_HOSTS": "localhost",
    "ROADMAPS_EDITOR_ORIGIN": "https://localhost",
}


def settings_for(environ: dict[str, str]) -> Settings:
    return load_settings({**VALID, **environ})


def logged_lines(capsys: pytest.CaptureFixture[str]) -> list[dict[str, Any]]:
    return [json.loads(line) for line in capsys.readouterr().out.splitlines()]


def log_failure(fail: Callable[[], object]) -> None:
    try:
        fail()
    except Exception:
        logging.getLogger("roadmaps_api.test").exception("failed")


# Each environment, or `None` for a line written before the settings are read, and
# whether its lines carry messages.
ENVIRONMENTS = {
    "local": ({"ROADMAPS_ENV": "local"}, True),
    "test": ({"ROADMAPS_ENV": "test"}, False),
    "production": ({"ROADMAPS_ENV": "production"}, False),
    "unset": ({}, False),
    "invalid": ({"ROADMAPS_ENV": "staging"}, False),
    "local on a Cloud Run service": ({"ROADMAPS_ENV": "local", "K_SERVICE": "api"}, False),
    "local in a Cloud Run job": ({"ROADMAPS_ENV": "local", "CLOUD_RUN_JOB": "job"}, False),
    "local in a Cloud Run worker pool": (
        {"ROADMAPS_ENV": "local", "CLOUD_RUN_WORKER_POOL": "pool"},
        False,
    ),
    "before the settings are read": (None, False),
}


@pytest.mark.parametrize(("environ", "writes"), ENVIRONMENTS.values(), ids=ENVIRONMENTS)
def test_only_a_developer_s_local_api_writes_messages(
    configure_logging: ConfigureLogging,
    capsys: pytest.CaptureFixture[str],
    environ: dict[str, str] | None,
    writes: bool,  # noqa: FBT001 - a table's column
) -> None:
    settings = None
    if environ is not None:
        with contextlib.suppress(SettingsError):
            settings = settings_for(environ)
    configure_logging(settings)
    capsys.readouterr()

    logging.getLogger("uvicorn.error").warning("Lost %s", PLANTED)
    log_failure(lambda: int(PLANTED))

    captured = capsys.readouterr()
    foreign, failure = [json.loads(line) for line in captured.out.splitlines()]
    assert failure["exception_type"] == "builtins.ValueError"
    if writes:
        assert foreign["message"] == f"Lost {PLANTED}"
        assert PLANTED in failure["exception_message"]
    else:
        assert "message" not in foreign
        assert "exception_message" not in failure
        assert PLANTED not in captured.out + captured.err
    # uvicorn's information lines are written only where their text is.
    assert logging.getLogger("uvicorn.error").isEnabledFor(logging.INFO) is writes
    assert logging.getLogger("uvicorn").isEnabledFor(logging.WARNING)


def test_a_message_that_cannot_be_formatted_is_left_out(
    configure_logging: ConfigureLogging, capsys: pytest.CaptureFixture[str]
) -> None:
    class UnprintableError(Exception):
        def __str__(self) -> str:
            raise RuntimeError

    configure_logging(settings_for({"ROADMAPS_ENV": "local"}))

    logging.getLogger("uvicorn.error").warning("%s and %s", "one")  # noqa: PLE1206 - the case
    log_failure(lambda: (_ for _ in ()).throw(UnprintableError()))

    foreign, failure = logged_lines(capsys)
    assert foreign["message"] is None
    assert failure["exception_message"] is None


def connect(url: str) -> None:
    engine = create_database_engine(url)
    try:
        with engine.connect():
            pass
    finally:
        engine.dispose()


def refused(_url: str) -> None:
    connect(DOWN_DATABASE_URL)


def wrong_password(url: str) -> None:
    connect(make_url(url).set(password=PLANTED).render_as_string(hide_password=False))


def connect_timeout(_url: str) -> None:
    raise psycopg.errors.ConnectionTimeout


def cancelled_statement(url: str) -> None:
    engine = create_database_engine(url)
    try:
        with engine.connect() as connection:
            connection.execute(text("SET statement_timeout = '10ms'"))
            connection.execute(text("SELECT pg_sleep(1)"))
    finally:
        engine.dispose()


# Each failure, given the test database's URL, its type, the types it was raised from and
# its SQLSTATE.
FAILURES = {
    "a refused connection": (
        refused,
        ("sqlalchemy.exc.OperationalError", ["psycopg.OperationalError"], None),
    ),
    "a wrong password": (
        wrong_password,
        ("sqlalchemy.exc.OperationalError", ["psycopg.OperationalError"], None),
    ),
    "a connect timeout": (connect_timeout, ("psycopg.errors.ConnectionTimeout", [], None)),
    "a cancelled statement": (
        cancelled_statement,
        ("sqlalchemy.exc.OperationalError", ["psycopg.errors.QueryCanceled"], "57014"),
    ),
}


@pytest.mark.parametrize(("fail", "expected"), FAILURES.values(), ids=FAILURES)
def test_an_exception_s_line_tells_failures_apart_by_codes(
    lines: Lines,
    database_url: str,
    fail: Callable[[str], None],
    expected: tuple[str, list[str], str | None],
) -> None:
    log_failure(lambda: fail(database_url))

    [line] = lines.read()
    assert (line["exception_type"], line["exception_causes"], line.get("sqlstate")) == expected
    assert "constraint_name" not in line
    assert line["stack"]


def test_a_refused_connection_and_a_wrong_password_differ_only_in_a_local_log(
    configure_logging: ConfigureLogging, capsys: pytest.CaptureFixture[str], database_url: str
) -> None:
    configure_logging(settings_for({"ROADMAPS_ENV": "local"}))

    log_failure(lambda: refused(database_url))
    log_failure(lambda: wrong_password(database_url))

    refusal, password = logged_lines(capsys)
    assert refusal["exception_causes"] == password["exception_causes"]
    assert refusal["exception_message"] != password["exception_message"]


@pytest.mark.parametrize("environment", ["test", "production"])
def test_a_unique_violation_logs_its_sqlstate_and_constraint_never_the_value(
    configure_logging: ConfigureLogging,
    capsys: pytest.CaptureFixture[str],
    database_url: str,
    environment: str,
) -> None:
    configure_logging(settings_for({"ROADMAPS_ENV": environment}))
    planted = str(uuid.uuid4())
    engine = create_database_engine(database_url)
    try:
        with engine.connect() as connection:
            connection.execute(
                text("SELECT set_config('app.tenant_id', :tenant, true)"),
                {"tenant": str(uuid.uuid4())},
            )
            insert = text(
                f"INSERT INTO {PROBE_TABLE} (id, tenant_id) "  # noqa: S608 - the harness's constant
                "VALUES (:id, NULLIF(current_setting('app.tenant_id'), '')::uuid)"
            )
            log_failure(lambda: [connection.execute(insert, {"id": planted}) for _ in range(2)])
            connection.rollback()
    finally:
        engine.dispose()

    captured = capsys.readouterr()
    [line] = [json.loads(text) for text in captured.out.splitlines()]
    assert line["exception_causes"] == ["psycopg.errors.UniqueViolation"]
    assert (line["sqlstate"], line["constraint_name"]) == ("23505", f"pk_{PROBE_TABLE}")
    assert planted not in captured.out + captured.err


def test_the_chain_follows_each_cause_then_context_stopping_at_a_repeat() -> None:
    cause, context, suppressed = KeyError(), IndexError(), LookupError()
    raised = ValueError()
    raised.__cause__ = cause
    cause.__context__ = context
    context.__context__ = suppressed
    context.__suppress_context__ = True
    looped = TypeError()
    looped.__context__ = looped

    assert exception_chain(raised) == [raised, cause, context]
    assert exception_chain(looped) == [looped]
