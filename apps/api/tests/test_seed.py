"""Unit tests for deterministic IDs, Welsh helpers, personas, seed guards, packaging and CLI."""

import base64
import hashlib
import ipaddress
import tomllib
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from roadmaps_api.authz import ShippedRoleKey
from roadmaps_api.settings import ENV, SettingsError
from tests.support import DOWN_DATABASE_URL, Lines
from tools.local_db import ADMIN_DATABASE_URL
from tools.seed.cli import format_summary, main, parse_args
from tools.seed.deterministic import (
    DEFAULT_SEED,
    derive_invitation_token,
    deterministic_uuidv7,
    hash_invitation_token,
    request_hash_for,
)
from tools.seed.guards import pinned_host, validated_admin_url
from tools.seed.personas import (
    CWM_AUR_SLUG,
    DHCW_SLUG,
    LOCAL_MOCK_ISSUER,
    NAMED_PERSONAS,
    TENANT_SPECS,
    UNINVITED_PERSONA,
)
from tools.seed.seeder import SeededInvitation, SeededPerson, SeededTenant, SeedResult
from tools.seed.welsh import create_faker, example_email, welsh_name_parts

API_DIR = Path(__file__).parent.parent
SECRET = "SECRET-SEED-VALUE-91e2"  # noqa: S105 - planted, to prove no secret leaks
LOCAL_URL = f"postgresql+psycopg://roadmaps:{SECRET}@127.0.0.1:5432/roadmaps"


def test_faker_is_declared_only_in_dev_dependency_group() -> None:
    pyproject = tomllib.loads((API_DIR / "pyproject.toml").read_text(encoding="utf-8"))
    runtime_deps: list[str] = pyproject["project"]["dependencies"]
    dev_deps: list[str] = pyproject["dependency-groups"]["dev"]

    assert not any(dep.lower().startswith("faker") for dep in runtime_deps)
    assert any(dep.lower().startswith("faker") for dep in dev_deps)


def test_deterministic_uuidv7_is_rfc9562_stable_and_time_ordered() -> None:
    earlier = datetime(2025, 1, 15, 9, 0, 0, tzinfo=UTC)
    later = earlier + timedelta(seconds=5)

    first = deterministic_uuidv7("tenant:dhcw", earlier)
    repeated = deterministic_uuidv7("tenant:dhcw", earlier)
    other_namespace = deterministic_uuidv7("tenant:cwm-aur", earlier)
    later_id = deterministic_uuidv7("tenant:dhcw", later)

    assert first == repeated
    assert first != other_namespace
    assert first < later_id
    for generated in (first, other_namespace, later_id):
        assert generated.version == 7
        assert generated.variant == uuid.RFC_4122


def test_invitation_token_derivation_is_256_bit_deterministic_and_sha256_hashed() -> None:
    token_a = derive_invitation_token(DEFAULT_SEED, "dhcw:pending")
    token_a_repeat = derive_invitation_token(DEFAULT_SEED, "dhcw:pending")
    token_other_seed = derive_invitation_token(DEFAULT_SEED + 1, "dhcw:pending")
    token_other_label = derive_invitation_token(DEFAULT_SEED, "dhcw:revoked")

    assert token_a == token_a_repeat
    assert token_a != token_other_seed
    assert token_a != token_other_label

    hash_a = hash_invitation_token(token_a)
    assert len(hash_a) == 32
    assert hash_a == hashlib.sha256(token_a.encode("ascii")).digest()
    assert hash_a != hash_invitation_token(token_other_seed)

    padded = token_a + "=" * (-len(token_a) % 4)
    assert len(base64.urlsafe_b64decode(padded)) == 32

    req_hash = request_hash_for(DEFAULT_SEED, "seed:dhcw:bootstrap")
    assert len(req_hash) == 32
    assert req_hash == request_hash_for(DEFAULT_SEED, "seed:dhcw:bootstrap")
    assert req_hash != request_hash_for(DEFAULT_SEED + 1, "seed:dhcw:bootstrap")


