"""Repositorios MFA en memoria para pruebas unitarias (sin Mongo)."""

from __future__ import annotations

import asyncio
from datetime import datetime

from gym_erp_api.modules.identity.domain.platform_mfa.platform_mfa_challenge import (
    PlatformMfaChallenge,
)
from gym_erp_api.modules.identity.domain.platform_mfa.platform_mfa_session_authorization import (
    PlatformMfaSessionAuthorization,
)
from gym_erp_api.modules.identity.domain.platform_mfa.platform_totp_enrollment import (
    PlatformTotpEnrollment,
)


class InMemoryPlatformTotpEnrollmentRepository:
    def __init__(self) -> None:
        self._by_user: dict[str, PlatformTotpEnrollment] = {}

    async def get_by_user_id(
        self, user_id: str, *, session: object | None = None
    ) -> PlatformTotpEnrollment | None:
        return self._by_user.get(user_id)

    async def save(
        self, enrollment: PlatformTotpEnrollment, *, session: object | None = None
    ) -> None:
        self._by_user[enrollment.user_id] = enrollment


class InMemoryPlatformMfaChallengeRepository:
    def __init__(self) -> None:
        self._challenges: dict[str, PlatformMfaChallenge] = {}
        self._lock = asyncio.Lock()

    async def insert(
        self, challenge: PlatformMfaChallenge, *, session: object | None = None
    ) -> None:
        self._challenges[challenge.challenge_id] = challenge

    async def get_by_id(
        self, challenge_id: str, *, session: object | None = None
    ) -> PlatformMfaChallenge | None:
        return self._challenges.get(challenge_id)

    async def find_open_for_user(
        self, user_id: str, *, now: datetime, session: object | None = None
    ) -> PlatformMfaChallenge | None:
        for ch in self._challenges.values():
            if ch.user_id != user_id or ch.is_consumed():
                continue
            if ch.is_expired(now):
                continue
            return ch
        return None

    async def reserve_verification_attempt(
        self,
        challenge_id: str,
        *,
        user_id: str,
        now: datetime,
        session: object | None = None,
    ) -> bool:
        async with self._lock:
            ch = self._challenges.get(challenge_id)
            if ch is None or ch.user_id != user_id:
                return False
            try:
                ch.assert_verifiable_at(now)
            except Exception:
                return False
            self._challenges[challenge_id] = ch.record_failed_attempt(now=now)
            return True

    async def consume_if_valid(
        self,
        challenge_id: str,
        *,
        user_id: str,
        now: datetime,
        session: object | None = None,
    ) -> PlatformMfaChallenge | None:
        async with self._lock:
            ch = self._challenges.get(challenge_id)
            if ch is None or ch.user_id != user_id:
                return None
            try:
                consumed = ch.mark_consumed_after_successful_totp(now=now)
            except Exception:
                return None
            self._challenges[challenge_id] = consumed
            return consumed


class InMemoryPlatformMfaStepConsumptionRepository:
    def __init__(self) -> None:
        self._steps: set[tuple[str, int]] = set()
        self._lock = asyncio.Lock()

    async def try_register_step(
        self,
        *,
        user_id: str,
        time_counter: int,
        expires_at: datetime,
        session: object | None = None,
    ) -> bool:
        async with self._lock:
            key = (user_id, time_counter)
            if key in self._steps:
                return False
            self._steps.add(key)
            return True


class InMemoryPlatformMfaSessionAuthorizationRepository:
    def __init__(self) -> None:
        self._auths: dict[str, PlatformMfaSessionAuthorization] = {}
        self._lock = asyncio.Lock()

    async def insert(
        self,
        authorization: PlatformMfaSessionAuthorization,
        *,
        session: object | None = None,
    ) -> None:
        self._auths[authorization.authorization_id] = authorization

    async def consume_for_session(
        self,
        authorization_id: str,
        *,
        user_id: str,
        credential_version: int,
        now: datetime,
        session: object | None = None,
    ) -> bool:
        async with self._lock:
            auth = self._auths.get(authorization_id)
            if auth is None:
                return False
            if auth.user_id != user_id or auth.credential_version != credential_version:
                return False
            if auth.is_consumed() or auth.is_expired(now):
                return False
            self._auths[authorization_id] = PlatformMfaSessionAuthorization(
                authorization_id=auth.authorization_id,
                user_id=auth.user_id,
                challenge_id=auth.challenge_id,
                credential_version=auth.credential_version,
                issued_at=auth.issued_at,
                expires_at=auth.expires_at,
                consumed_at=now,
            )
            return True
