"""Asignación/revocación RBAC platform (sin API HTTP en incremento A).

Controles:
- Actor con ``platform.operators.manage`` (root incluido vía catálogo completo).
- Solo ``root_admin`` puede otorgar ``root_admin``.
- Prohibido dejar cero ``root_admin`` activos.
- Evento append-only en auditoría (best-effort tras persistencia de rol).

La API REST de escritura permanece sin exponer hasta pruebas HTTP dedicadas.
"""

from __future__ import annotations

from datetime import datetime

from gym_erp_api.modules.platform_admin.application.errors import (
    LastRootAdminProtectionError,
    PlatformRoleManagementForbiddenError,
)
from gym_erp_api.modules.platform_admin.application.ports.platform_role_assignment_repository import (  # noqa: E501
    PlatformRoleAssignmentRepository,
)
from gym_erp_api.modules.platform_admin.application.services.platform_authorization_service import (  # noqa: E501
    PlatformAuthorizationService,
)
from gym_erp_api.modules.platform_admin.application.use_cases.record_platform_audit_event import (
    RecordPlatformAuditEventUseCase,
)
from gym_erp_api.modules.platform_admin.domain.platform_permission import PlatformPermission
from gym_erp_api.modules.platform_admin.domain.platform_role import PlatformRole
from gym_erp_api.modules.platform_admin.domain.platform_role_assignment import (
    PlatformRoleAssignment,
)


class ApplyPlatformRoleAssignmentUseCase:
    def __init__(
        self,
        *,
        assignments: PlatformRoleAssignmentRepository,
        authorization: PlatformAuthorizationService,
        audit: RecordPlatformAuditEventUseCase,
    ) -> None:
        self._assignments = assignments
        self._authorization = authorization
        self._audit = audit

    async def execute(
        self,
        *,
        actor_user_id: str,
        assignment: PlatformRoleAssignment,
        recorded_at: datetime,
        correlation_id: str | None = None,
    ) -> PlatformRoleAssignment:
        await self._authorization.require_permission(
            user_id=actor_user_id,
            permission=PlatformPermission.PLATFORM_OPERATORS_MANAGE,
        )
        actor_assignment = await self._assignments.get_by_user_id(user_id=actor_user_id)
        actor_is_root = (
            actor_assignment is not None and PlatformRole.ROOT_ADMIN in actor_assignment.roles
        )
        target_is_root = PlatformRole.ROOT_ADMIN in assignment.roles

        if target_is_root and not actor_is_root:
            raise PlatformRoleManagementForbiddenError(
                "Solo root_admin puede asignar root_admin.",
            )

        previous = await self._assignments.get_by_user_id(user_id=assignment.user_id)
        had_root = previous is not None and PlatformRole.ROOT_ADMIN in previous.roles
        if had_root and not target_is_root:
            root_count = await self._assignments.count_users_with_role(
                role=PlatformRole.ROOT_ADMIN,
            )
            if root_count <= 1:
                raise LastRootAdminProtectionError(
                    "Debe permanecer al menos un root_admin.",
                )

        stamped = PlatformRoleAssignment(
            user_id=assignment.user_id,
            roles=assignment.roles,
            granted_permissions=assignment.granted_permissions,
            revoked_permissions=assignment.revoked_permissions,
            updated_at=recorded_at,
            updated_by_user_id=actor_user_id,
        )
        await self._assignments.upsert(assignment=stamped)
        await self._audit.execute(
            actor_user_id=actor_user_id,
            action="platform.role_assignment.upsert",
            resource_type="platform_operator",
            resource_id=assignment.user_id,
            outcome="success",
            recorded_at=recorded_at,
            correlation_id=correlation_id,
            metadata={
                "roles": sorted(r.value for r in stamped.roles),
            },
        )
        return stamped
