"""Repositorio Mongo — platform_role_assignments (gym_platform)."""

from __future__ import annotations

from pymongo.asynchronous.collection import AsyncCollection

from gym_erp_api.modules.platform_admin.application.ports.platform_role_assignment_repository import (  # noqa: E501
    PlatformRoleAssignmentRepository,
)
from gym_erp_api.modules.platform_admin.domain.platform_role import PlatformRole
from gym_erp_api.modules.platform_admin.domain.platform_role_assignment import (
    PlatformRoleAssignment,
)
from gym_erp_api.modules.platform_admin.infrastructure.mongo.platform_role_assignment_mapper import (  # noqa: E501
    assignment_from_document,
    assignment_to_document,
)


class MongoPlatformRoleAssignmentRepository(PlatformRoleAssignmentRepository):
    def __init__(self, collection: AsyncCollection) -> None:
        self._collection = collection

    async def get_by_user_id(self, *, user_id: str) -> PlatformRoleAssignment | None:
        doc = await self._collection.find_one({"_id": user_id})
        if doc is None:
            return None
        return assignment_from_document(doc)

    async def upsert(self, *, assignment: PlatformRoleAssignment) -> None:
        await self._collection.replace_one(
            {"_id": assignment.user_id},
            assignment_to_document(assignment),
            upsert=True,
        )

    async def count_users_with_role(self, *, role: PlatformRole) -> int:
        return await self._collection.count_documents({"roles": role.value})
