import pytest

from gym_erp_api.modules.organization.application.authorization.platform_provisioning import (
    PlatformProvisioningScope,
)
from gym_erp_api.modules.organization.application.errors import TenantAccessDeniedApplicationError
from gym_erp_api.modules.organization.domain.errors import InvalidOrganizationIdentifierError
from tests.support.tenant_fixtures import TENANT_A_ID, TENANT_B_ID


def test_scope_allows_matching_target():
    scope = PlatformProvisioningScope.for_single_tenant(TENANT_A_ID)
    scope.require_target_tenant(TENANT_A_ID)


def test_scope_rejects_other_tenant():
    scope = PlatformProvisioningScope.for_single_tenant(TENANT_A_ID)
    with pytest.raises(TenantAccessDeniedApplicationError):
        scope.require_target_tenant(TENANT_B_ID)


def test_scope_rejects_invalid_uuid():
    with pytest.raises(InvalidOrganizationIdentifierError):
        PlatformProvisioningScope.for_single_tenant("bad-tenant-id")


def test_no_global_admin_factory():
    assert not hasattr(PlatformProvisioningScope, "for_all_tenants")
    assert not hasattr(PlatformProvisioningScope, "admin")
