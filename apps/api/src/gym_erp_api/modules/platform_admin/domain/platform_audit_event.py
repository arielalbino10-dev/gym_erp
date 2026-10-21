"""Evento append-only de auditoría administrativa platform."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from gym_erp_api.shared_kernel.identifiers import new_uuid


@dataclass(frozen=True, slots=True)
class PlatformAuditEvent:
    event_id: str
    actor_user_id: str
    action: str
    resource_type: str
    resource_id: str
    outcome: str
    recorded_at: datetime
    correlation_id: str | None = None
    metadata: dict[str, Any] | None = None

    @classmethod
    def create(
        cls,
        *,
        actor_user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        outcome: str,
        recorded_at: datetime,
        correlation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PlatformAuditEvent:
        if not actor_user_id.strip():
            raise ValueError("actor_user_id requerido.")
        if not action.strip() or not resource_type.strip() or not resource_id.strip():
            raise ValueError("action, resource_type y resource_id son obligatorios.")
        safe_meta = None
        if metadata:
            safe_meta = {k: v for k, v in metadata.items() if k not in _FORBIDDEN_META_KEYS}
        return cls(
            event_id=new_uuid(),
            actor_user_id=actor_user_id.strip(),
            action=action.strip(),
            resource_type=resource_type.strip(),
            resource_id=resource_id.strip(),
            outcome=outcome.strip(),
            recorded_at=recorded_at,
            correlation_id=correlation_id.strip() if correlation_id else None,
            metadata=safe_meta,
        )


_FORBIDDEN_META_KEYS = frozenset(
    {
        "password",
        "token",
        "secret",
        "mfa",
        "csrf",
        "session_token",
    },
)
