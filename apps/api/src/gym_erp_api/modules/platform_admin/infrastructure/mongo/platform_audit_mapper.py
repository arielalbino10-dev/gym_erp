from __future__ import annotations

from typing import Any

from gym_erp_api.modules.platform_admin.domain.platform_audit_event import PlatformAuditEvent

PLATFORM_AUDIT_EVENTS_COLLECTION = "platform_audit_events"


def audit_event_to_document(event: PlatformAuditEvent) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "_id": event.event_id,
        "actor_user_id": event.actor_user_id,
        "action": event.action,
        "resource_type": event.resource_type,
        "resource_id": event.resource_id,
        "outcome": event.outcome,
        "recorded_at": event.recorded_at,
    }
    if event.correlation_id is not None:
        doc["correlation_id"] = event.correlation_id
    if event.metadata:
        doc["metadata"] = event.metadata
    return doc
