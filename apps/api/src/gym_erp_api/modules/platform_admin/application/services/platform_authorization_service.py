"""Evaluación RBAC platform (server-side)."""

from __future__ import annotations

from gym_erp_api.modules.platform_admin.application.errors import (
    PlatformPermissionDeniedError,
    PlatformRoleAssignmentNotFoundError,
)
from gym_erp_api.modules.platform_admin.application.ports.platform_role_assignment_repository import (  # noqa: E501
    PlatformRoleAssignmentRepository,
)
from gym_erp_api.modules.platform_admin.domain.platform_permission import (
    ALL_PLATFORM_PERMISSIONS,
    PlatformPermission,
)
from gym_erp_api.modules.platform_admin.domain.platform_role import PlatformRole


class PlatformAuthorizationService:
    def __init__(self, *, assignments: PlatformRoleAssignmentRepository) -> None:
        self._assignments = assignments

    async def effective_permissions(self, *, user_id: str) -> frozenset[PlatformPermission]:
        assignment = await self._assignments.get_by_user_id(user_id=user_id)
        if assignment is None:
            return frozenset()
        if PlatformRole.ROOT_ADMIN in assignment.roles:
            return ALL_PLATFORM_PERMISSIONS
        granted = set(assignment.granted_permissions)
        granted -= assignment.revoked_permissions
        return frozenset(granted)

    async def require_permission(
        self,
        *,
        user_id: str,
        permission: PlatformPermission,
    ) -> None:
        effective = await self.effective_permissions(user_id=user_id)
        if permission not in effective:
            raise PlatformPermissionDeniedError(
                f"Permiso platform requerido: {permission.value}",
            )

    async def require_any_assignment(self, *, user_id: str) -> None:
        assignment = await self._assignments.get_by_user_id(user_id=user_id)
        if assignment is None or not assignment.roles:
            raise PlatformRoleAssignmentNotFoundError(
                "Operador sin roles platform asignados.",
            )
