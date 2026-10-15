from datetime import UTC, datetime

import pytest

from gym_erp_api.modules.organization.domain.enums import TenantStatus
from gym_erp_api.modules.organization.domain.errors import (
    InvalidOrganizationFieldError,
    InvalidOrganizationIdentifierError,
    InvalidOrganizationStateTransitionError,
)
from gym_erp_api.modules.organization.domain.tenant import Tenant
from gym_erp_api.shared_kernel.identifiers import is_valid_uuid_v4
from tests.support.tenant_fixtures import TENANT_A_ID, USER_A_ID


def test_tenant_create_starts_in_provisioning():
    tenant = Tenant.create(
        legal_name="  Gimnasios Ficticios SA de CV  ",
        display_name="PowerGym",
    )
    assert tenant.status is TenantStatus.PROVISIONING
    assert tenant.legal_name == "Gimnasios Ficticios SA de CV"
    assert tenant.display_name == "PowerGym"
    assert tenant.timezone == "America/Mexico_City"
    assert is_valid_uuid_v4(tenant.tenant_id)
    assert tenant.commercial_email is None
    assert tenant.commercial_email_normalized is None


def test_tenant_create_with_fixed_id_and_audit():
    moment = datetime(2026, 1, 15, 10, 0, tzinfo=UTC)
    tenant = Tenant.create(
        legal_name="Legal",
        display_name="Display",
        tenant_id=TENANT_A_ID,
        created_by_user_id=USER_A_ID,
        now=moment,
    )
    assert tenant.tenant_id == TENANT_A_ID
    assert tenant.created_at == moment
    assert tenant.updated_at == moment
    assert tenant.created_by_user_id == USER_A_ID


def test_tenant_commercial_email_normalized():
    tenant = Tenant.create(
        legal_name="Legal",
        display_name="Display",
        commercial_email="  Contact@Example.COM  ",
    )
    assert tenant.commercial_email == "Contact@Example.COM"
    assert tenant.commercial_email_normalized == "contact@example.com"


def test_tenant_rejects_invalid_uuid():
    with pytest.raises(InvalidOrganizationIdentifierError):
        Tenant.create(legal_name="L", display_name="D", tenant_id="not-a-uuid")


def test_tenant_rejects_empty_legal_name():
    with pytest.raises(InvalidOrganizationFieldError):
        Tenant.create(legal_name="   ", display_name="D")


def test_tenant_rejects_invalid_timezone():
    with pytest.raises(InvalidOrganizationFieldError):
        Tenant.create(legal_name="L", display_name="D", timezone="Not/AZone")


def test_tenant_status_transitions_allowed():
    tenant = Tenant.create(legal_name="L", display_name="D", tenant_id=TENANT_A_ID)
    active = tenant.transition_status(TenantStatus.ACTIVE)
    assert active.status is TenantStatus.ACTIVE
    suspended = active.transition_status(TenantStatus.SUSPENDED)
    assert suspended.status is TenantStatus.SUSPENDED
    reactivated = suspended.transition_status(TenantStatus.ACTIVE)
    assert reactivated.status is TenantStatus.ACTIVE


def test_tenant_provisioning_to_suspended():
    tenant = Tenant.create(legal_name="L", display_name="D", tenant_id=TENANT_A_ID)
    suspended = tenant.transition_status(TenantStatus.SUSPENDED)
    assert suspended.status is TenantStatus.SUSPENDED


def test_tenant_rejects_active_to_provisioning():
    tenant = Tenant.create(legal_name="L", display_name="D", tenant_id=TENANT_A_ID)
    active = tenant.transition_status(TenantStatus.ACTIVE)
    with pytest.raises(InvalidOrganizationStateTransitionError):
        active.transition_status(TenantStatus.PROVISIONING)


def test_tenant_is_immutable():
    tenant = Tenant.create(legal_name="L", display_name="D", tenant_id=TENANT_A_ID)
    with pytest.raises(AttributeError):
        tenant.tenant_id = TENANT_A_ID  # type: ignore[misc]
