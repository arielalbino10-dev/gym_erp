"""Repositorio MongoDB de UserIdentity (gym_platform)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import DuplicateKeyError, OperationFailure, PyMongoError

from gym_erp_api.infrastructure.mongo.session_support import session_mongo_kwargs
from gym_erp_api.modules.identity.domain.errors import (
    IdentityDuplicateEmailError,
    IdentityDuplicateUserError,
    IdentityNotFoundError,
    IdentityStorageError,
    IdentityUpdateConflictError,
)
from gym_erp_api.modules.identity.domain.user_identity import UserIdentity
from gym_erp_api.modules.identity.domain.validators import require_user_uuid_v4
from gym_erp_api.modules.identity.infrastructure.mongo.identity_document_mapper import (
    identity_from_document,
    identity_to_document,
)
from gym_erp_api.modules.identity.infrastructure.mongo.platform_index_specs import (
    duplicate_key_field,
)


class MongoIdentityRepository:
    """Acceso a ``user_identities`` en gym_platform."""

    def __init__(self, collection: AsyncCollection) -> None:
        self._collection = collection

    def _session_kw(self, session: object | None) -> dict[str, Any]:
        return session_mongo_kwargs(
            session,
            expected_client=self._collection.database.client,
        )

    async def get_by_email_normalized(
        self,
        email_normalized: str,
        *,
        session: object | None = None,
    ) -> UserIdentity | None:
        normalized = email_normalized.strip().lower()
        if not normalized:
            return None
        raw = await self._collection.find_one(
            {"email_normalized": normalized},
            **self._session_kw(session),
        )
        if raw is None:
            return None
        return identity_from_document(raw)

    async def get_by_id(
        self,
        user_id: str,
        *,
        session: object | None = None,
    ) -> UserIdentity | None:
        uid = require_user_uuid_v4(user_id)
        raw = await self._collection.find_one({"_id": uid}, **self._session_kw(session))
        if raw is None:
            return None
        return identity_from_document(raw)

    async def save(
        self,
        identity: UserIdentity,
        *,
        expected_updated_at: datetime | None = None,
        session: object | None = None,
    ) -> None:
        uid = require_user_uuid_v4(identity.user_id)
        doc = identity_to_document(identity)
        kwargs = self._session_kw(session)
        try:
            if expected_updated_at is None:
                await self._collection.insert_one(doc, **kwargs)
                return
            update_fields = {key: value for key, value in doc.items() if key != "_id"}
            result = await self._collection.update_one(
                {"_id": uid, "updated_at": expected_updated_at},
                {"$set": update_fields},
                **kwargs,
            )
            if result.matched_count == 0:
                existing = await self.get_by_id(uid, session=session)
                if existing is None:
                    raise IdentityNotFoundError(f"Identidad no encontrada: {uid}.")
                raise IdentityUpdateConflictError("Conflicto al actualizar identidad.")
        except DuplicateKeyError as exc:
            field = duplicate_key_field(exc)
            if field == "email_normalized":
                raise IdentityDuplicateEmailError("email_normalized duplicado.") from None
            if field == "_id":
                raise IdentityDuplicateUserError("user_id duplicado.") from None
            raise IdentityDuplicateEmailError("Identidad duplicada.") from None
        except (IdentityNotFoundError, IdentityUpdateConflictError, IdentityDuplicateEmailError):
            raise
        except OperationFailure as exc:
            raise IdentityStorageError("No se pudo persistir identidad.") from exc
        except PyMongoError as exc:
            raise IdentityStorageError("No se pudo persistir identidad.") from exc
