"""Asignación persistida de roles y permisos platform por operador."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from gym_erp_api.modules.platform_admin.domain.platform_permission import PlatformPermission
from gym_erp_api.modules.platform_admin.domain.platform_role import PlatformRole


@dataclass(frozen=True, slots=True)
class PlatformRoleAssignment:
    user_id: str
    roles: frozenset[PlatformRole]
    granted_permissions: frozenset[PlatformPermission] = field(default_factory=frozenset)
    revoked_permissions: frozenset[PlatformPermission] = field(default_factory=frozenset)
    updated_at: datetime | None = None
    updated_by_user_id: str | None = None

    def __post_init__(self) -> None:
        if not self.user_id.strip():
            raise ValueError("user_id requerido.")
        overlap = self.granted_permissions & self.revoked_permissions
        if overlap:
            raise ValueError("Permisos otorgados y revocados no pueden solaparse.")
        if PlatformRole.ROOT_ADMIN in self.roles and (
            self.granted_permissions or self.revoked_permissions
        ):
            raise ValueError("root_admin no admite grants/revokes explícitos en MVP.")
