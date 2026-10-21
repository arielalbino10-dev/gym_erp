"""Sesión de autenticación opaca (solo hash de token persistido, ADR-0003)."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

from gym_erp_api.modules.identity.domain.errors import (
    InvalidSessionFieldError,
    SessionExpiredError,
    SessionRevokedError,
)
from gym_erp_api.modules.identity.domain.session_kind import SessionKind
from gym_erp_api.modules.identity.domain.time_utils import truncate_utc_to_milliseconds, utc_now_ms
from gym_erp_api.modules.identity.domain.validators import require_user_uuid_v4
from gym_erp_api.shared_kernel.identifiers import new_uuid

_TOKEN_HASH_HEX_LEN = 64


def _ensure_utc(moment: datetime) -> datetime:
    return truncate_utc_to_milliseconds(moment)


@dataclass(frozen=True, slots=True)
class AuthSession:
    session_id: str
    token_hash: str = field(repr=False)
    user_id: str
    session_kind: SessionKind
    created_at: datetime
    expires_at: datetime
    idle_expires_at: datetime
    last_seen_at: datetime
    credential_version: int
    active_tenant_id: str | None = None
    gym_membership_authz_epoch: int | None = None
    revoked_at: datetime | None = None
    revocation_reason: str | None = None

    def __post_init__(self) -> None:
        require_user_uuid_v4(self.session_id, "session_id")
        require_user_uuid_v4(self.user_id)
        if self.active_tenant_id is not None:
            require_user_uuid_v4(self.active_tenant_id, "active_tenant_id")
        if self.gym_membership_authz_epoch is not None:
            if self.gym_membership_authz_epoch < 0:
                raise InvalidSessionFieldError("gym_membership_authz_epoch inválido.")
            if self.active_tenant_id is None:
                raise InvalidSessionFieldError(
                    "gym_membership_authz_epoch requiere active_tenant_id."
                )
        if (
            not isinstance(self.token_hash, str)
            or len(self.token_hash) != _TOKEN_HASH_HEX_LEN
            or any(ch not in "0123456789abcdef" for ch in self.token_hash)
        ):
            raise InvalidSessionFieldError("token_hash debe ser SHA-256 hex.")
        if self.credential_version < 0:
            raise InvalidSessionFieldError("credential_version inválido.")
        if self.revoked_at is not None and not self.revocation_reason:
            raise InvalidSessionFieldError(
                "revocation_reason requerido si revoked_at está definido."
            )

    @classmethod
    def create(
        cls,
        *,
        user_id: str,
        session_kind: SessionKind,
        token_hash: str,
        expires_at: datetime,
        idle_expires_at: datetime,
        credential_version: int,
        session_id: str | None = None,
        active_tenant_id: str | None = None,
        now: datetime | None = None,
    ) -> AuthSession:
        moment = _ensure_utc(now) if now is not None else utc_now_ms()
        exp = _ensure_utc(expires_at)
        idle = _ensure_utc(idle_expires_at)
        if idle > exp:
            raise InvalidSessionFieldError("idle_expires_at no puede ser posterior a expires_at.")
        return cls(
            session_id=require_user_uuid_v4(session_id or new_uuid(), "session_id"),
            token_hash=token_hash,
            user_id=require_user_uuid_v4(user_id),
            session_kind=SessionKind(session_kind),
            active_tenant_id=(
                require_user_uuid_v4(active_tenant_id, "active_tenant_id")
                if active_tenant_id
                else None
            ),
            created_at=moment,
            expires_at=exp,
            idle_expires_at=idle,
            last_seen_at=moment,
            credential_version=credential_version,
        )

    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    def assert_usable_at(self, moment: datetime) -> None:
        """Expiración y revocación — verificación explícita (TTL Mongo es solo limpieza)."""
        now = _ensure_utc(moment)
        if self.is_revoked():
            raise SessionRevokedError("Sesión revocada.")
        if now >= self.expires_at:
            raise SessionExpiredError("Sesión expirada (TTL absoluto).")
        if now >= self.idle_expires_at:
            raise SessionExpiredError("Sesión expirada por inactividad.")

    def revoke(self, *, reason: str, now: datetime | None = None) -> AuthSession:
        if self.is_revoked():
            return self
        moment = _ensure_utc(now) if now is not None else utc_now_ms()
        cleaned = reason.strip()
        if not cleaned:
            raise InvalidSessionFieldError("Motivo de revocación requerido.")
        return replace(
            self,
            revoked_at=moment,
            revocation_reason=cleaned,
        )

    def with_gym_tenant_selection(
        self,
        *,
        active_tenant_id: str,
        membership_authz_epoch: int,
        now: datetime | None = None,
    ) -> AuthSession:
        if self.session_kind is not SessionKind.GYM:
            raise InvalidSessionFieldError("Selección de tenant solo aplica a sesiones gym.")
        tid = require_user_uuid_v4(active_tenant_id, "active_tenant_id")
        if membership_authz_epoch < 0:
            raise InvalidSessionFieldError("membership_authz_epoch inválido.")
        moment = _ensure_utc(now) if now is not None else utc_now_ms()
        return replace(
            self,
            active_tenant_id=tid,
            gym_membership_authz_epoch=membership_authz_epoch,
            last_seen_at=moment,
        )

    def touch_activity(
        self,
        *,
        idle_expires_at: datetime,
        now: datetime | None = None,
    ) -> AuthSession:
        moment = _ensure_utc(now) if now is not None else utc_now_ms()
        idle = _ensure_utc(idle_expires_at)
        if idle > self.expires_at:
            raise InvalidSessionFieldError("idle_expires_at no puede exceder expires_at.")
        return replace(
            self,
            last_seen_at=moment,
            idle_expires_at=idle,
        )
