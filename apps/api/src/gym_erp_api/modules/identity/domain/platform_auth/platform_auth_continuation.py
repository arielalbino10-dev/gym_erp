"""Continuidad server-side del login platform (pre-sesión, sin HTTP)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from gym_erp_api.modules.identity.domain.platform_auth.enums import PlatformAuthContinuationStatus
from gym_erp_api.modules.identity.domain.platform_auth.errors import (
    InvalidPlatformAuthContinuationError,
)
from gym_erp_api.modules.identity.domain.time_utils import truncate_utc_to_milliseconds, utc_now_ms
from gym_erp_api.modules.identity.domain.validators import require_user_uuid_v4
from gym_erp_api.shared_kernel.identifiers import new_uuid

DEFAULT_CONTINUATION_TTL = timedelta(minutes=10)


@dataclass(frozen=True, slots=True)
class PlatformAuthContinuation:
    continuation_id: str
    token_hash: str
    user_id: str
    credential_version: int
    password_verified_at: datetime
    status: PlatformAuthContinuationStatus
    expires_at: datetime
    created_at: datetime
    challenge_id: str | None = None
    authorization_id: str | None = None
    consumed_at: datetime | None = None

    def __post_init__(self) -> None:
        require_user_uuid_v4(self.continuation_id, "continuation_id")
        require_user_uuid_v4(self.user_id)
        if self.credential_version < 0:
            raise InvalidPlatformAuthContinuationError("credential_version inválido.")
        if self.challenge_id is not None:
            require_user_uuid_v4(self.challenge_id, "challenge_id")
        if self.authorization_id is not None:
            require_user_uuid_v4(self.authorization_id, "authorization_id")

    @classmethod
    def begin(
        cls,
        *,
        token_hash: str,
        user_id: str,
        credential_version: int,
        password_verified_at: datetime,
        ttl: timedelta = DEFAULT_CONTINUATION_TTL,
        now: datetime | None = None,
    ) -> PlatformAuthContinuation:
        moment = truncate_utc_to_milliseconds(now) if now else utc_now_ms()
        verified = truncate_utc_to_milliseconds(password_verified_at)
        return cls(
            continuation_id=require_user_uuid_v4(new_uuid(), "continuation_id"),
            token_hash=token_hash,
            user_id=require_user_uuid_v4(user_id),
            credential_version=credential_version,
            password_verified_at=verified,
            status=PlatformAuthContinuationStatus.PASSWORD_VERIFIED,
            expires_at=moment + ttl,
            created_at=moment,
        )

    def is_expired(self, moment: datetime) -> bool:
        return truncate_utc_to_milliseconds(moment) >= self.expires_at

    def is_consumed(self) -> bool:
        return self.consumed_at is not None

    def assert_active_at(self, moment: datetime) -> None:
        if self.is_consumed():
            raise InvalidPlatformAuthContinuationError("Continuación ya consumida.")
        if self.is_expired(moment):
            raise InvalidPlatformAuthContinuationError("Continuación expirada.")

    def bind_challenge(
        self, *, challenge_id: str, now: datetime | None = None
    ) -> PlatformAuthContinuation:
        moment = truncate_utc_to_milliseconds(now) if now else utc_now_ms()
        self.assert_active_at(moment)
        if self.status is not PlatformAuthContinuationStatus.PASSWORD_VERIFIED:
            raise InvalidPlatformAuthContinuationError("Estado incompatible para desafío.")
        cid = require_user_uuid_v4(challenge_id, "challenge_id")
        return replace(
            self,
            status=PlatformAuthContinuationStatus.MFA_CHALLENGE_BOUND,
            challenge_id=cid,
        )

    def bind_authorization(
        self, *, authorization_id: str, now: datetime | None = None
    ) -> PlatformAuthContinuation:
        moment = truncate_utc_to_milliseconds(now) if now else utc_now_ms()
        self.assert_active_at(moment)
        if self.status is not PlatformAuthContinuationStatus.MFA_CHALLENGE_BOUND:
            raise InvalidPlatformAuthContinuationError("Estado incompatible para autorización.")
        aid = require_user_uuid_v4(authorization_id, "authorization_id")
        return replace(
            self,
            status=PlatformAuthContinuationStatus.MFA_AUTHORIZED,
            authorization_id=aid,
        )

    def consume(self, *, now: datetime | None = None) -> PlatformAuthContinuation:
        moment = truncate_utc_to_milliseconds(now) if now else utc_now_ms()
        self.assert_active_at(moment)
        if self.status is not PlatformAuthContinuationStatus.MFA_AUTHORIZED:
            raise InvalidPlatformAuthContinuationError("MFA no completada.")
        if self.authorization_id is None:
            raise InvalidPlatformAuthContinuationError("Sin autorización MFA.")
        return replace(self, consumed_at=moment)
