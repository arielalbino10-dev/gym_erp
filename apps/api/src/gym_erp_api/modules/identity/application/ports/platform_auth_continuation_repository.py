from datetime import datetime
from typing import Protocol

from gym_erp_api.modules.identity.domain.platform_auth.platform_auth_continuation import (
    PlatformAuthContinuation,
)


class PlatformAuthContinuationRepository(Protocol):
    async def insert(self, continuation: PlatformAuthContinuation) -> None: ...

    async def get_by_token_hash(self, token_hash: str) -> PlatformAuthContinuation | None: ...

    async def find_open_for_user(
        self, user_id: str, *, now: datetime
    ) -> PlatformAuthContinuation | None: ...

    async def bind_challenge(
        self,
        continuation_id: str,
        *,
        challenge_id: str,
        now: datetime,
    ) -> PlatformAuthContinuation | None: ...

    async def bind_authorization(
        self,
        continuation_id: str,
        *,
        authorization_id: str,
        now: datetime,
    ) -> PlatformAuthContinuation | None: ...

    async def consume_if_authorized(
        self,
        continuation_id: str,
        *,
        user_id: str,
        credential_version: int,
        now: datetime,
    ) -> PlatformAuthContinuation | None: ...