def test_welsh_helper_is_deterministic_per_seed_and_uses_example_domain() -> None:
    faker_a = create_faker(DEFAULT_SEED)
    faker_b = create_faker(DEFAULT_SEED)
    faker_c = create_faker(DEFAULT_SEED + 17)

    names_a = [welsh_name_parts(faker_a) for _ in range(6)]
    names_b = [welsh_name_parts(faker_b) for _ in range(6)]
    names_c = [welsh_name_parts(faker_c) for _ in range(6)]

    assert names_a == names_b
    assert names_a != names_c

    email = example_email("Siân", "O'Connor-Davies", index=1, domain="dhcw.example")
    assert email == "sian.oconnor-davies.1@dhcw.example"
    assert email.endswith(".example")


def test_tenants_and_named_persona_roster_match_story_and_adr_018_contracts() -> None:
    by_slug = {tenant.slug: tenant for tenant in TENANT_SPECS}
    assert set(by_slug) == {DHCW_SLUG, CWM_AUR_SLUG}
    assert by_slug[DHCW_SLUG].name_en == "Digital Health and Care Wales"
    assert by_slug[DHCW_SLUG].name_cy == "Iechyd a Gofal Digidol Cymru"
    assert by_slug[CWM_AUR_SLUG].name_en == "Cwm Aur Health Board"
    assert by_slug[CWM_AUR_SLUG].name_cy == "Bwrdd Iechyd Cwm Aur"

    # Issuer must be both non-HTTPS and loopback so both ADR-018 guards refuse it outside local.
    parts = urlsplit(LOCAL_MOCK_ISSUER)
    assert not any(ch.isspace() for ch in LOCAL_MOCK_ISSUER)
    assert parts.scheme == "http"
    assert parts.hostname is not None
    assert ipaddress.ip_address(parts.hostname).is_loopback

    assert len(NAMED_PERSONAS) == 8
    all_specs = (*NAMED_PERSONAS, UNINVITED_PERSONA)
    assert len({spec.key for spec in all_specs}) == len(all_specs)
    assert len({spec.subject for spec in all_specs}) == len(all_specs)
    assert len({spec.email for spec in all_specs}) == len(all_specs)
    assert all(spec.issuer == LOCAL_MOCK_ISSUER for spec in all_specs)
    assert all(spec.email.endswith(".example") for spec in all_specs)
    assert UNINVITED_PERSONA.memberships == ()

    dhcw_admins = [
        p
        for p in NAMED_PERSONAS
        if (DHCW_SLUG, ShippedRoleKey.ADMIN) in p.memberships
        and not p.disabled
        and DHCW_SLUG not in p.ended_in_tenants
    ]
    assert len(dhcw_admins) == 2
    assert any(
        (DHCW_SLUG, ShippedRoleKey.PRODUCT_LEAD) in p.memberships and len(p.memberships) == 1
        for p in NAMED_PERSONAS
    )
    assert any(
        (DHCW_SLUG, ShippedRoleKey.VIEWER) in p.memberships
        and not p.disabled
        and DHCW_SLUG not in p.ended_in_tenants
        for p in NAMED_PERSONAS
    )
    assert any(
        set(p.memberships)
        == {(DHCW_SLUG, ShippedRoleKey.PRODUCT_LEAD), (CWM_AUR_SLUG, ShippedRoleKey.ADMIN)}
        for p in NAMED_PERSONAS
    )
    assert any(p.memberships == ((CWM_AUR_SLUG, ShippedRoleKey.ADMIN),) for p in NAMED_PERSONAS)
    assert any(DHCW_SLUG in p.ended_in_tenants for p in NAMED_PERSONAS)
    assert any(p.disabled for p in NAMED_PERSONAS)


def test_seed_guard_wiring_rejects_cloud_run_markers_and_accepts_loopback(lines: Lines) -> None:
    assert validated_admin_url({ENV: "local", ADMIN_DATABASE_URL: LOCAL_URL}) == LOCAL_URL
    assert pinned_host(LOCAL_URL) == "127.0.0.1"

    with pytest.raises(SettingsError) as raised:
        validated_admin_url({ENV: "local", ADMIN_DATABASE_URL: LOCAL_URL, "K_SERVICE": "api"})
    assert raised.value.invalid == ["K_SERVICE"]
    [line] = lines.read()
    assert line["invalid_settings"] == ["K_SERVICE"]


