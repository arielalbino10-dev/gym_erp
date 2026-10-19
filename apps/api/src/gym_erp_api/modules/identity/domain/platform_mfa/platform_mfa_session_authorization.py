"""Autorización de un solo uso para emitir sesión platform tras MFA."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from gym_erp_api.modules.identity.domain.platform_mfa.errors import InvalidMfaAuthorizationError
from gym_erp_api.modules.identity.domain.time_utils import truncate_utc_to_milliseconds, utc_now_ms
from gym_erp_api.modules.identity.domain.validators import require_user_uuid_v4
from gym_erp_api.shared_kernel.identifiers import new_uuid

DEFAULT_AUTHORIZATION_TTL = timedelta(minutes=2)


@dataclass(frozen=True, slots=True)
class PlatformMfaSessionAuthorization:
    authorization_id: str
    user_id: str
    challenge_id: str
    credential_version: int
    issued_at: datetime
    expires_at: datetime
    consumed_at: datetime | None = None

    def __post_init__(self) -> None:
        require_user_uuid_v4(self.authorization_id, "authorization_id")
        require_user_uuid_v4(self.user_id)
        require_user_uuid_v4(self.challenge_id, "challenge_id")
        if self.credential_version < 0:
            raise InvalidMfaAuthorizationError("credential_version inválido.")

    @classmethod
    def issue(
        cls,
        *,
        user_id: str,
        challenge_id: str,
        credential_version: int,
        ttl: timedelta = DEFAULT_AUTHORIZATION_TTL,
        now: datetime | None = None,
    ) -> PlatformMfaSessionAuthorization:
        moment = truncate_utc_to_milliseconds(now) if now else utc_now_ms()
        return cls(
            authorization_id=require_user_uuid_v4(new_uuid(), "authorization_id"),
            user_id=require_user_uuid_v4(user_id),
            challenge_id=require_user_uuid_v4(challenge_id, "challenge_id"),
            credential_version=credential_version,
            issued_at=moment,
            expires_at=moment + ttl,
        )

    def is_expired(self, moment: datetime) -> bool:
        return truncate_utc_to_milliseconds(moment) >= self.expires_at

    def is_consumed(self) -> bool:
        return self.consumed_at is not None
