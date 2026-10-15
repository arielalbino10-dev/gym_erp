"""Repositorio platform para tenants — sin listados globales."""

from __future__ import annotations

from typing import Any

from pymongo.asynchronous.collection import AsyncCollection

from gym_erp_api.infrastructure.mongo.session_support import session_mongo_kwargs
from gym_erp_api.modules.organization.domain.errors import OrganizationEntityNotFoundError
from gym_erp_api.modules.organization.domain.tenant import Tenant
from gym_erp_api.modules.organization.domain.validators import require_uuid_v4
from gym_erp_api.modules.organization.infrastructure.mongo.tenant_document_mapper import (
    tenant_from_document,
    tenant_to_document,
)


class PlatformTenantRepository:
    """Acceso acotado a ``gym_platform.tenants`` (no sustituye scope operational)."""

    def __init__(self, collection: AsyncCollection) -> None:
        self._collection = collection

    def _session_kw(self, session: object | None) -> dict[str, Any]:
        return session_mongo_kwargs(
            session,
            expected_client=self._collection.database.client,
        )

    async def insert(self, tenant: Tenant, *, session: object | None = None) -> None:
        require_uuid_v4(tenant.tenant_id, "tenant_id")
        await self._collection.insert_one(
            tenant_to_document(tenant),
            **self._session_kw(session),
        )

    async def get_by_id(self, tenant_id: str, *, session: object | None = None) -> Tenant | None:
        tid = require_uuid_v4(tenant_id, "tenant_id")
        raw = await self._collection.find_one({"_id": tid}, **self._session_kw(session))
        if raw is None:
            return None
        return tenant_from_document(raw)

    async def exists_by_id(self, tenant_id: str, *, session: object | None = None) -> bool:
        tid = require_uuid_v4(tenant_id, "tenant_id")
        count = await self._collection.count_documents(
            {"_id": tid},
            limit=1,
            **self._session_kw(session),
        )
        return count > 0

    async def save(self, tenant: Tenant, *, session: object | None = None) -> None:
        tid = require_uuid_v4(tenant.tenant_id, "tenant_id")
        doc = tenant_to_document(tenant)
        update_fields: dict[str, Any] = {key: value for key, value in doc.items() if key != "_id"}
        result = await self._collection.update_one(
            {"_id": tid},
            {"$set": update_fields},
            **self._session_kw(session),
        )
        if result.matched_count == 0:
            raise OrganizationEntityNotFoundError(f"Tenant no encontrado: {tid}.")