def test_cli_main_refuses_bad_environment_without_leaking_secret(lines: Lines) -> None:
    code = main(
        argv=[],
        environ={ENV: "production", "CLOUD_RUN_JOB": SECRET, ADMIN_DATABASE_URL: LOCAL_URL},
    )
    assert code == 1
    [line] = lines.read()
    assert line["invalid_settings"] == [ENV, "CLOUD_RUN_JOB"]
    assert SECRET not in str(line)


def test_pinned_host_refuses_non_loopback_or_query_url_directly(lines: Lines) -> None:
    with pytest.raises(SettingsError) as raised:
        pinned_host(f"{LOCAL_URL}?hostaddr=10.0.0.5")
    assert raised.value.invalid == [ADMIN_DATABASE_URL]
    [line] = lines.read()
    assert line["invalid_settings"] == [ADMIN_DATABASE_URL]


def test_cli_parses_default_and_explicit_seed() -> None:
    assert parse_args([]).seed == DEFAULT_SEED
    assert parse_args(["--seed", "123"]).seed == 123


def test_cli_logs_failure_without_raw_exception_message(lines: Lines) -> None:
    code = main(argv=[], environ={ENV: "local", ADMIN_DATABASE_URL: DOWN_DATABASE_URL})
    assert code == 1
    [line] = lines.read()
    assert line["message"] == "seed.failed"
    assert line["logger"] == "roadmaps_api.seed"
    assert "exception_message" not in line


def test_summary_lists_personas_and_only_pending_invitation_raw_tokens() -> None:
    now = datetime(2026, 11, 27, 12, 0, 0, tzinfo=UTC)
    pending_token = "PENDING-RAW-TOKEN-VALUE"  # noqa: S105 - synthetic test token
    revoked_token = "REVOKED-RAW-TOKEN-VALUE"  # noqa: S105 - synthetic test token
    expired_token = "EXPIRED-RAW-TOKEN-VALUE"  # noqa: S105 - synthetic test token
    result = SeedResult(
        seed=DEFAULT_SEED,
        tenants=(
            SeededTenant(
                id=deterministic_uuidv7("t:dhcw", now),
                slug=DHCW_SLUG,
                name_en="Digital Health and Care Wales",
                name_cy="Iechyd a Gofal Digidol Cymru",
            ),
        ),
        personas=(
            SeededPerson(
                id=deterministic_uuidv7("p:admin", now),
                key="dhcw_admin_primary",
                display_name="Rhiannon Davies",
                email="rhiannon.davies@dhcw.example",
                issuer=LOCAL_MOCK_ISSUER,
                subject="local-dhcw-admin-1",
                summary_roles=("dhcw:admin",),
            ),
        ),
        generated_member_count=6,
        invitations=(
            SeededInvitation(
                id=deterministic_uuidv7("i:pending", now),
                tenant_slug=DHCW_SLUG,
                email="invite.pending@dhcw.example",
                role_key=ShippedRoleKey.PRODUCT_LEAD,
                status="pending",
                raw_token=pending_token,
                expires_at=now + timedelta(days=7),
            ),
            SeededInvitation(
                id=deterministic_uuidv7("i:revoked", now),
                tenant_slug=DHCW_SLUG,
                email="invite.revoked@dhcw.example",
                role_key=ShippedRoleKey.VIEWER,
                status="revoked",
                raw_token=revoked_token,
                expires_at=now + timedelta(days=7),
            ),
            SeededInvitation(
                id=deterministic_uuidv7("i:expired", now),
                tenant_slug=DHCW_SLUG,
                email="invite.expired@dhcw.example",
                role_key=ShippedRoleKey.PRODUCT_LEAD,
                status="expired",
                raw_token=expired_token,
                expires_at=now - timedelta(days=10),
            ),
        ),
    )

    summary = format_summary(result)
    assert "dhcw" in summary
    assert "Rhiannon Davies" in summary
    assert "rhiannon.davies@dhcw.example" in summary
    assert "local-dhcw-admin-1" in summary
    assert pending_token in summary
    assert revoked_token not in summary
    assert expired_token not in summary
