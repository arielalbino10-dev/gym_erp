"""Repositorio MongoDB de TenantMembership (gym_platform)."""

from __future__ import annotations

from typing import Any

from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import DuplicateKeyError, PyMongoError

from gym_erp_api.infrastructure.mongo.session_support import session_mongo_kwargs
from gym_erp_api.modules.access.application.errors import (
    MembershipDuplicateError,
    MembershipStorageError,
    MembershipUpdateConflictError,
)
from gym_erp_api.modules.access.domain.enums import MembershipStatus
from gym_erp_api.modules.access.domain.errors import AccessDomainError
from gym_erp_api.modules.access.domain.tenant_membership import TenantMembership
from gym_erp_api.modules.access.infrastructure.mongo.access_index_specs import (
    duplicate_key_field,
)
from gym_erp_api.modules.access.infrastructure.mongo.membership_document_mapper import (
    membership_from_document,
    membership_to_document,
)
from gym_erp_api.modules.organization.domain.validators import require_uuid_v4


class MongoTenantMembershipRepository:
    """Acceso a ``tenant_memberships`` en gym_platform."""

    def __init__(self, collection: AsyncCollection) -> None:
        self._collection = collection

    def _session_kw(self, session: object | None) -> dict[str, Any]:
        return session_mongo_kwargs(
            session,
            expected_client=self._collection.database.client,
        )

    async def insert(
        self,
        membership: TenantMembership,
        *,
        session: object | None = None,
    ) -> None:
        doc = membership_to_document(membership)
        try:
            await self._collection.insert_one(doc, **self._session_kw(session))
        except DuplicateKeyError as exc:
            field = duplicate_key_field(exc)
            if field in {"uniq_tenant_user", "tenant_id", "user_id"}:
                raise MembershipDuplicateError(
                    "Membresía canónica duplicada para tenant_id y user_id."
                ) from None
            raise MembershipDuplicateError("Clave de membresía duplicada.") from None
        except PyMongoError as exc:
            raise MembershipStorageError("Error al insertar membresía.") from exc

    async def get_by_id(
        self,
        membership_id: str,
        *,
        session: object | None = None,
    ) -> TenantMembership | None:
        mid = require_uuid_v4(membership_id, "membership_id")
        raw = await self._collection.find_one({"_id": mid}, **self._session_kw(session))
        if raw is None:
            return None
        return self._document_to_membership(raw)

    async def get_by_user_and_tenant(
        self,
        *,
        user_id: str,
        tenant_id: str,
        session: object | None = None,
    ) -> TenantMembership | None:
        uid = require_uuid_v4(user_id, "user_id")
        tid = require_uuid_v4(tenant_id, "tenant_id")
        raw = await self._collection.find_one(
            {"user_id": uid, "tenant_id": tid},
            **self._session_kw(session),
        )
        if raw is None:
            return None
        return self._document_to_membership(raw)

    async def list_active_by_user_id(
        self,
        user_id: str,
        *,
        session: object | None = None,
    ) -> tuple[TenantMembership, ...]:
        uid = require_uuid_v4(user_id, "user_id")
        cursor = self._collection.find(
            {"user_id": uid, "status": MembershipStatus.ACTIVE.value},
            **self._session_kw(session),
        )
        docs = [doc async for doc in cursor]
        return tuple(self._document_to_membership(doc) for doc in docs)

    def _document_to_membership(self, raw: dict[str, Any]) -> TenantMembership:
        try:
            return membership_from_document(raw)
        except AccessDomainError as exc:
            raise MembershipStorageError("Documento de membresía ilegible.") from exc

    async def save(
        self,
        membership: TenantMembership,
        *,
        expected_authz_epoch: int,
        session: object | None = None,
    ) -> None:
        mid = require_uuid_v4(membership.membership_id, "membership_id")
        if expected_authz_epoch < 0:
            raise MembershipStorageError("expected_authz_epoch inválido.")
        doc = membership_to_document(membership)
        try:
            result = await self._collection.replace_one(
                {
                    "_id": mid,
                    "user_id": membership.user_id,
                    "tenant_id": membership.tenant_id,
                    "authz_epoch": expected_authz_epoch,
                },
                doc,
                **self._session_kw(session),
            )
        except PyMongoError as exc:
            raise MembershipStorageError("Error al actualizar membresía.") from exc
        if result.matched_count == 0:
            existing = await self.get_by_id(mid, session=session)
            if existing is None:
                raise MembershipStorageError("Membresía no encontrada para actualizar.")
            raise MembershipUpdateConflictError("Conflicto al actualizar membresía.")
