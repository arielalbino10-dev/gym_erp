from __future__ import annotations

from datetime import UTC, datetime

from gym_erp_api.modules.platform_admin.domain.platform_audit_event import PlatformAuditEvent

_MOMENT = datetime(2026, 11, 1, tzinfo=UTC)


def test_audit_event_strips_sensitive_metadata_keys():
    event = PlatformAuditEvent.create(
        actor_user_id="actor-1",
        action="platform.role_assignment.upsert",
        resource_type="platform_operator",
        resource_id="target-1",
        outcome="success",
        recorded_at=_MOMENT,
        metadata={"roles": ["root_admin"], "password": "must-not-persist", "token": "x"},
    )
    assert event.metadata == {"roles": ["root_admin"]}
