"""Repositorio en memoria para elegibilidad platform (tests unitarios)."""

from __future__ import annotations


class InMemoryPlatformOperatorEligibilityRepository:
    def __init__(self) -> None:
        self._eligible: set[str] = set()

    async def is_eligible(self, *, user_id: str) -> bool:
        return user_id in self._eligible

    def grant(self, user_id: str) -> None:
        self._eligible.add(user_id)

    async def revoke_eligibility(self, *, user_id: str) -> None:
        self._eligible.discard(user_id)
