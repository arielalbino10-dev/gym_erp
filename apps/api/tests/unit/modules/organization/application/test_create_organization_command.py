from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from gym_erp_api.modules.organization.application.commands.create_organization import (
    CreateOrganizationCommand,
    CreateOrganizationResult,
)
from gym_erp_api.modules.organization.application.create_organization_fingerprint import (
    create_organization_request_fingerprint,
)
from gym_erp_api.modules.organization.application.errors import IdempotencyKeyRequiredError
from gym_erp_api.modules.organization.domain.enums import BranchStatus, TenantStatus
from gym_erp_api.modules.organization.domain.errors import InvalidOrganizationFieldError
from gym_erp_api.modules.organization.domain.tenant import DEFAULT_TENANT_TIMEZONE
from gym_erp_api.modules.organization.domain.value_objects import BranchAddress
from tests.support.tenant_fixtures import USER_A_ID


def _minimal_command(**overrides) -> CreateOrganizationCommand:
    base = {
        "idempotency_key": "req-abc-123456",
        "legal_name": "Legal SA",
        "display_name": "Gym Display",
        "branch_name": "Centro",
    }
    base.update(overrides)
    return CreateOrganizationCommand.build(**base)


def test_build_rejects_missing_idempotency_key():
    with pytest.raises(IdempotencyKeyRequiredError):
        CreateOrganizationCommand.build(
            idempotency_key="",
            legal_name="L",
            display_name="D",
            branch_name="B",
        )


def test_build_rejects_short_idempotency_key():
    with pytest.raises(IdempotencyKeyRequiredError):
        CreateOrganizationCommand.build(
            idempotency_key="short",
            legal_name="L",
            display_name="D",
            branch_name="B",
        )


def test_build_rejects_invalid_business_field():
    with pytest.raises(InvalidOrganizationFieldError):
        CreateOrganizationCommand.build(
            idempotency_key="req-abc-123456",
            legal_name="",
            display_name="D",
            branch_name="B",
        )


def test_branch_timezone_inherits_tenant_timezone():
    cmd = CreateOrganizationCommand.build(
        idempotency_key="req-abc-123456",
        legal_name="L",
        display_name="D",
        branch_name="B",
        tenant_timezone="America/Cancun",
    )
    assert cmd.tenant_timezone == "America/Cancun"
    assert cmd.branch_timezone == "America/Cancun"


def test_branch_timezone_explicit_overrides_inheritance():
    cmd = CreateOrganizationCommand.build(
        idempotency_key="req-abc-123456",
        legal_name="L",
        display_name="D",
        branch_name="B",
        tenant_timezone="America/Mexico_City",
        branch_timezone="America/Tijuana",
    )
    assert cmd.branch_timezone == "America/Tijuana"


def test_command_is_immutable():
    cmd = _minimal_command()
    with pytest.raises(FrozenInstanceError):
        cmd.legal_name = "Other"  # type: ignore[misc]


def test_fingerprint_stable_for_equivalent_normalization():
    cmd_a = CreateOrganizationCommand.build(
        idempotency_key="req-abc-123456",
        legal_name="  Legal SA  ",
        display_name="Gym",
        branch_name="Centro",
        commercial_email="  Ops@Example.COM ",
        branch_code=" centro-1 ",
    )
    cmd_b = CreateOrganizationCommand.build(
        idempotency_key="other-key-not-in-hash",
        legal_name="Legal SA",
        display_name="Gym",
        branch_name="Centro",
        commercial_email="ops@example.com",
        branch_code="CENTRO-1",
    )
    fp_a = create_organization_request_fingerprint(cmd_a)
    fp_b = create_organization_request_fingerprint(cmd_b)
    assert fp_a == fp_b


def test_fingerprint_differs_when_business_data_differs():
    base = _minimal_command()
    other = _minimal_command(display_name="Other Gym")
    assert create_organization_request_fingerprint(base) != create_organization_request_fingerprint(
        other
    )


def test_fingerprint_excludes_correlation_id():
    with_corr = _minimal_command(correlation_id="trace-99")
    without = _minimal_command()
    assert create_organization_request_fingerprint(with_corr) == (
        create_organization_request_fingerprint(without)
    )


def test_fingerprint_includes_address_when_present():
    addr = BranchAddress.create(line1="Calle 1", city="CDMX")
    with_addr = _minimal_command(branch_address=addr)
    without = _minimal_command()
    assert create_organization_request_fingerprint(with_addr) != (
        create_organization_request_fingerprint(without)
    )


def test_result_normalizes_created_at_to_utc():
    moment = datetime(2026, 6, 1, 12, 0, tzinfo=ZoneInfo("America/Mexico_City"))
    result = CreateOrganizationResult(
        tenant_id="550e8400-e29b-41d4-a716-446655440001",
        branch_id="990e8400-e29b-41d4-a716-446655440030",
        tenant_status=TenantStatus.ACTIVE,
        branch_status=BranchStatus.ACTIVE,
        idempotency_replayed=False,
        created_at=moment,
    )
    assert result.created_at.tzinfo == UTC


def test_result_rejects_naive_created_at():
    with pytest.raises(ValueError):
        CreateOrganizationResult(
            tenant_id="550e8400-e29b-41d4-a716-446655440001",
            branch_id="990e8400-e29b-41d4-a716-446655440030",
            tenant_status=TenantStatus.ACTIVE,
            branch_status=BranchStatus.ACTIVE,
            idempotency_replayed=False,
            created_at=datetime(2026, 6, 1, 12, 0),
        )


def test_optional_created_by_user_id():
    cmd = _minimal_command(created_by_user_id=USER_A_ID)
    assert cmd.created_by_user_id == USER_A_ID


def test_default_tenant_timezone():
    cmd = _minimal_command()
    assert cmd.tenant_timezone == DEFAULT_TENANT_TIMEZONE
