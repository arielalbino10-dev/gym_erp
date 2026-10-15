from datetime import UTC, datetime

import pytest

from gym_erp_api.modules.organization.application.errors import (
    TenantNotActiveApplicationError,
    TenantNotFoundApplicationError,
    TenantSuspendedApplicationError,
)
from gym_erp_api.modules.organization.application.policies.tenant_operational import (
    TenantOperationalPolicy,
)
from gym_erp_api.modules.organization.domain.enums import TenantStatus
from gym_erp_api.modules.organization.domain.tenant import Tenant
from tests.support.tenant_fixtures import TENANT_A_ID


def _tenant_with_status(status: TenantStatus) -> Tenant:
    moment = datetime(2026, 5, 1, tzinfo=UTC)
    base = Tenant.create(
        legal_name="Legal",
        display_name="Display",
        tenant_id=TENANT_A_ID,
        now=moment,
    )
    if status is TenantStatus.PROVISIONING:
        return base
    if status is TenantStatus.ACTIVE:
        return base.transition_status(TenantStatus.ACTIVE, now=moment)
    if status is TenantStatus.SUSPENDED:
        return base.transition_status(TenantStatus.SUSPENDED, now=moment)
    raise AssertionError("status no soportado")


def test_active_tenant_allows_operational():
    tenant = _tenant_with_status(TenantStatus.ACTIVE)
    result = TenantOperationalPolicy.ensure_allows_operational(tenant)
    assert result is tenant


def test_suspended_tenant_rejects_operational():
    tenant = _tenant_with_status(TenantStatus.SUSPENDED)
    with pytest.raises(TenantSuspendedApplicationError):
        TenantOperationalPolicy.ensure_allows_operational(tenant)


def test_provisioning_tenant_rejects_operational():
    tenant = _tenant_with_status(TenantStatus.PROVISIONING)
    with pytest.raises(TenantNotActiveApplicationError):
        TenantOperationalPolicy.ensure_allows_operational(tenant)


def test_missing_tenant_rejects_operational():
    with pytest.raises(TenantNotFoundApplicationError):
        TenantOperationalPolicy.ensure_allows_operational(None)
