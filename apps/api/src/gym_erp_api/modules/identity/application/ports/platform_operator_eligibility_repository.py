"""Elegibilidad mínima para sesión platform (pre-RBAC H2-C)."""

from __future__ import annotations

from typing import Protocol


class PlatformOperatorEligibilityRepository(Protocol):
    async def is_eligible(self, *, user_id: str) -> bool: ...

    async def revoke_eligibility(self, *, user_id: str) -> None: ...
