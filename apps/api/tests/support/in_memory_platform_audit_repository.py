from __future__ import annotations

from gym_erp_api.modules.platform_admin.domain.platform_audit_event import PlatformAuditEvent


class InMemoryPlatformAuditRepository:
    def __init__(self) -> None:
        self.events: list[PlatformAuditEvent] = []

    async def append(self, *, event: PlatformAuditEvent) -> None:
        self.events.append(event)
