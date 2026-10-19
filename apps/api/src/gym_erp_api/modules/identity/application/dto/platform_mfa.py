"""Ticket MFA platform — solo emitido por PlatformMfaVerificationPort (no desde cliente)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from gym_erp_api.modules.identity.domain.validators import require_user_uuid_v4


@dataclass(frozen=True, slots=True)
class PlatformMfaVerificationTicket:
    """Marcador interno post-MFA (H2-B.5).

    No es prueba criptográfica: cualquier código en el mismo proceso puede instanciarlo.
    La emisión platform debe estar bloqueada por ``PlatformSessionEmissionGate`` hasta
    que el puerto MFA emita tickets con autenticidad verificable.
    """

    user_id: str
    verified_at: datetime

    def __post_init__(self) -> None:
        require_user_uuid_v4(self.user_id)
        if self.verified_at.tzinfo is None:
            raise ValueError("verified_at debe ser timezone-aware.")
