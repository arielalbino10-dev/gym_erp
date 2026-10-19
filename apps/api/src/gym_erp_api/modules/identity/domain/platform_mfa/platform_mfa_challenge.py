"""Desafío MFA platform de vida corta."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from gym_erp_api.modules.identity.domain.platform_mfa.errors import InvalidMfaChallengeError
from gym_erp_api.modules.identity.domain.time_utils import truncate_utc_to_milliseconds, utc_now_ms
from gym_erp_api.modules.identity.domain.validators import require_user_uuid_v4
from gym_erp_api.shared_kernel.identifiers import new_uuid

DEFAULT_CHALLENGE_TTL = timedelta(minutes=5)
DEFAULT_MAX_ATTEMPTS = 5


@dataclass(frozen=True, slots=True)
class PlatformMfaChallenge:
    challenge_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    failed_attempts: int
    max_attempts: int
    consumed_at: datetime | None = None

    def __post_init__(self) -> None:
        require_user_uuid_v4(self.challenge_id, "challenge_id")
        require_user_uuid_v4(self.user_id)
        if self.failed_attempts < 0 or self.max_attempts < 1:
            raise InvalidMfaChallengeError("Contadores de intento inválidos.")
        if self.consumed_at is not None and self.failed_attempts > self.max_attempts:
            raise InvalidMfaChallengeError("Estado de desafío inconsistente.")

    @classmethod
    def create(
        cls,
        *,
        user_id: str,
        ttl: timedelta = DEFAULT_CHALLENGE_TTL,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        now: datetime | None = None,
    ) -> PlatformMfaChallenge:
        moment = truncate_utc_to_milliseconds(now) if now else utc_now_ms()
        return cls(
            challenge_id=require_user_uuid_v4(new_uuid(), "challenge_id"),
            user_id=require_user_uuid_v4(user_id),
            created_at=moment,
            expires_at=moment + ttl,
            failed_attempts=0,
            max_attempts=max_attempts,
        )

    def is_expired(self, moment: datetime) -> bool:
        return truncate_utc_to_milliseconds(moment) >= self.expires_at

    def is_consumed(self) -> bool:
        return self.consumed_at is not None

    def is_locked_out(self) -> bool:
        return self.failed_attempts >= self.max_attempts

    def assert_verifiable_at(self, moment: datetime) -> None:
        if self.is_consumed():
            raise InvalidMfaChallengeError("Desafío ya consumido.")
        if self.is_expired(moment):
            raise InvalidMfaChallengeError("Desafío expirado.")
        if self.is_locked_out():
            raise InvalidMfaChallengeError("Demasiados intentos fallidos.")

    def record_failed_attempt(self, *, now: datetime | None = None) -> PlatformMfaChallenge:
        moment = truncate_utc_to_milliseconds(now) if now else utc_now_ms()
        self.assert_verifiable_at(moment)
        return replace(
            self,
            failed_attempts=self.failed_attempts + 1,
        )

    def consume(self, *, now: datetime | None = None) -> PlatformMfaChallenge:
        moment = truncate_utc_to_milliseconds(now) if now else utc_now_ms()
        self.assert_verifiable_at(moment)
        return replace(self, consumed_at=moment)

    def mark_consumed_after_successful_totp(
        self, *, now: datetime | None = None
    ) -> PlatformMfaChallenge:
        """Marca consumido tras TOTP válido (sin re-evaluar lockout por intentos)."""
        moment = truncate_utc_to_milliseconds(now) if now else utc_now_ms()
        if self.is_consumed():
            raise InvalidMfaChallengeError("Desafío ya consumido.")
        if self.is_expired(moment):
            raise InvalidMfaChallengeError("Desafío expirado.")
        return replace(self, consumed_at=moment)
