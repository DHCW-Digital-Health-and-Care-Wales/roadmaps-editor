"""The test app: the API as `create_app` builds it, plus routes that only tests mount.

The probes take no input and never fail unexpectedly, so the 422 and 500 cases need a
route of their own, and the body limit a route that reads no body. The server test runs
`create_test_app` under uvicorn.
"""

import contextlib
import json
import socket
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Annotated, Any, Final

import pytest
from fastapi import APIRouter, FastAPI, Query, Request
from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind, Status, StatusCode
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

# Imported only to raise one, as FastAPI's routing would for a status it never uses.
from starlette.exceptions import HTTPException  # noqa: TID251 - raised as routing would

from roadmaps_api.app import create_app
from roadmaps_api.authz import PolicyAPIRoute, public
from roadmaps_api.settings import Environment, Settings, load_settings
from roadmaps_api.wire import ApiRequestModel

TEST_HOST: Final = "testserver"
TEST_EDITOR_ORIGIN: Final = f"http://{TEST_HOST}"
SAME_ORIGIN_HEADERS: Final = {"Sec-Fetch-Site": "same-origin"}
SAME_ORIGIN_JSON_HEADERS: Final = {
    "Sec-Fetch-Site": "same-origin",
    "Content-Type": "application/json",
}
# A port where nothing listens: the database is down.
DOWN_DATABASE_URL: Final = "postgresql+psycopg://roadmaps:roadmaps@127.0.0.1:1/roadmaps"
PLANTED: Final = "PLANTED-VALUE-7f3a"

# Applies the API's log configuration for the settings (`configure_logging` in conftest).
type ConfigureLogging = Callable[[Settings | None], None]


class Lines:
    """The JSON lines written on stdout, none holding the planted value."""

    def __init__(self, capsys: pytest.CaptureFixture[str]) -> None:
        self._capsys = capsys

    def read(self) -> list[dict[str, Any]]:
        captured = self._capsys.readouterr()
        assert captured.err == ""
        assert PLANTED not in captured.out
        parsed = [json.loads(line) for line in captured.out.splitlines()]
        # The test client's own lines, one per request it sends.
        return [line for line in parsed if line["logger"] != "httpx2"]


def server_span(spans: InMemorySpanExporter) -> ReadableSpan:
    """The one request span the exporter holds."""
    [span] = [span for span in spans.get_finished_spans() if span.kind is SpanKind.SERVER]
    return span


def free_port() -> int:
    """A port nothing listens on now."""
    with socket.create_server(("127.0.0.1", 0)) as probe:
        return probe.getsockname()[1]


def make_settings(
    url: str = DOWN_DATABASE_URL,
    environment: Environment = Environment.TEST,
    hosts: tuple[str, ...] = (TEST_HOST,),
    editor_origin: str = TEST_EDITOR_ORIGIN,
) -> Settings:
    return Settings(
        environment=environment,
        database_url=url,
        allowed_hosts=hosts,
        editor_origin=editor_origin,
    )


class Echo(ApiRequestModel):
    name: str


def add_test_routes(app: FastAPI) -> FastAPI:
    router = APIRouter(prefix="/test", route_class=PolicyAPIRoute)
    own = APIRouter(route_class=PolicyAPIRoute, dependencies=[public()])
    app.state.unread_calls = 0

    @own.post("/echo")
    def echo(body: Echo, count: Annotated[int, Query()] = 1) -> dict[str, object]:
        return {"name": body.name, "count": count}

    @own.post("/unread")
    def unread(request: Request) -> dict[str, str]:
        """Answers without reading the body, counting each call."""
        request.app.state.unread_calls += 1
        return {"status": "ok"}

    @own.get("/boom")
    def boom() -> None:
        raise ValueError(PLANTED)

    @own.get("/teapot")
    def teapot() -> None:
        raise HTTPException(status_code=418, detail=PLANTED)

    @own.get("/items/{item_id}")
    def item(item_id: str) -> dict[str, str]:
        return {"item": item_id}

    # Routers included in another, under a prefix of their own and one given at include
    # time, as the contract's resources will be under /api/v1.
    nested = APIRouter(prefix="/nested", route_class=PolicyAPIRoute, dependencies=[public()])

    @nested.get("/{item_id}")
    def nested_item(item_id: str) -> dict[str, str]:
        return {"item": item_id}

    admin = APIRouter(route_class=PolicyAPIRoute, dependencies=[public()])

    @admin.get("/things/{thing_id}")
    def thing(thing_id: str) -> dict[str, str]:
        return {"thing": thing_id}

    @admin.get("/health")
    def admin_health() -> dict[str, str]:
        return {"status": "ok"}

    add_tracing_routes(own)
    router.include_router(own)
    router.include_router(nested)
    router.include_router(admin, prefix="/admin")
    app.include_router(router)
    return app


def add_tracing_routes(router: APIRouter) -> None:
    """Routes that plant values where a span might take them up."""

    @router.get("/annotated")
    def annotated() -> dict[str, str]:
        """Writes a span attribute, an event and a status description no list allows."""
        span = trace.get_current_span()
        span.set_attribute("user.email", PLANTED)
        span.add_event(PLANTED, {"value": PLANTED})
        span.set_status(Status(StatusCode.ERROR, PLANTED))
        return {"status": "ok"}

    @router.get("/recorded")
    def recorded(request: Request) -> dict[str, str]:
        """Has the SDK record exceptions holding the planted value, as its own calls do."""
        tracer: trace.Tracer = request.app.state.tracer
        with contextlib.suppress(ValueError), tracer.start_as_current_span("child"):
            raise ValueError(PLANTED)
        trace.get_current_span().record_exception(ValueError(PLANTED))
        return {"status": "ok"}

    @router.get("/query")
    def query(request: Request) -> dict[str, str]:
        """Binds the planted value to a query, then to one that fails echoing it."""
        sessions: sessionmaker[Session] = request.app.state.sessions
        with sessions() as session:
            session.execute(text("SELECT :value"), {"value": PLANTED})
            session.execute(text("SELECT CAST(:value AS integer)"), {"value": PLANTED})
        return {"status": "ok"}


def mounted_app() -> FastAPI:
    """An app with a route of its own, to mount."""
    mounted = FastAPI()

    @mounted.get("/items/{item_id}")
    def mounted_item(item_id: str) -> dict[str, str]:
        return {"item": item_id}

    return mounted


@contextmanager
def serving(settings: Settings, span_exporter: SpanExporter | None = None) -> Generator[TestClient]:
    """A client of the test app, with its lifespan run, its spans sent to the exporter."""
    with TestClient(add_test_routes(create_app(settings, span_exporter=span_exporter))) as client:
        yield client


def create_test_app() -> FastAPI:
    """Uvicorn's factory for the server test: the settings come from the environment."""
    return add_test_routes(create_app(load_settings()))
