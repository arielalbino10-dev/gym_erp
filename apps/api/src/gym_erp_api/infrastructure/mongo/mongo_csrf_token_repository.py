"""Tokens CSRF server-side (hash, binding, TTL)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import OperationFailure, PyMongoError

from gym_erp_api.infrastructure.mongo.session_support import session_mongo_kwargs
from gym_erp_api.presentation.http_security.errors import RateLimitBackendError

HTTP_CSRF_TOKENS_COLLECTION = "http_csrf_tokens"


class MongoCsrfTokenRepository:
    def __init__(self, collection: AsyncCollection) -> None:
        self._collection = collection

    def _kw(self, session: object | None) -> dict[str, Any]:
        return session_mongo_kwargs(session, expected_client=self._collection.database.client)

    async def store(
        self,
        *,
        token_hash: str,
        binding_key: str,
        expires_at: datetime,
        session: object | None = None,
    ) -> None:
        try:
            await self._collection.replace_one(
                {"_id": token_hash},
                {
                    "_id": token_hash,
                    "binding_key": binding_key,
                    "expires_at": expires_at,
                },
                upsert=True,
                **self._kw(session),
            )
        except (OperationFailure, PyMongoError) as exc:
            raise RateLimitBackendError("CSRF storage failure.") from exc

    async def consume_if_valid(
        self,
        *,
        token_hash: str,
        binding_key: str,
        now: datetime,
        session: object | None = None,
    ) -> bool:
        try:
            raw = await self._collection.find_one_and_delete(
                {
                    "_id": token_hash,
                    "binding_key": binding_key,
                    "expires_at": {"$gt": now},
                },
                **self._kw(session),
            )
            return raw is not None
        except (OperationFailure, PyMongoError) as exc:
            raise RateLimitBackendError("CSRF storage failure.") from exc
