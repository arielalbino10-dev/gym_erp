from datetime import datetime
from typing import Protocol

from gym_erp_api.modules.identity.domain.platform_mfa.platform_mfa_session_authorization import (
    PlatformMfaSessionAuthorization,
)


class PlatformMfaSessionAuthorizationRepository(Protocol):
    async def insert(self, authorization: PlatformMfaSessionAuthorization) -> None: ...

    async def consume_for_session(
        self,
        authorization_id: str,
        *,
        user_id: str,
        credential_version: int,
        now: datetime,
    ) -> bool:
        """True si consumió autorización válida; False si inválida/expirada/usada."""
