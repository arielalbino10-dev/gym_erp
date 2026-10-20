"""Contadores de rate limit en gym_platform (compartidos entre workers)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from pymongo import ReturnDocument
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import OperationFailure, PyMongoError

from gym_erp_api.infrastructure.mongo.session_support import session_mongo_kwargs
from gym_erp_api.presentation.http_security.errors import RateLimitBackendError

HTTP_RATE_LIMIT_COLLECTION = "http_rate_limit_counters"


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    """allowed: si este intento puede continuar. El documento Mongo guarda intentos totales."""

    allowed: bool
    retry_after_seconds: int = 0


class MongoRateLimitRepository:
    """Contador atómico por ventana. ``count`` = intentos registrados (incluye rechazados)."""

    def __init__(self, collection: AsyncCollection) -> None:
        self._collection = collection

    def _kw(self, session: object | None) -> dict[str, Any]:
        return session_mongo_kwargs(session, expected_client=self._collection.database.client)

    async def check_and_increment(
        self,
        *,
        bucket: str,
        scope_key: str,
        limit: int,
        window: timedelta,
        now: datetime,
        session: object | None = None,
    ) -> RateLimitDecision:
        if limit < 1:
            return RateLimitDecision(allowed=True)
        doc_id = f"{bucket}:{scope_key}"
        window_start_cutoff = now - window
        ttl_at = now + window + window
        try:
            updated = await self._collection.find_one_and_update(
                {"_id": doc_id},
                [
                    {
                        "$set": {
                            "bucket": bucket,
                            "scope_key": scope_key,
                            "expires_at": ttl_at,
                            "count": {
                                "$cond": [
                                    {
                                        "$or": [
                                            {"$eq": [{"$type": "$window_start"}, "missing"]},
                                            {"$lt": ["$window_start", window_start_cutoff]},
                                        ]
                                    },
                                    1,
                                    {"$add": [{"$ifNull": ["$count", 0]}, 1]},
                                ]
                            },
                            "window_start": {
                                "$cond": [
                                    {
                                        "$or": [
                                            {"$eq": [{"$type": "$window_start"}, "missing"]},
                                            {"$lt": ["$window_start", window_start_cutoff]},
                                        ]
                                    },
                                    now,
                                    "$window_start",
                                ]
                            },
                        }
                    }
                ],
                upsert=True,
                return_document=ReturnDocument.AFTER,
                **self._kw(session),
            )
            if updated is None:
                raise RateLimitBackendError("Rate limit storage failure.")
            count = int(updated.get("count", 0))
            if count > limit:
                ws = updated["window_start"]
                retry = int((ws + window - now).total_seconds())
                return RateLimitDecision(allowed=False, retry_after_seconds=max(1, retry))
            return RateLimitDecision(allowed=True)
        except RateLimitBackendError:
            raise
        except (OperationFailure, PyMongoError) as exc:
            raise RateLimitBackendError("Rate limit storage failure.") from exc
