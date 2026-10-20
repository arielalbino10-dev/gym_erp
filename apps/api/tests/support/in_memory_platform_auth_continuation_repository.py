from __future__ import annotations

import asyncio
from datetime import datetime

from gym_erp_api.modules.identity.domain.platform_auth.enums import PlatformAuthContinuationStatus
from gym_erp_api.modules.identity.domain.platform_auth.platform_auth_continuation import (
    PlatformAuthContinuation,
)


class InMemoryPlatformAuthContinuationRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, PlatformAuthContinuation] = {}
        self._by_token: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def insert(
        self, continuation: PlatformAuthContinuation, *, session: object | None = None
    ) -> None:
        self._by_id[continuation.continuation_id] = continuation
        self._by_token[continuation.token_hash] = continuation.continuation_id

    async def get_by_token_hash(
        self, token_hash: str, *, session: object | None = None
    ) -> PlatformAuthContinuation | None:
        cid = self._by_token.get(token_hash)
        return self._by_id.get(cid) if cid else None

    async def find_open_for_user(
        self, user_id: str, *, now: datetime, session: object | None = None
    ) -> PlatformAuthContinuation | None:
        for cont in self._by_id.values():
            if cont.user_id != user_id or cont.is_consumed():
                continue
            if cont.is_expired(now):
                continue
            return cont
        return None

    async def bind_challenge(
        self,
        continuation_id: str,
        *,
        challenge_id: str,
        now: datetime,
        session: object | None = None,
    ) -> PlatformAuthContinuation | None:
        async with self._lock:
            cont = self._by_id.get(continuation_id)
            if cont is None:
                return None
            if cont.status is not PlatformAuthContinuationStatus.PASSWORD_VERIFIED:
                return None
            try:
                updated = cont.bind_challenge(challenge_id=challenge_id, now=now)
            except Exception:
                return None
            self._by_id[continuation_id] = updated
            return updated

    async def bind_authorization(
        self,
        continuation_id: str,
        *,
        authorization_id: str,
        now: datetime,
        session: object | None = None,
    ) -> PlatformAuthContinuation | None:
        async with self._lock:
            cont = self._by_id.get(continuation_id)
            if cont is None:
                return None
            if cont.status is not PlatformAuthContinuationStatus.MFA_CHALLENGE_BOUND:
                return None
            try:
                updated = cont.bind_authorization(authorization_id=authorization_id, now=now)
            except Exception:
                return None
            self._by_id[continuation_id] = updated
            return updated

    async def consume_if_authorized(
        self,
        continuation_id: str,
        *,
        user_id: str,
        credential_version: int,
        now: datetime,
        session: object | None = None,
    ) -> PlatformAuthContinuation | None:
        async with self._lock:
            cont = self._by_id.get(continuation_id)
            if cont is None:
                return None
            if (
                cont.user_id != user_id
                or cont.credential_version != credential_version
                or cont.status is not PlatformAuthContinuationStatus.MFA_AUTHORIZED
            ):
                return None
            try:
                cont.assert_active_at(now)
                updated = cont.consume(now=now)
            except Exception:
                return None
            self._by_id[continuation_id] = updated
            return updated
