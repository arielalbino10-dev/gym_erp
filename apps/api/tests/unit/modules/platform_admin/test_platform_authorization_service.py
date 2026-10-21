import pytest

from gym_erp_api.modules.platform_admin.application.errors import PlatformPermissionDeniedError
from gym_erp_api.modules.platform_admin.application.services.platform_authorization_service import (
    PlatformAuthorizationService,
)
from gym_erp_api.modules.platform_admin.domain.platform_permission import (
    ALL_PLATFORM_PERMISSIONS,
    PlatformPermission,
)
from gym_erp_api.modules.platform_admin.domain.platform_role import PlatformRole
from gym_erp_api.modules.platform_admin.domain.platform_role_assignment import (
    PlatformRoleAssignment,
)
from tests.support.in_memory_platform_role_assignment_repository import (
    InMemoryPlatformRoleAssignmentRepository,
)


@pytest.fixture
def repo() -> InMemoryPlatformRoleAssignmentRepository:
    return InMemoryPlatformRoleAssignmentRepository()


@pytest.fixture
def service(repo: InMemoryPlatformRoleAssignmentRepository) -> PlatformAuthorizationService:
    return PlatformAuthorizationService(assignments=repo)


@pytest.mark.asyncio
async def test_root_admin_has_full_catalog(service, repo):
    await repo.upsert(
        assignment=PlatformRoleAssignment(
            user_id="root-1",
            roles=frozenset({PlatformRole.ROOT_ADMIN}),
        ),
    )
    effective = await service.effective_permissions(user_id="root-1")
    assert effective == ALL_PLATFORM_PERMISSIONS


@pytest.mark.asyncio
async def test_platform_admin_requires_explicit_grants(service, repo):
    await repo.upsert(
        assignment=PlatformRoleAssignment(
            user_id="op-1",
            roles=frozenset({PlatformRole.PLATFORM_ADMIN}),
            granted_permissions=frozenset({PlatformPermission.COMMERCIAL_PLANS_READ}),
        ),
    )
    effective = await service.effective_permissions(user_id="op-1")
    assert effective == frozenset({PlatformPermission.COMMERCIAL_PLANS_READ})
    with pytest.raises(PlatformPermissionDeniedError):
        await service.require_permission(
            user_id="op-1",
            permission=PlatformPermission.COMMERCIAL_PLANS_CREATE,
        )


@pytest.mark.asyncio
async def test_no_assignment_means_no_permissions(service):
    effective = await service.effective_permissions(user_id="unknown")
    assert effective == frozenset()
