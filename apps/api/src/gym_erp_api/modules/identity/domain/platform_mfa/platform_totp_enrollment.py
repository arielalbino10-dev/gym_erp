"""Enrolamiento TOTP platform por user_id."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from gym_erp_api.modules.identity.domain.platform_mfa.encrypted_secret import EncryptedMfaSecret
from gym_erp_api.modules.identity.domain.platform_mfa.enums import TotpEnrollmentStatus
from gym_erp_api.modules.identity.domain.platform_mfa.errors import InvalidTotpEnrollmentError
from gym_erp_api.modules.identity.domain.time_utils import truncate_utc_to_milliseconds, utc_now_ms
from gym_erp_api.modules.identity.domain.validators import require_user_uuid_v4


@dataclass(frozen=True, slots=True)
class PlatformTotpEnrollment:
    user_id: str
    status: TotpEnrollmentStatus
    encrypted_secret: EncryptedMfaSecret
    created_at: datetime
    updated_at: datetime
    enabled_at: datetime | None = None

    def __post_init__(self) -> None:
        require_user_uuid_v4(self.user_id)
        if self.status is TotpEnrollmentStatus.ENABLED and self.enabled_at is None:
            raise InvalidTotpEnrollmentError("enabled requiere enabled_at.")
        if self.status is TotpEnrollmentStatus.PENDING and self.enabled_at is not None:
            raise InvalidTotpEnrollmentError("pending no puede tener enabled_at.")

    @classmethod
    def begin_pending(
        cls,
        *,
        user_id: str,
        encrypted_secret: EncryptedMfaSecret,
        now: datetime | None = None,
    ) -> PlatformTotpEnrollment:
        moment = truncate_utc_to_milliseconds(now) if now else utc_now_ms()
        return cls(
            user_id=require_user_uuid_v4(user_id),
            status=TotpEnrollmentStatus.PENDING,
            encrypted_secret=encrypted_secret,
            created_at=moment,
            updated_at=moment,
        )

    def activate(self, *, now: datetime | None = None) -> PlatformTotpEnrollment:
        if self.status is not TotpEnrollmentStatus.PENDING:
            raise InvalidTotpEnrollmentError("Solo pending puede activarse.")
        moment = truncate_utc_to_milliseconds(now) if now else utc_now_ms()
        return replace(
            self,
            status=TotpEnrollmentStatus.ENABLED,
            enabled_at=moment,
            updated_at=moment,
        )

    def disable(self, *, now: datetime | None = None) -> PlatformTotpEnrollment:
        moment = truncate_utc_to_milliseconds(now) if now else utc_now_ms()
        return replace(
            self,
            status=TotpEnrollmentStatus.DISABLED,
            updated_at=moment,
        )
