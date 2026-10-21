from __future__ import annotations

from typing import Protocol

from gym_erp_api.modules.platform_admin.domain.platform_audit_event import PlatformAuditEvent


class PlatformAuditRepository(Protocol):
    async def append(self, *, event: PlatformAuditEvent) -> None: ...
