"""Entidad UserIdentity — identidad humana global (gym_platform, ADR-0003)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from gym_erp_api.modules.identity.domain.enums import (
    IDENTITY_ALLOWED_TRANSITIONS,
    UserIdentityStatus,
)
from gym_erp_api.modules.identity.domain.errors import (
    InvalidIdentityFieldError,
    InvalidIdentityInvariantError,
    InvalidIdentityPersistenceError,
    InvalidIdentityStateTransitionError,
)
from gym_erp_api.modules.identity.domain.persistence_utils import parse_utc_datetime
from gym_erp_api.modules.identity.domain.time_utils import truncate_utc_to_milliseconds, utc_now_ms
from gym_erp_api.modules.identity.domain.validators import (
    normalize_identity_email,
    require_non_negative_credential_version,
    require_user_uuid_v4,
)
from gym_erp_api.shared_kernel.identifiers import new_uuid


def _ensure_utc(moment: datetime) -> datetime:
    return truncate_utc_to_milliseconds(moment)


@dataclass(frozen=True, slots=True)
class UserIdentity:
    user_id: str
    email: str
    email_normalized: str
    status: UserIdentityStatus
    credential_version: int
    created_at: datetime
    updated_at: datetime
    email_verified_at: datetime | None = None

    def __post_init__(self) -> None:
        require_user_uuid_v4(self.user_id)
        require_non_negative_credential_version(self.credential_version)
        if self.email_normalized != normalize_identity_email(self.email)[1]:
            raise InvalidIdentityFieldError("email_normalized no coincide con email.")
        self._validate_status_invariants()

    def _validate_status_invariants(self) -> None:
        needs_verified = (
            UserIdentityStatus.ACTIVE,
            UserIdentityStatus.LOCKED,
        )
        if self.status in needs_verified and self.email_verified_at is None:
            raise InvalidIdentityInvariantError(
                f"Identidad {self.status.value} requiere email_verified_at."
            )
        pending = UserIdentityStatus.PENDING_VERIFICATION
        if self.status is pending and self.email_verified_at is not None:
            raise InvalidIdentityInvariantError(
                "Identidad pending_verification no puede tener email_verified_at."
            )

    @classmethod
    def create(
        cls,
        *,
        email: str,
        user_id: str | None = None,
        now: datetime | None = None,
    ) -> UserIdentity:
        visible, normalized = normalize_identity_email(email)
        moment = _ensure_utc(now) if now is not None else utc_now_ms()
        uid = require_user_uuid_v4(user_id or new_uuid())
        return cls(
            user_id=uid,
            email=visible,
            email_normalized=normalized,
            status=UserIdentityStatus.PENDING_VERIFICATION,
            credential_version=0,
            created_at=moment,
            updated_at=moment,
            email_verified_at=None,
        )

    def transition_status(
        self,
        new_status: UserIdentityStatus,
        *,
        now: datetime | None = None,
    ) -> UserIdentity:
        target = UserIdentityStatus(new_status)
        allowed = IDENTITY_ALLOWED_TRANSITIONS.get(self.status, frozenset())
        if target not in allowed:
            raise InvalidIdentityStateTransitionError(
                f"Transición de identidad no permitida: {self.status.value} → {target.value}."
            )
        moment = _ensure_utc(now) if now is not None else utc_now_ms()
        if target is UserIdentityStatus.ACTIVE and self.email_verified_at is None:
            raise InvalidIdentityInvariantError(
                "No se puede activar sin email_verified_at (verifique correo antes)."
            )
        return replace(
            self,
            status=target,
            updated_at=moment,
        )

    def mark_email_verified(self, *, now: datetime | None = None) -> UserIdentity:
        moment = _ensure_utc(now) if now is not None else utc_now_ms()
        if self.status is not UserIdentityStatus.PENDING_VERIFICATION:
            raise InvalidIdentityStateTransitionError(
                "Solo pending_verification puede verificar correo hacia active."
            )
        return replace(
            self,
            status=UserIdentityStatus.ACTIVE,
            email_verified_at=moment,
            updated_at=moment,
        )

    def increment_credential_version(self, *, now: datetime | None = None) -> UserIdentity:
        moment = _ensure_utc(now) if now is not None else utc_now_ms()
        return replace(
            self,
            credential_version=self.credential_version + 1,
            updated_at=moment,
        )

    @classmethod
    def from_persistence(cls, raw: Mapping[str, Any]) -> UserIdentity:
        try:
            status = UserIdentityStatus(str(raw["status"]))
            verified_raw = raw.get("email_verified_at")
            verified = (
                parse_utc_datetime(verified_raw, "email_verified_at")
                if verified_raw is not None
                else None
            )
            return cls(
                user_id=str(raw["user_id"]),
                email=str(raw["email"]),
                email_normalized=str(raw["email_normalized"]),
                status=status,
                credential_version=int(raw["credential_version"]),
                created_at=parse_utc_datetime(raw["created_at"], "created_at"),
                updated_at=parse_utc_datetime(raw["updated_at"], "updated_at"),
                email_verified_at=verified,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidIdentityPersistenceError("Documento de identidad incompleto.") from exc
