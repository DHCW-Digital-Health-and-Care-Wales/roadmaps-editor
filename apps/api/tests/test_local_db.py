"""Unit tests for shared local-only superuser URL and environment guards (`tools.local_db`)."""

import pytest

from roadmaps_api.settings import CLOUD_RUN_MARKERS, ENV, SettingsError
from tests.support import Lines
from tools.local_db import ADMIN_DATABASE_URL, loopback_host, validated_local_admin_url

SECRET = "SECRET-PASSWORD-91e2"  # noqa: S105 - planted, to prove no secret leaks
LOCAL_URL = f"postgresql+psycopg://roadmaps:{SECRET}@127.0.0.1:5432/roadmaps"

BAD_LOCAL_RUNS: dict[str, tuple[dict[str, str], list[str]]] = {
    "unset ROADMAPS_ENV": ({ADMIN_DATABASE_URL: LOCAL_URL}, [ENV]),
    "production ROADMAPS_ENV": ({ENV: "production", ADMIN_DATABASE_URL: LOCAL_URL}, [ENV]),
    "unknown ROADMAPS_ENV": ({ENV: SECRET, ADMIN_DATABASE_URL: LOCAL_URL}, [ENV]),
    "bad ROADMAPS_ENV and bad admin URL": (
        {ENV: "production", ADMIN_DATABASE_URL: LOCAL_URL.replace("127.0.0.1", "db.example")},
        [ENV, ADMIN_DATABASE_URL],
    ),
    "missing admin URL": ({ENV: "local"}, [ADMIN_DATABASE_URL]),
    "wrong driver scheme": (
        {ENV: "local", ADMIN_DATABASE_URL: LOCAL_URL.replace("+psycopg", "")},
        [ADMIN_DATABASE_URL],
    ),
    "socket URL without host": (
        {
            ENV: "local",
            ADMIN_DATABASE_URL: f"postgresql+psycopg://roadmaps:{SECRET}@/roadmaps",
        },
        [ADMIN_DATABASE_URL],
    ),
    **{
        f"non-loopback host {host}": (
            {ENV: "test", ADMIN_DATABASE_URL: LOCAL_URL.replace("127.0.0.1", host)},
            [ADMIN_DATABASE_URL],
        )
        for host in ("localhost", "db.example", "10.0.0.5", "192.168.1.10")
    },
    **{
        f"query parameter {param}": (
            {ENV: "local", ADMIN_DATABASE_URL: f"{LOCAL_URL}?{param}={value}"},
            [ADMIN_DATABASE_URL],
        )
        for param, value in (
            ("host", "db.example"),
            ("hostaddr", "10.0.0.5"),
            ("service", "prod"),
            ("sslmode", "require"),
        )
    },
}


@pytest.mark.parametrize(
    ("environ", "expected_invalid"), BAD_LOCAL_RUNS.values(), ids=BAD_LOCAL_RUNS
)
def test_validated_local_admin_url_refuses_non_local_settings_without_leaking_values(
    lines: Lines,
    environ: dict[str, str],
    expected_invalid: list[str],
) -> None:
    with pytest.raises(SettingsError) as raised:
        validated_local_admin_url(environ)
    assert raised.value.invalid == expected_invalid
    [line] = lines.read()
    assert line["invalid_settings"] == expected_invalid
    assert SECRET not in str(raised.value)
    assert SECRET not in str(line)


@pytest.mark.parametrize(
    ("host", "expected_host"),
    [("127.0.0.1", "127.0.0.1"), ("127.0.0.2", "127.0.0.2"), ("[::1]", "::1")],
)
def test_validated_local_admin_url_accepts_loopback_ips_in_local_and_test(
    host: str, expected_host: str
) -> None:
    url = LOCAL_URL.replace("127.0.0.1", host)
    assert validated_local_admin_url({ENV: "local", ADMIN_DATABASE_URL: url}) == url
    assert validated_local_admin_url({ENV: "test", ADMIN_DATABASE_URL: url}) == url
    assert loopback_host(url) == expected_host


@pytest.mark.parametrize("marker", [*CLOUD_RUN_MARKERS])
@pytest.mark.parametrize("value", [SECRET, ""], ids=["non-empty", "empty"])
def test_reject_cloud_run_flag_refuses_every_cloud_run_marker(
    lines: Lines,
    marker: str,
    value: str,
) -> None:
    environ = {ENV: "local", ADMIN_DATABASE_URL: LOCAL_URL, marker: value}
    with pytest.raises(SettingsError) as raised:
        validated_local_admin_url(environ, reject_cloud_run=True)
    assert raised.value.invalid == [marker]
    [line] = lines.read()
    assert line["invalid_settings"] == [marker]
    assert SECRET not in str(line)
