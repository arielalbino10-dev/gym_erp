from __future__ import annotations

from datetime import datetime
from typing import Any

from gym_erp_api.modules.platform_admin.application.ports.platform_audit_repository import (
    PlatformAuditRepository,
)
from gym_erp_api.modules.platform_admin.domain.platform_audit_event import PlatformAuditEvent


class RecordPlatformAuditEventUseCase:
    def __init__(self, *, audit: PlatformAuditRepository) -> None:
        self._audit = audit

    async def execute(
        self,
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
        event = PlatformAuditEvent.create(
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            recorded_at=recorded_at,
            correlation_id=correlation_id,
            metadata=metadata,
        )
        await self._audit.append(event=event)
        return event
