from __future__ import annotations

from pymongo.asynchronous.collection import AsyncCollection

from gym_erp_api.modules.platform_admin.application.ports.platform_audit_repository import (
    PlatformAuditRepository,
)
from gym_erp_api.modules.platform_admin.domain.platform_audit_event import PlatformAuditEvent
from gym_erp_api.modules.platform_admin.infrastructure.mongo.platform_audit_mapper import (
    audit_event_to_document,
)


class MongoPlatformAuditRepository(PlatformAuditRepository):
    def __init__(self, collection: AsyncCollection) -> None:
        self._collection = collection

    async def append(self, *, event: PlatformAuditEvent) -> None:
        await self._collection.insert_one(audit_event_to_document(event))
