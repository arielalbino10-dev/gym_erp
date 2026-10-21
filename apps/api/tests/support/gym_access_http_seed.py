"""Seed mínimo platform (tenant + membresía) para pruebas HTTP gym H2-C.3."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from gym_erp_api.modules.access.domain.enums import BranchScopeMode, GymRole
from gym_erp_api.modules.access.domain.tenant_membership import TenantMembership
from gym_erp_api.modules.access.infrastructure.mongo.mongo_tenant_membership_repository import (
    MongoTenantMembershipRepository,
)
from gym_erp_api.modules.organization.domain.enums import TenantStatus
from gym_erp_api.modules.organization.domain.tenant import Tenant
from gym_erp_api.modules.organization.infrastructure.mongo.platform_tenant_repository import (
    PlatformTenantRepository,
)


async def seed_active_tenant(
    tenants_collection: Any,
    *,
    tenant_id: str,
    display_name: str,
    moment: datetime,
    status: TenantStatus = TenantStatus.ACTIVE,
) -> Tenant:
    tenant = Tenant.create(
        legal_name=display_name,
        display_name=display_name,
        tenant_id=tenant_id,
        now=moment,
    )
    if status is TenantStatus.ACTIVE:
        tenant = tenant.transition_status(TenantStatus.ACTIVE, now=moment)
    elif status is not TenantStatus.PROVISIONING:
        tenant = tenant.transition_status(status, now=moment)
    repo = PlatformTenantRepository(tenants_collection)
    await repo.insert(tenant)
    return tenant


async def seed_active_membership(
    memberships_collection: Any,
    *,
    user_id: str,
    tenant_id: str,
    moment: datetime,
    gym_roles: frozenset[GymRole] | None = None,
) -> TenantMembership:
    roles = gym_roles or frozenset({GymRole.GYM_OWNER})
    membership = TenantMembership.create_active(
        user_id=user_id,
        tenant_id=tenant_id,
        gym_roles=roles,
        branch_scope_mode=BranchScopeMode.ALL_BRANCHES,
        now=moment,
    )
    repo = MongoTenantMembershipRepository(memberships_collection)
    await repo.insert(membership)
    return membership
