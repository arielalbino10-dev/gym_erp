from datetime import datetime
from typing import Protocol

from gym_erp_api.modules.identity.domain.platform_mfa.platform_mfa_challenge import (
    PlatformMfaChallenge,
)


class PlatformMfaChallengeRepository(Protocol):
    async def insert(self, challenge: PlatformMfaChallenge) -> None: ...

    async def get_by_id(self, challenge_id: str) -> PlatformMfaChallenge | None: ...

    async def find_open_for_user(
        self, user_id: str, *, now: datetime
    ) -> PlatformMfaChallenge | None:
        """Desafío no consumido y no expirado para el usuario (como máximo uno)."""

    async def save(
        self, challenge: PlatformMfaChallenge, *, expected_updated_at: datetime
    ) -> None: ...

    async def reserve_verification_attempt(
        self,
        challenge_id: str,
        *,
        user_id: str,
        now: datetime,
    ) -> bool:
        """Reserva atómica de un intento (incrementa failed_attempts si aún hay cupo)."""

    async def consume_if_valid(
        self,
        challenge_id: str,
        *,
        user_id: str,
        now: datetime,
    ) -> PlatformMfaChallenge | None:
        """Consumo atómico si no expirado, no consumido y no bloqueado."""
