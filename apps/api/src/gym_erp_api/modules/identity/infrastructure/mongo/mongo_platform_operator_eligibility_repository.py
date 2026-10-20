"""Persistencia de operadores platform elegibles (gym_platform)."""

from __future__ import annotations

from typing import Any

from pymongo.asynchronous.collection import AsyncCollection

PLATFORM_OPERATOR_ELIGIBILITIES_COLLECTION = "platform_operator_eligibilities"


class MongoPlatformOperatorEligibilityRepository:
    def __init__(self, collection: AsyncCollection) -> None:
        self._collection = collection

    async def is_eligible(self, *, user_id: str) -> bool:
        doc = await self._collection.find_one({"_id": user_id, "eligible": True})
        return doc is not None

    async def grant_eligibility(
        self,
        *,
        user_id: str,
        granted_at: Any,
        session: object | None = None,
    ) -> None:
        await self._collection.replace_one(
            {"_id": user_id},
            {"_id": user_id, "eligible": True, "granted_at": granted_at},
            upsert=True,
        )

    async def revoke_eligibility(self, *, user_id: str) -> None:
        await self._collection.delete_one({"_id": user_id})
