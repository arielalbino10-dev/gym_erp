"""Contratos de autorización interna (no HTTP, no ADR-0003)."""

from gym_erp_api.modules.organization.application.authorization.platform_provisioning import (
    PlatformProvisioningScope,
)
from gym_erp_api.modules.organization.application.authorization.tenant_member import (
    TenantMemberAccess,
)

__all__ = ["PlatformProvisioningScope", "TenantMemberAccess"]
