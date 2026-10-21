"""Composición access (membresías + factory) en gym_platform / lectura operational."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gym_erp_api.infrastructure.mongo.mongo_databases import MongoDatabases
from gym_erp_api.infrastructure.mongo.scoped_repository import TenantScopedRepository
from gym_erp_api.modules.access.application.authorization.gym_authorization_service import (
    GymAuthorizationService,
)
from gym_erp_api.modules.access.application.services.tenant_context_factory import (
    TenantContextFactory,
)
from gym_erp_api.modules.access.application.use_cases.list_gym_memberships import (
    ListGymMembershipsForUserUseCase,
)
from gym_erp_api.modules.access.application.use_cases.select_gym_active_tenant import (
    SelectGymActiveTenantUseCase,
)
from gym_erp_api.modules.access.infrastructure.mongo.membership_document_mapper import (
    TENANT_MEMBERSHIPS_COLLECTION,
)
from gym_erp_api.modules.access.infrastructure.mongo.mongo_tenant_membership_repository import (
    MongoTenantMembershipRepository,
)
from gym_erp_api.modules.access.infrastructure.organization_branch_scope_validator import (
    OrganizationBranchScopeValidator,
)
from gym_erp_api.modules.identity.application.ports.session_repository import SessionRepository
from gym_erp_api.modules.organization.application.bootstrap_context import (
    CREATE_ORGANIZATION_BOOTSTRAP_MEMBERSHIP_ID,
    CREATE_ORGANIZATION_BOOTSTRAP_USER_ID,
)
from gym_erp_api.modules.organization.infrastructure.mongo.branch_document_mapper import (
    BRANCHES_COLLECTION,
)
from gym_erp_api.modules.organization.infrastructure.mongo.operational_branch_repository import (
    OperationalBranchRepository,
)
from gym_erp_api.modules.organization.infrastructure.mongo.platform_tenant_repository import (
    PlatformTenantRepository,
)
from gym_erp_api.modules.organization.infrastructure.mongo.tenant_document_mapper import (
    TENANTS_COLLECTION,
)
from gym_erp_api.shared_kernel.tenant_context import TenantContext


@dataclass(frozen=True, slots=True)
class AccessInfrastructure:
    membership_repository: MongoTenantMembershipRepository
    tenant_repository: PlatformTenantRepository
    tenant_context_factory: TenantContextFactory
    branch_scope_validator: OrganizationBranchScopeValidator
    list_gym_memberships: ListGymMembershipsForUserUseCase
    select_gym_active_tenant: SelectGymActiveTenantUseCase
    gym_authorization_service: GymAuthorizationService


def build_access_infrastructure(
    databases: MongoDatabases,
    *,
    session_repository: SessionRepository,
    memberships_collection: Any | None = None,
    tenants_collection: Any | None = None,
) -> AccessInfrastructure:
    platform = databases.platform
    operational = databases.operational
    memberships = MongoTenantMembershipRepository(
        memberships_collection
        if memberships_collection is not None
        else platform[TENANT_MEMBERSHIPS_COLLECTION]
    )
    tenants = PlatformTenantRepository(
        tenants_collection if tenants_collection is not None else platform[TENANTS_COLLECTION]
    )
    branches_collection = operational[BRANCHES_COLLECTION]

    def branch_repository_for_tenant(tenant_id: str) -> OperationalBranchRepository:
        ctx = TenantContext(
            tenant_id=tenant_id,
            user_id=CREATE_ORGANIZATION_BOOTSTRAP_USER_ID,
            membership_id=CREATE_ORGANIZATION_BOOTSTRAP_MEMBERSHIP_ID,
            allowed_branch_ids=None,
        )
        scoped = TenantScopedRepository(branches_collection, ctx, branch_scoped=False)
        return OperationalBranchRepository(scoped)

    branch_validator = OrganizationBranchScopeValidator(
        branch_repository_for_tenant=branch_repository_for_tenant,
    )
    factory = TenantContextFactory(memberships=memberships, tenants=tenants)
    authz_service = GymAuthorizationService()
    return AccessInfrastructure(
        membership_repository=memberships,
        tenant_repository=tenants,
        tenant_context_factory=factory,
        branch_scope_validator=branch_validator,
        list_gym_memberships=ListGymMembershipsForUserUseCase(
            memberships=memberships,
            tenants=tenants,
        ),
        select_gym_active_tenant=SelectGymActiveTenantUseCase(
            sessions=session_repository,
            tenant_context_factory=factory,
        ),
        gym_authorization_service=authz_service,
    )
