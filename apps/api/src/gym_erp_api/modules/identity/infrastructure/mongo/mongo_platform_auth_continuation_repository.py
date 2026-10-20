from __future__ import annotations

from datetime import datetime
from typing import Any

from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import OperationFailure, PyMongoError

from gym_erp_api.infrastructure.mongo.session_support import session_mongo_kwargs
from gym_erp_api.modules.identity.domain.errors import IdentityStorageError
from gym_erp_api.modules.identity.domain.platform_auth.enums import PlatformAuthContinuationStatus
from gym_erp_api.modules.identity.domain.platform_auth.platform_auth_continuation import (
    PlatformAuthContinuation,
)
from gym_erp_api.modules.identity.domain.validators import require_user_uuid_v4
from gym_erp_api.modules.identity.infrastructure.mongo.platform_auth_continuation_mappers import (
    continuation_from_document,
    continuation_to_document,
)


def _not_consumed_clause() -> dict[str, Any]:
    return {"$or": [{"consumed_at": {"$exists": False}}, {"consumed_at": None}]}


class MongoPlatformAuthContinuationRepository:
    def __init__(self, collection: AsyncCollection) -> None:
        self._collection = collection

    def _kw(self, session: object | None) -> dict[str, Any]:
        return session_mongo_kwargs(session, expected_client=self._collection.database.client)

    async def insert(
        self, continuation: PlatformAuthContinuation, *, session: object | None = None
    ) -> None:
        try:
            await self._collection.insert_one(
                continuation_to_document(continuation),
                **self._kw(session),
            )
        except (OperationFailure, PyMongoError) as exc:
            raise IdentityStorageError("No se pudo persistir continuación de auth.") from exc

    async def get_by_token_hash(
        self, token_hash: str, *, session: object | None = None
    ) -> PlatformAuthContinuation | None:
        raw = await self._collection.find_one({"token_hash": token_hash}, **self._kw(session))
        return continuation_from_document(raw) if raw else None

    async def find_open_for_user(
        self, user_id: str, *, now: datetime, session: object | None = None
    ) -> PlatformAuthContinuation | None:
        uid = require_user_uuid_v4(user_id)
        raw = await self._collection.find_one(
            {
                "user_id": uid,
                "expires_at": {"$gt": now},
                **_not_consumed_clause(),
            },
            **self._kw(session),
        )
        return continuation_from_document(raw) if raw else None

    async def bind_challenge(
        self,
        continuation_id: str,
        *,
        challenge_id: str,
        now: datetime,
        session: object | None = None,
    ) -> PlatformAuthContinuation | None:
        cid = require_user_uuid_v4(continuation_id, "continuation_id")
        ch_id = require_user_uuid_v4(challenge_id, "challenge_id")
        raw = await self._collection.find_one_and_update(
            {
                "_id": cid,
                "status": PlatformAuthContinuationStatus.PASSWORD_VERIFIED.value,
                "expires_at": {"$gt": now},
                **_not_consumed_clause(),
            },
            {
                "$set": {
                    "status": PlatformAuthContinuationStatus.MFA_CHALLENGE_BOUND.value,
                    "challenge_id": ch_id,
                }
            },
            return_document=True,
            **self._kw(session),
        )
        return continuation_from_document(raw) if raw else None

    async def bind_authorization(
        self,
        continuation_id: str,
        *,
        authorization_id: str,
        now: datetime,
        session: object | None = None,
    ) -> PlatformAuthContinuation | None:
        cid = require_user_uuid_v4(continuation_id, "continuation_id")
        aid = require_user_uuid_v4(authorization_id, "authorization_id")
        raw = await self._collection.find_one_and_update(
            {
                "_id": cid,
                "status": PlatformAuthContinuationStatus.MFA_CHALLENGE_BOUND.value,
                "expires_at": {"$gt": now},
                **_not_consumed_clause(),
            },
            {
                "$set": {
                    "status": PlatformAuthContinuationStatus.MFA_AUTHORIZED.value,
                    "authorization_id": aid,
                }
            },
            return_document=True,
            **self._kw(session),
        )
        return continuation_from_document(raw) if raw else None

    async def consume_if_authorized(
        self,
        continuation_id: str,
        *,
        user_id: str,
        credential_version: int,
        now: datetime,
        session: object | None = None,
    ) -> PlatformAuthContinuation | None:
        cid = require_user_uuid_v4(continuation_id, "continuation_id")
        uid = require_user_uuid_v4(user_id)
        raw = await self._collection.find_one_and_update(
            {
                "_id": cid,
                "user_id": uid,
                "credential_version": credential_version,
                "status": PlatformAuthContinuationStatus.MFA_AUTHORIZED.value,
                "expires_at": {"$gt": now},
                **_not_consumed_clause(),
            },
            {"$set": {"consumed_at": now}},
            return_document=True,
            **self._kw(session),
        )
        return continuation_from_document(raw) if raw else None
