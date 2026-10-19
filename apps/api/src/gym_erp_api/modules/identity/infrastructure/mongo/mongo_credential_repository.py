"""Repositorio MongoDB de credenciales (gym_platform)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import DuplicateKeyError, OperationFailure, PyMongoError

from gym_erp_api.infrastructure.mongo.session_support import session_mongo_kwargs
from gym_erp_api.modules.identity.domain.errors import (
    CredentialDuplicateUserError,
    CredentialNotFoundError,
    CredentialUpdateConflictError,
    IdentityStorageError,
)
from gym_erp_api.modules.identity.domain.user_credential import UserCredential
from gym_erp_api.modules.identity.domain.validators import require_user_uuid_v4
from gym_erp_api.modules.identity.infrastructure.mongo.credential_document_mapper import (
    credential_from_document,
    credential_to_document,
)


class MongoCredentialRepository:
    """Acceso a ``user_credentials`` en gym_platform."""

    def __init__(self, collection: AsyncCollection) -> None:
        self._collection = collection

    def _session_kw(self, session: object | None) -> dict[str, Any]:
        return session_mongo_kwargs(
            session,
            expected_client=self._collection.database.client,
        )

    async def get_by_user_id(
        self,
        user_id: str,
        *,
        session: object | None = None,
    ) -> UserCredential | None:
        uid = require_user_uuid_v4(user_id)
        raw = await self._collection.find_one({"_id": uid}, **self._session_kw(session))
        if raw is None:
            return None
        return credential_from_document(raw)

    async def insert(
        self,
        credential: UserCredential,
        *,
        session: object | None = None,
    ) -> None:
        doc = credential_to_document(credential)
        try:
            await self._collection.insert_one(doc, **self._session_kw(session))
        except DuplicateKeyError as exc:
            raise CredentialDuplicateUserError("Credencial duplicada para user_id.") from exc
        except OperationFailure as exc:
            raise IdentityStorageError("No se pudo persistir credencial.") from exc
        except PyMongoError as exc:
            raise IdentityStorageError("No se pudo persistir credencial.") from exc

    async def save(
        self,
        credential: UserCredential,
        *,
        expected_updated_at: datetime,
        session: object | None = None,
    ) -> None:
        uid = require_user_uuid_v4(credential.user_id)
        doc = credential_to_document(credential)
        update_fields = {key: value for key, value in doc.items() if key != "_id"}
        try:
            result = await self._collection.update_one(
                {"_id": uid, "updated_at": expected_updated_at},
                {"$set": update_fields},
                **self._session_kw(session),
            )
            if result.matched_count == 0:
                existing = await self.get_by_user_id(uid, session=session)
                if existing is None:
                    raise CredentialNotFoundError(f"Credencial no encontrada: {uid}.")
                raise CredentialUpdateConflictError("Conflicto al actualizar credencial.")
        except (
            CredentialNotFoundError,
            CredentialUpdateConflictError,
            CredentialDuplicateUserError,
        ):
            raise
        except OperationFailure as exc:
            raise IdentityStorageError("No se pudo persistir credencial.") from exc
        except PyMongoError as exc:
            raise IdentityStorageError("No se pudo persistir credencial.") from exc
