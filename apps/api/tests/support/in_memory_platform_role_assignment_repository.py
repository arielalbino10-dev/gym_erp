from __future__ import annotations

from gym_erp_api.modules.platform_admin.domain.platform_role import PlatformRole
from gym_erp_api.modules.platform_admin.domain.platform_role_assignment import (
    PlatformRoleAssignment,
)


class InMemoryPlatformRoleAssignmentRepository:
    def __init__(self) -> None:
        self._by_user: dict[str, PlatformRoleAssignment] = {}

    async def get_by_user_id(self, *, user_id: str) -> PlatformRoleAssignment | None:
        return self._by_user.get(user_id)

    async def upsert(self, *, assignment: PlatformRoleAssignment) -> None:
        self._by_user[assignment.user_id] = assignment

    async def count_users_with_role(self, *, role: PlatformRole) -> int:
        return sum(1 for a in self._by_user.values() if role in a.roles)
