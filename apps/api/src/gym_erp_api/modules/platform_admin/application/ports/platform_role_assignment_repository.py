"""Puerto persistencia asignaciones RBAC platform."""

from __future__ import annotations

from typing import Protocol

from gym_erp_api.modules.platform_admin.domain.platform_role import PlatformRole
from gym_erp_api.modules.platform_admin.domain.platform_role_assignment import (
    PlatformRoleAssignment,
)


class PlatformRoleAssignmentRepository(Protocol):
    async def get_by_user_id(self, *, user_id: str) -> PlatformRoleAssignment | None: ...

    async def upsert(self, *, assignment: PlatformRoleAssignment) -> None: ...

    async def count_users_with_role(self, *, role: PlatformRole) -> int: ...
