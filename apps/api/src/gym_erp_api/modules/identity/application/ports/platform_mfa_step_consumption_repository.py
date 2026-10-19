from datetime import datetime
from typing import Protocol


class PlatformMfaStepConsumptionRepository(Protocol):
    async def try_register_step(
        self,
        *,
        user_id: str,
        time_counter: int,
        expires_at: datetime,
    ) -> bool:
        """True si el paso TOTP queda registrado; False si ya fue usado (replay)."""
