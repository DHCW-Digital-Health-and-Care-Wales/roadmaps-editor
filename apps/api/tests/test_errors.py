"""Every refusal is the envelope, with a stable code, and never echoes submitted values.

A 422 trims the trailing unknown key on `extra_forbidden`, caps `params.errors` at 25
entries (setting `truncated: true` only when more exist), and truncates string `loc`
segments longer than 128 characters to 127 characters plus `"…"` (ADR-020 _CHO-053
amendments_, _DEF-040 amendments_). The two exceptions to the envelope, the `Host`
allow-list's 400 and the body limit's 413, are Starlette's plain text
(`test_middleware.py`).
"""

import re
from collections.abc import Callable, Iterator
from typing import Annotated, Literal

import pytest
from fastapi import FastAPI, Header, Query
from fastapi.testclient import TestClient
from httpx2 import Response
from pydantic import Field, model_validator

from roadmaps_api.app import create_app
from roadmaps_api.authz import public
from roadmaps_api.wire import ApiRequestModel
from tests.support import PLANTED, SAME_ORIGIN_HEADERS, SAME_ORIGIN_JSON_HEADERS, make_settings

CAMEL_CASE = re.compile(r"[a-z][a-zA-Z0-9]*")


def keys(node: object) -> Iterator[str]:
    """Every key anywhere in a refusal's params, which are camelCase as the wire is."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from keys(value)
    elif isinstance(node, list):
        for value in node:
            yield from keys(value)


REFUSALS = {
    "an unknown path": (
        lambda c: c.get(f"/api/v1/{PLANTED}?q={PLANTED}"),
        404,
        "request.not_found",
        {},
    ),
    "a known path with the wrong method": (
        lambda c: c.post("/health", content=PLANTED),
        405,
        "request.method_not_allowed",
        {},
    ),
    "a body that fails validation": (
        lambda c: c.post("/test/echo", json={"name": [PLANTED]}, headers=SAME_ORIGIN_HEADERS),
        422,
        "request.invalid",
        {"errors": [{"loc": ["body", "name"], "type": "string_type"}]},
    ),
    "a query that fails validation": (
        lambda c: c.post(
            f"/test/echo?count={PLANTED}", json={"name": "a"}, headers=SAME_ORIGIN_HEADERS
        ),
        422,
        "request.invalid",
        {"errors": [{"loc": ["query", "count"], "type": "int_parsing"}]},
    ),
    "a body that is not JSON": (
        lambda c: c.post("/test/echo", content=PLANTED, headers=SAME_ORIGIN_JSON_HEADERS),
        422,
        "request.invalid",
        {"errors": [{"loc": ["body", 0], "type": "json_invalid"}]},
    ),
    "a body that is not UTF-8": (
        lambda c: c.post(
            "/test/echo",
            content=b'{"name": "\xff"}',
            headers=SAME_ORIGIN_JSON_HEADERS,
        ),
        422,
        "request.invalid",
        {"errors": [{"loc": ["body"], "type": "body_unreadable"}]},
    ),
    "a route raising an unexpected error": (
        lambda c: c.get("/test/boom"),
        500,
        "server.internal_error",
        {},
    ),
    "a route raising a status FastAPI never raises": (
        lambda c: c.get("/test/teapot"),
        500,
        "server.internal_error",
        {},
    ),
}


@pytest.mark.parametrize(("send", "status", "code", "params"), REFUSALS.values(), ids=REFUSALS)
def test_a_refusal_is_the_envelope_without_the_input(
    client: TestClient,
    send: Callable[[TestClient], Response],
    status: int,
    code: str,
    params: dict[str, object],
) -> None:
    response = send(client)

    assert response.status_code == status
    body = response.json()
    assert set(body) == {"detail", "code", "params"}
    assert body["code"] == code
    assert body["params"] == params
    assert all(CAMEL_CASE.fullmatch(key) for key in keys(body["params"]))
    assert isinstance(body["detail"], str)
    assert PLANTED not in response.text
    assert "Traceback" not in response.text


def test_a_valid_request_passes_through(client: TestClient) -> None:
    response = client.post("/test/echo?count=2", json={"name": "a"}, headers=SAME_ORIGIN_HEADERS)

    assert response.status_code == 200
    assert response.json() == {"name": "a", "count": 2}


def test_a_405_names_the_methods_the_path_allows(client: TestClient) -> None:
    assert client.post("/health").headers["Allow"] == "GET"


# 422 location cases.


class Leaf(ApiRequestModel):
    item_count: int = 0


class WrappedLeaf(ApiRequestModel):
    item_count: int = 0

    @model_validator(mode="after")
    def keep(self) -> WrappedLeaf:
        return self


class Cat(ApiRequestModel):
    kind: Literal["cat"]
    lives: int = 0


class Dog(ApiRequestModel):
    kind: Literal["dog"]
    barks: int = 0


class Shapes(ApiRequestModel):
    leaf: Leaf | None = None
    leaves: list[Leaf] = Field([])
    counts: dict[str, int] = Field({})
    buckets: dict[str, list[Leaf]] = Field({})
    pet: Annotated[Cat | Dog, Field(discriminator="kind")] | None = None
    wrapped: WrappedLeaf | int = 0


class Search(ApiRequestModel):
    page_size: int = 20


def locations_app() -> FastAPI:
    app = create_app(make_settings())

    @app.post("/test/shapes", dependencies=[public()])
    def shapes(body: Shapes) -> None: ...

    @app.get("/test/search", dependencies=[public()])
    def search(query: Annotated[Search, Query()]) -> None: ...

    @app.get("/test/parameters/{itemId}", dependencies=[public()])
    def parameters(
        itemId: int,  # noqa: N803 - the wire's name, as a path template spells it
        ids: Annotated[list[int], Query(alias="itemIds")] = [],  # noqa: B006 - FastAPI copies it
        x_page: Annotated[int, Header()] = 1,
    ) -> None: ...

    return app


@pytest.fixture(scope="module")
def locations_client() -> Iterator[TestClient]:
    with TestClient(locations_app()) as client:
        yield client


type Errors = list[tuple[list[str | int], str]]


def shapes_row(
    sent: object, *errors: tuple[list[str | int], str]
) -> tuple[str, str, object, Errors]:
    return "POST", "/test/shapes", sent, list(errors)


LOCATIONS: dict[str, tuple[str, str, object, Errors]] = {
    "an unknown key": shapes_row({PLANTED: 1}, (["body"], "extra_forbidden")),
    "an unknown key of a nested model": shapes_row(
        {"leaf": {PLANTED: 1}}, (["body", "leaf"], "extra_forbidden")
    ),
    "an unknown key of a model in a list": shapes_row(
        {"leaves": [{}, {PLANTED: 1}]}, (["body", "leaves", 1], "extra_forbidden")
    ),
    "a field of a model in a list": shapes_row(
        {"leaves": [{"itemCount": PLANTED}]}, (["body", "leaves", 0, "itemCount"], "int_parsing")
    ),
    "a dictionary key without its value": shapes_row(
        {"counts": {"callerKey": PLANTED}}, (["body", "counts", "callerKey"], "int_parsing")
    ),
    "an unknown key and field error of a discriminated union's choice": shapes_row(
        {"pet": {"kind": "cat", "lives": PLANTED, PLANTED: 1}},
        (["body", "pet", "cat", "lives"], "int_parsing"),
        (["body", "pet", "cat"], "extra_forbidden"),
    ),
    "an unknown query key of a query model": (
        "GET",
        f"/test/search?pageSize={PLANTED}&{PLANTED}=1",
        None,
        [(["query", "pageSize"], "int_parsing"), (["query"], "extra_forbidden")],
    ),
    "a path, a query and a header parameter": (
        "GET",
        f"/test/parameters/{PLANTED}?itemIds=1&itemIds={PLANTED}",
        None,
        [
            (["path", "itemId"], "int_parsing"),
            (["query", "itemIds", 1], "int_parsing"),
            (["header", "x-page"], "int_parsing"),
        ],
    ),
}


@pytest.mark.parametrize(("method", "url", "sent", "errors"), LOCATIONS.values(), ids=LOCATIONS)
def test_a_422_trims_forbidden_keys_and_keeps_locations(
    locations_client: TestClient, method: str, url: str, sent: object, errors: Errors
) -> None:
    # Only the route with a header parameter reads it.
    response = locations_client.request(
        method, url, json=sent, headers={**SAME_ORIGIN_HEADERS, "x-page": PLANTED}
    )

    assert response.status_code == 422
    assert response.json()["params"] == {
        "errors": [{"loc": loc, "type": error_type} for loc, error_type in errors]
    }
    assert PLANTED not in response.text


def test_a_422_keeps_nested_fields_under_a_wrapped_union_choice(
    locations_client: TestClient,
) -> None:
    response = locations_client.post(
        "/test/shapes",
        json={"wrapped": {"itemCount": PLANTED, PLANTED: 1}},
        headers=SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 422
    field_error, extra_error, int_error = response.json()["params"]["errors"]
    # Treat Pydantic's generated union-choice label as opaque: the nested field survives
    # beneath it and the unknown key after it is trimmed.
    assert field_error["type"] == "int_parsing"
    assert field_error["loc"][:2] == ["body", "wrapped"]
    assert len(field_error["loc"]) == 4
    assert field_error["loc"][3] == "itemCount"
    assert extra_error == {"loc": field_error["loc"][:3], "type": "extra_forbidden"}
    assert int_error == {"loc": ["body", "wrapped", "int"], "type": "int_type"}
    assert PLANTED not in response.text


ERROR_CAPS: dict[str, tuple[int, int, bool]] = {
    "at the cap (25 errors)": (25, 25, False),
    "one past the cap (26 errors)": (26, 25, True),
}


@pytest.mark.parametrize(
    ("submitted_count", "expected_count", "truncated"), ERROR_CAPS.values(), ids=ERROR_CAPS
)
def test_a_422_caps_listed_errors_and_marks_truncation_only_past_the_cap(
    locations_client: TestClient,
    submitted_count: int,
    expected_count: int,
    *,
    truncated: bool,
) -> None:
    response = locations_client.post(
        "/test/shapes",
        json={"leaves": [{"itemCount": PLANTED} for _ in range(submitted_count)]},
        headers=SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 422
    params = response.json()["params"]
    assert all(CAMEL_CASE.fullmatch(key) for key in keys(params))
    assert len(params["errors"]) == expected_count
    assert params["errors"][0] == {"loc": ["body", "leaves", 0, "itemCount"], "type": "int_parsing"}
    assert params["errors"][-1] == {
        "loc": ["body", "leaves", expected_count - 1, "itemCount"],
        "type": "int_parsing",
    }
    if truncated:
        assert params["truncated"] is True
        assert set(params) == {"errors", "truncated"}
    else:
        assert set(params) == {"errors"}
    assert PLANTED not in response.text


SEGMENT_BOUNDS: dict[str, tuple[object, list[str | int], str]] = {
    "a string segment at the 128-character limit": (
        {"counts": {"a" * 128: PLANTED}},
        ["body", "counts", "a" * 128],
        "int_parsing",
    ),
    "a string segment one character past the limit": (
        {"counts": {"a" * 128 + "z": PLANTED}},
        ["body", "counts", "a" * 127 + "…"],
        "int_parsing",
    ),
    "a long dictionary key before an extra_forbidden key and list index": (
        {"buckets": {"k" * 200: [{PLANTED: 1}]}},
        ["body", "buckets", "k" * 127 + "…", 0],
        "extra_forbidden",
    ),
    "a long trailing extra_forbidden key is omitted rather than truncated": (
        {f"{PLANTED}{'x' * 200}": 1},
        ["body"],
        "extra_forbidden",
    ),
}


@pytest.mark.parametrize(
    ("sent", "expected_loc", "expected_type"), SEGMENT_BOUNDS.values(), ids=SEGMENT_BOUNDS
)
def test_a_422_truncates_long_string_loc_segments(
    locations_client: TestClient,
    sent: object,
    expected_loc: list[str | int],
    expected_type: str,
) -> None:
    response = locations_client.post("/test/shapes", json=sent, headers=SAME_ORIGIN_HEADERS)

    assert response.status_code == 422
    assert response.json()["params"] == {"errors": [{"loc": expected_loc, "type": expected_type}]}
    assert PLANTED not in response.text


def test_a_422_bounds_the_response_for_a_long_dictionary_key_with_many_errors(
    locations_client: TestClient,
) -> None:
    long_key = "k" * 500
    response = locations_client.post(
        "/test/shapes",
        json={"buckets": {long_key: [{"itemCount": PLANTED} for _ in range(40)]}},
        headers=SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 422
    params = response.json()["params"]
    assert set(params) == {"errors", "truncated"}
    assert params["truncated"] is True
    assert len(params["errors"]) == 25
    assert all(
        error
        == {"loc": ["body", "buckets", "k" * 127 + "…", index, "itemCount"], "type": "int_parsing"}
        for index, error in enumerate(params["errors"])
    )
    assert long_key not in response.text
    assert PLANTED not in response.text
