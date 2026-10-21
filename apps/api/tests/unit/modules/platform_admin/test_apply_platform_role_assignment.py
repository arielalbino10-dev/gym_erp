from __future__ import annotations

from datetime import UTC, datetime

import pytest

from gym_erp_api.modules.platform_admin.application.errors import (
    LastRootAdminProtectionError,
    PlatformPermissionDeniedError,
    PlatformRoleManagementForbiddenError,
)
from gym_erp_api.modules.platform_admin.application.services.platform_authorization_service import (
    PlatformAuthorizationService,
)
from gym_erp_api.modules.platform_admin.application.use_cases.apply_platform_role_assignment import (  # noqa: E501
    ApplyPlatformRoleAssignmentUseCase,
)
from gym_erp_api.modules.platform_admin.application.use_cases.record_platform_audit_event import (
    RecordPlatformAuditEventUseCase,
)
from gym_erp_api.modules.platform_admin.domain.platform_permission import PlatformPermission
from gym_erp_api.modules.platform_admin.domain.platform_role import PlatformRole
from gym_erp_api.modules.platform_admin.domain.platform_role_assignment import (
    PlatformRoleAssignment,
)
from tests.support.in_memory_platform_audit_repository import InMemoryPlatformAuditRepository
from tests.support.in_memory_platform_role_assignment_repository import (
    InMemoryPlatformRoleAssignmentRepository,
)

_MOMENT = datetime(2026, 11, 1, tzinfo=UTC)
_ROOT = "00000000-0000-4000-8000-000000000010"
_OP = "00000000-0000-4000-8000-000000000011"
_TARGET = "00000000-0000-4000-8000-000000000012"


def _use_case(
    repo: InMemoryPlatformRoleAssignmentRepository,
) -> ApplyPlatformRoleAssignmentUseCase:
    audit = RecordPlatformAuditEventUseCase(audit=InMemoryPlatformAuditRepository())
    authz = PlatformAuthorizationService(assignments=repo)
    return ApplyPlatformRoleAssignmentUseCase(
        assignments=repo,
        authorization=authz,
        audit=audit,
    )


@pytest.mark.asyncio
async def test_platform_admin_cannot_assign_root_admin():
    repo = InMemoryPlatformRoleAssignmentRepository()
    await repo.upsert(
        assignment=PlatformRoleAssignment(
            user_id=_OP,
            roles=frozenset({PlatformRole.PLATFORM_ADMIN}),
            granted_permissions=frozenset({PlatformPermission.PLATFORM_OPERATORS_MANAGE}),
        ),
    )
    uc = _use_case(repo)
    with pytest.raises(PlatformRoleManagementForbiddenError):
        await uc.execute(
            actor_user_id=_OP,
            assignment=PlatformRoleAssignment(
                user_id=_TARGET,
                roles=frozenset({PlatformRole.ROOT_ADMIN}),
            ),
            recorded_at=_MOMENT,
        )


@pytest.mark.asyncio
async def test_cannot_remove_last_root_admin():
    repo = InMemoryPlatformRoleAssignmentRepository()
    await repo.upsert(
        assignment=PlatformRoleAssignment(
            user_id=_ROOT,
            roles=frozenset({PlatformRole.ROOT_ADMIN}),
        ),
    )
    uc = _use_case(repo)
    with pytest.raises(LastRootAdminProtectionError):
        await uc.execute(
            actor_user_id=_ROOT,
            assignment=PlatformRoleAssignment(
                user_id=_ROOT,
                roles=frozenset({PlatformRole.PLATFORM_ADMIN}),
            ),
            recorded_at=_MOMENT,
        )


@pytest.mark.asyncio
async def test_operator_without_manage_permission_denied():
    repo = InMemoryPlatformRoleAssignmentRepository()
    await repo.upsert(
        assignment=PlatformRoleAssignment(
            user_id=_OP,
            roles=frozenset({PlatformRole.PLATFORM_ADMIN}),
            granted_permissions=frozenset({PlatformPermission.PLATFORM_OPERATORS_READ}),
        ),
    )
    uc = _use_case(repo)
    with pytest.raises(PlatformPermissionDeniedError):
        await uc.execute(
            actor_user_id=_OP,
            assignment=PlatformRoleAssignment(
                user_id=_TARGET,
                roles=frozenset({PlatformRole.PLATFORM_ADMIN}),
            ),
            recorded_at=_MOMENT,
        )


@pytest.mark.asyncio
async def test_root_can_assign_platform_admin_and_writes_audit():
    repo = InMemoryPlatformRoleAssignmentRepository()
    audit_repo = InMemoryPlatformAuditRepository()
    authz = PlatformAuthorizationService(assignments=repo)
    uc = ApplyPlatformRoleAssignmentUseCase(
        assignments=repo,
        authorization=authz,
        audit=RecordPlatformAuditEventUseCase(audit=audit_repo),
    )
    await repo.upsert(
        assignment=PlatformRoleAssignment(
            user_id=_ROOT,
            roles=frozenset({PlatformRole.ROOT_ADMIN}),
        ),
    )
    await uc.execute(
        actor_user_id=_ROOT,
        assignment=PlatformRoleAssignment(
            user_id=_TARGET,
            roles=frozenset({PlatformRole.PLATFORM_ADMIN}),
            granted_permissions=frozenset({PlatformPermission.COMMERCIAL_PLANS_READ}),
        ),
        recorded_at=_MOMENT,
    )
    stored = await repo.get_by_user_id(user_id=_TARGET)
    assert stored is not None
    assert PlatformRole.PLATFORM_ADMIN in stored.roles
    assert len(audit_repo.events) == 1
    assert audit_repo.events[0].action == "platform.role_assignment.upsert"
