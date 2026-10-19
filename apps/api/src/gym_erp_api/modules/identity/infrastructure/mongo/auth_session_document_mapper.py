"""Mapper AuthSession ↔ documento MongoDB (``auth_sessions``)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from gym_erp_api.modules.identity.domain.auth_session import AuthSession
from gym_erp_api.modules.identity.domain.errors import InvalidIdentityPersistenceError
from gym_erp_api.modules.identity.domain.persistence_utils import parse_utc_datetime
from gym_erp_api.modules.identity.domain.session_kind import SessionKind

AUTH_SESSIONS_COLLECTION = "auth_sessions"


def auth_session_to_document(session: AuthSession) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "_id": session.session_id,
        "session_id": session.session_id,
        "token_hash": session.token_hash,
        "user_id": session.user_id,
        "session_kind": session.session_kind.value,
        "created_at": session.created_at,
        "expires_at": session.expires_at,
        "idle_expires_at": session.idle_expires_at,
        "last_seen_at": session.last_seen_at,
        "credential_version": session.credential_version,
    }
    if session.active_tenant_id is not None:
        doc["active_tenant_id"] = session.active_tenant_id
    if session.revoked_at is not None:
        doc["revoked_at"] = session.revoked_at
        doc["revocation_reason"] = session.revocation_reason
    return doc


def auth_session_from_document(raw: Mapping[str, Any]) -> AuthSession:
    try:
        revoked_raw = raw.get("revoked_at")
        revoked = parse_utc_datetime(revoked_raw, "revoked_at") if revoked_raw is not None else None
        tenant_raw = raw.get("active_tenant_id")
        return AuthSession(
            session_id=str(raw["session_id"]),
            token_hash=str(raw["token_hash"]),
            user_id=str(raw["user_id"]),
            session_kind=SessionKind(str(raw["session_kind"])),
            created_at=parse_utc_datetime(raw["created_at"], "created_at"),
            expires_at=parse_utc_datetime(raw["expires_at"], "expires_at"),
            idle_expires_at=parse_utc_datetime(raw["idle_expires_at"], "idle_expires_at"),
            last_seen_at=parse_utc_datetime(raw["last_seen_at"], "last_seen_at"),
            credential_version=int(raw["credential_version"]),
            active_tenant_id=str(tenant_raw) if tenant_raw is not None else None,
            revoked_at=revoked,
            revocation_reason=str(raw["revocation_reason"]) if revoked is not None else None,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidIdentityPersistenceError("Documento de sesión incompleto.") from exc
