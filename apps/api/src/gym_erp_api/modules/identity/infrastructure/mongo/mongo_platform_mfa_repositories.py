"""Repositorios MongoDB MFA platform (gym_platform)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import DuplicateKeyError, OperationFailure, PyMongoError

from gym_erp_api.infrastructure.mongo.session_support import session_mongo_kwargs
from gym_erp_api.modules.identity.domain.errors import IdentityStorageError
from gym_erp_api.modules.identity.domain.platform_mfa.platform_mfa_challenge import (
    PlatformMfaChallenge,
)
from gym_erp_api.modules.identity.domain.platform_mfa.platform_mfa_session_authorization import (
    PlatformMfaSessionAuthorization,
)
from gym_erp_api.modules.identity.domain.platform_mfa.platform_totp_enrollment import (
    PlatformTotpEnrollment,
)
from gym_erp_api.modules.identity.domain.validators import require_user_uuid_v4
from gym_erp_api.modules.identity.infrastructure.mongo.platform_mfa_mappers import (
    authorization_to_document,
    challenge_from_document,
    challenge_to_document,
    enrollment_from_document,
    enrollment_to_document,
)


def _not_consumed_clause() -> dict[str, Any]:
    return {"$or": [{"consumed_at": {"$exists": False}}, {"consumed_at": None}]}


class MongoPlatformTotpEnrollmentRepository:
    def __init__(self, collection: AsyncCollection) -> None:
        self._collection = collection

    def _kw(self, session: object | None) -> dict[str, Any]:
        return session_mongo_kwargs(session, expected_client=self._collection.database.client)

    async def get_by_user_id(
        self, user_id: str, *, session: object | None = None
    ) -> PlatformTotpEnrollment | None:
        uid = require_user_uuid_v4(user_id)
        raw = await self._collection.find_one({"_id": uid}, **self._kw(session))
        return enrollment_from_document(raw) if raw else None

    async def save(
        self, enrollment: PlatformTotpEnrollment, *, session: object | None = None
    ) -> None:
        doc = enrollment_to_document(enrollment)
        try:
            await self._collection.replace_one(
                {"_id": enrollment.user_id},
                doc,
                upsert=True,
                **self._kw(session),
            )
        except (OperationFailure, PyMongoError) as exc:
            raise IdentityStorageError("No se pudo persistir enrolamiento MFA.") from exc


class MongoPlatformMfaChallengeRepository:
    def __init__(self, collection: AsyncCollection) -> None:
        self._collection = collection

    def _kw(self, session: object | None) -> dict[str, Any]:
        return session_mongo_kwargs(session, expected_client=self._collection.database.client)

    async def insert(
        self, challenge: PlatformMfaChallenge, *, session: object | None = None
    ) -> None:
        try:
            await self._collection.insert_one(challenge_to_document(challenge), **self._kw(session))
        except (OperationFailure, PyMongoError) as exc:
            raise IdentityStorageError("No se pudo crear desafío MFA.") from exc

    async def get_by_id(
        self, challenge_id: str, *, session: object | None = None
    ) -> PlatformMfaChallenge | None:
        cid = require_user_uuid_v4(challenge_id, "challenge_id")
        raw = await self._collection.find_one({"_id": cid}, **self._kw(session))
        return challenge_from_document(raw) if raw else None

    async def find_open_for_user(
        self, user_id: str, *, now: datetime, session: object | None = None
    ) -> PlatformMfaChallenge | None:
        uid = require_user_uuid_v4(user_id)
        raw = await self._collection.find_one(
            {
                "user_id": uid,
                "expires_at": {"$gt": now},
                **_not_consumed_clause(),
            },
            **self._kw(session),
        )
        return challenge_from_document(raw) if raw else None

    async def reserve_verification_attempt(
        self,
        challenge_id: str,
        *,
        user_id: str,
        now: datetime,
        session: object | None = None,
    ) -> bool:
        cid = require_user_uuid_v4(challenge_id, "challenge_id")
        uid = require_user_uuid_v4(user_id)
        raw = await self._collection.find_one_and_update(
            {
                "_id": cid,
                "user_id": uid,
                "expires_at": {"$gt": now},
                "$expr": {"$lt": ["$failed_attempts", "$max_attempts"]},
                **_not_consumed_clause(),
            },
            {"$inc": {"failed_attempts": 1}},
            **self._kw(session),
        )
        return raw is not None

    async def consume_if_valid(
        self,
        challenge_id: str,
        *,
        user_id: str,
        now: datetime,
        session: object | None = None,
    ) -> PlatformMfaChallenge | None:
        cid = require_user_uuid_v4(challenge_id, "challenge_id")
        uid = require_user_uuid_v4(user_id)
        raw = await self._collection.find_one_and_update(
            {
                "_id": cid,
                "user_id": uid,
                "expires_at": {"$gt": now},
                **_not_consumed_clause(),
            },
            {"$set": {"consumed_at": now}},
            return_document=True,
            **self._kw(session),
        )
        return challenge_from_document(raw) if raw else None


class MongoPlatformMfaStepConsumptionRepository:
    def __init__(self, collection: AsyncCollection) -> None:
        self._collection = collection

    def _kw(self, session: object | None) -> dict[str, Any]:
        return session_mongo_kwargs(session, expected_client=self._collection.database.client)

    async def try_register_step(
        self,
        *,
        user_id: str,
        time_counter: int,
        expires_at: datetime,
        session: object | None = None,
    ) -> bool:
        uid = require_user_uuid_v4(user_id)
        doc_id = f"{uid}:{time_counter}"
        try:
            await self._collection.insert_one(
                {
                    "_id": doc_id,
                    "user_id": uid,
                    "time_counter": time_counter,
                    "expires_at": expires_at,
                },
                **self._kw(session),
            )
            return True
        except DuplicateKeyError:
            return False
        except (OperationFailure, PyMongoError) as exc:
            raise IdentityStorageError("No se pudo registrar paso TOTP.") from exc


class MongoPlatformMfaSessionAuthorizationRepository:
    def __init__(self, collection: AsyncCollection) -> None:
        self._collection = collection

    def _kw(self, session: object | None) -> dict[str, Any]:
        return session_mongo_kwargs(session, expected_client=self._collection.database.client)

    async def insert(
        self,
        authorization: PlatformMfaSessionAuthorization,
        *,
        session: object | None = None,
    ) -> None:
        try:
            await self._collection.insert_one(
                authorization_to_document(authorization),
                **self._kw(session),
            )
        except (OperationFailure, PyMongoError) as exc:
            raise IdentityStorageError("No se pudo persistir autorización MFA.") from exc

    async def consume_for_session(
        self,
        authorization_id: str,
        *,
        user_id: str,
        credential_version: int,
        now: datetime,
        session: object | None = None,
    ) -> bool:
        aid = require_user_uuid_v4(authorization_id, "authorization_id")
        uid = require_user_uuid_v4(user_id)
        raw = await self._collection.find_one_and_update(
            {
                "_id": aid,
                "user_id": uid,
                "credential_version": credential_version,
                "expires_at": {"$gt": now},
                **_not_consumed_clause(),
            },
            {"$set": {"consumed_at": now}},
            **self._kw(session),
        )
        return raw is not None
