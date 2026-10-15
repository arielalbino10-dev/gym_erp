"""Repositorio operational con alcance obligatorio de tenant."""

from __future__ import annotations

from typing import Any

from pymongo.asynchronous.collection import AsyncCollection

from gym_erp_api.infrastructure.mongo.filter_policy import (
    build_aggregation_pipeline,
    build_mutation_scoped_filter,
    build_scoped_filter,
    build_trusted_branch_id_mutation_filter,
    build_trusted_branch_id_read_filter,
    prepare_insert_document,
    prepare_insert_many,
    sanitize_update,
)
from gym_erp_api.infrastructure.mongo.session_support import ensure_pymongo_session
from gym_erp_api.shared_kernel.exceptions import ForbiddenMongoOperatorError
from gym_erp_api.shared_kernel.tenant_context import TenantContext

_FORBIDDEN_KWARGS = frozenset(
    {
        "upsert",
        "bypass_document_validation",
        "array_filters",
        "allowDiskUse",
    }
)

_KWARGS_FIND_ONE = frozenset({"session", "hint", "max_time_ms"})
_KWARGS_FIND = frozenset({"session", "hint", "max_time_ms", "limit", "skip", "sort", "projection"})
_KWARGS_COUNT = frozenset({"session", "hint", "max_time_ms"})
_KWARGS_WRITE = frozenset({"session", "hint"})
_KWARGS_INSERT = frozenset({"session"})
_KWARGS_AGGREGATE = frozenset({"session", "batchSize", "maxTimeMS"})


def _pick_allowed_kwargs(allowed: frozenset[str], kwargs: dict[str, Any]) -> dict[str, Any]:
    for key in kwargs:
        if key in _FORBIDDEN_KWARGS:
            raise ForbiddenMongoOperatorError(f"Parámetro no permitido: {key!r}.")
        if key not in allowed:
            raise ForbiddenMongoOperatorError(f"Parámetro no reconocido: {key!r}.")
    return {key: kwargs[key] for key in kwargs}


class TenantScopedRepository:
    """Operaciones MongoDB acotadas; no expone el cliente a capas superiores."""

    def __init__(
        self,
        collection: AsyncCollection,
        context: TenantContext,
        *,
        branch_scoped: bool = False,
    ) -> None:
        self._collection = collection
        self._context = context
        self._branch_scoped = branch_scoped

    @property
    def context(self) -> TenantContext:
        return self._context

    @property
    def branch_scoped(self) -> bool:
        return self._branch_scoped

    def _scoped_filter(self, user_filter: dict[str, Any] | None) -> dict[str, Any]:
        return build_scoped_filter(
            self._context,
            user_filter,
            branch_scoped=self._branch_scoped,
        )

    def _mutation_filter(self, user_filter: dict[str, Any] | None) -> dict[str, Any]:
        return build_mutation_scoped_filter(
            self._context,
            user_filter,
            branch_scoped=self._branch_scoped,
        )

    def _mongo_kwargs(self, allowed: frozenset[str], kwargs: dict[str, Any]) -> dict[str, Any]:
        picked = _pick_allowed_kwargs(allowed, kwargs)
        if "session" in picked:
            ensure_pymongo_session(
                picked["session"],
                expected_client=self._collection.database.client,
                require_in_transaction=True,
            )
        return picked

    async def find_one(
        self,
        user_filter: dict[str, Any] | None = None,
        *,
        projection: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        filter_doc = self._scoped_filter(user_filter)
        extra = self._mongo_kwargs(_KWARGS_FIND_ONE, kwargs)
        return await self._collection.find_one(filter_doc, projection, **extra)

    async def find_one_by_branch_id(
        self,
        branch_id: str,
        *,
        projection: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Lookup por branch_id validado; no expone filtro branch_id genérico al caller."""
        filter_doc = build_trusted_branch_id_read_filter(
            self._context,
            branch_id,
            branch_scoped=self._branch_scoped,
        )
        extra = self._mongo_kwargs(_KWARGS_FIND_ONE, kwargs)
        return await self._collection.find_one(filter_doc, projection, **extra)

    def find(self, user_filter: dict[str, Any] | None = None, **kwargs: Any):
        filter_doc = self._scoped_filter(user_filter)
        extra = self._mongo_kwargs(_KWARGS_FIND, kwargs)
        return self._collection.find(filter_doc, **extra)

    async def count_documents(
        self,
        user_filter: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> int:
        filter_doc = self._scoped_filter(user_filter)
        extra = self._mongo_kwargs(_KWARGS_COUNT, kwargs)
        return await self._collection.count_documents(filter_doc, **extra)

    async def insert_one(self, document: dict[str, Any], **kwargs: Any):
        doc = prepare_insert_document(
            document,
            self._context,
            branch_scoped=self._branch_scoped,
        )
        extra = self._mongo_kwargs(_KWARGS_INSERT, kwargs)
        return await self._collection.insert_one(doc, **extra)

    async def insert_many(self, documents: list[dict[str, Any]], **kwargs: Any):
        docs = prepare_insert_many(
            documents,
            self._context,
            branch_scoped=self._branch_scoped,
        )
        extra = self._mongo_kwargs(_KWARGS_INSERT, kwargs)
        return await self._collection.insert_many(docs, **extra)

    async def update_one(
        self,
        user_filter: dict[str, Any] | None,
        update: dict[str, Any],
        **kwargs: Any,
    ):
        filter_doc = self._mutation_filter(user_filter)
        update_doc = sanitize_update(update, branch_scoped=self._branch_scoped)
        extra = self._mongo_kwargs(_KWARGS_WRITE, kwargs)
        return await self._collection.update_one(filter_doc, update_doc, **extra)

    async def update_one_by_branch_id(
        self,
        branch_id: str,
        update: dict[str, Any],
        **kwargs: Any,
    ):
        """Actualización por branch_id validado (capa repositorio)."""
        filter_doc = build_trusted_branch_id_mutation_filter(
            self._context,
            branch_id,
            branch_scoped=self._branch_scoped,
        )
        update_doc = sanitize_update(update, branch_scoped=self._branch_scoped)
        extra = self._mongo_kwargs(_KWARGS_WRITE, kwargs)
        return await self._collection.update_one(filter_doc, update_doc, **extra)

    async def update_many(
        self,
        user_filter: dict[str, Any] | None,
        update: dict[str, Any],
        **kwargs: Any,
    ):
        filter_doc = self._mutation_filter(user_filter)
        update_doc = sanitize_update(update, branch_scoped=self._branch_scoped)
        extra = self._mongo_kwargs(_KWARGS_WRITE, kwargs)
        return await self._collection.update_many(filter_doc, update_doc, **extra)

    async def delete_one(self, user_filter: dict[str, Any] | None = None, **kwargs: Any):
        filter_doc = self._mutation_filter(user_filter)
        extra = self._mongo_kwargs(_KWARGS_WRITE, kwargs)
        return await self._collection.delete_one(filter_doc, **extra)

    async def delete_many(self, user_filter: dict[str, Any] | None = None, **kwargs: Any):
        filter_doc = self._mutation_filter(user_filter)
        extra = self._mongo_kwargs(_KWARGS_WRITE, kwargs)
        return await self._collection.delete_many(filter_doc, **extra)

    async def aggregate(
        self,
        stages: list[dict[str, Any]],
        **kwargs: Any,
    ):
        pipeline = build_aggregation_pipeline(
            self._context,
            stages,
            branch_scoped=self._branch_scoped,
        )
        extra = self._mongo_kwargs(_KWARGS_AGGREGATE, kwargs)
        return await self._collection.aggregate(pipeline, **extra)
