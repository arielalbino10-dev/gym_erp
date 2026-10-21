"""Repositorio MongoDB de sesiones opacas (gym_platform)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import DuplicateKeyError, OperationFailure, PyMongoError

from gym_erp_api.infrastructure.mongo.session_support import session_mongo_kwargs
from gym_erp_api.modules.identity.domain.auth_session import AuthSession
from gym_erp_api.modules.identity.domain.errors import (
    IdentityStorageError,
    SessionNotFoundError,
    SessionUpdateConflictError,
)
from gym_erp_api.modules.identity.domain.session_kind import SessionKind
from gym_erp_api.modules.identity.domain.validators import require_user_uuid_v4
from gym_erp_api.modules.identity.infrastructure.mongo.auth_session_document_mapper import (
    auth_session_from_document,
    auth_session_to_document,
)


def _session_not_revoked_clause() -> dict[str, Any]:
    return {"$or": [{"revoked_at": {"$exists": False}}, {"revoked_at": None}]}


class MongoAuthSessionRepository:
    """Acceso a ``auth_sessions`` en gym_platform."""

    def __init__(self, collection: AsyncCollection) -> None:
        self._collection = collection

    def _session_kw(self, session: object | None) -> dict[str, Any]:
        return session_mongo_kwargs(
            session,
            expected_client=self._collection.database.client,
        )

    async def insert(
        self,
        auth_session: AuthSession,
        *,
        session: object | None = None,
    ) -> None:
        doc = auth_session_to_document(auth_session)
        try:
            await self._collection.insert_one(doc, **self._session_kw(session))
        except DuplicateKeyError as exc:
            raise IdentityStorageError("No se pudo crear sesión.") from exc
        except OperationFailure as exc:
            raise IdentityStorageError("No se pudo crear sesión.") from exc
        except PyMongoError as exc:
            raise IdentityStorageError("No se pudo crear sesión.") from exc

    async def get_by_id(
        self,
        session_id: str,
        *,
        session: object | None = None,
    ) -> AuthSession | None:
        sid = require_user_uuid_v4(session_id, "session_id")
        raw = await self._collection.find_one({"_id": sid}, **self._session_kw(session))
        if raw is None:
            return None
        return auth_session_from_document(raw)

    async def get_by_token_hash(
        self,
        token_hash: str,
        *,
        session: object | None = None,
    ) -> AuthSession | None:
        if not isinstance(token_hash, str) or len(token_hash) != 64:
            return None
        raw = await self._collection.find_one(
            {"token_hash": token_hash},
            **self._session_kw(session),
        )
        if raw is None:
            return None
        return auth_session_from_document(raw)

    async def save_revoked(
        self,
        auth_session: AuthSession,
        *,
        session: object | None = None,
    ) -> None:
        if auth_session.revoked_at is None:
            raise SessionNotFoundError("Sesión sin revocación para persistir.")
        sid = require_user_uuid_v4(auth_session.session_id, "session_id")
        try:
            result = await self._collection.update_one(
                {"$and": [{"_id": sid}, _session_not_revoked_clause()]},
                {
                    "$set": {
                        "revoked_at": auth_session.revoked_at,
                        "revocation_reason": auth_session.revocation_reason,
                    }
                },
                **self._session_kw(session),
            )
            if result.matched_count == 0:
                raise SessionNotFoundError("Sesión no encontrada o ya revocada.")
        except SessionNotFoundError:
            raise
        except OperationFailure as exc:
            raise IdentityStorageError("No se pudo revocar sesión.") from exc
        except PyMongoError as exc:
            raise IdentityStorageError("No se pudo revocar sesión.") from exc

    async def revoke_all_for_user(
        self,
        user_id: str,
        *,
        session_kind: SessionKind | None = None,
        reason: str,
        revoked_at: datetime,
        session: object | None = None,
    ) -> int:
        uid = require_user_uuid_v4(user_id)
        cleaned = reason.strip()
        if not cleaned:
            raise ValueError("Motivo de revocación requerido.")
        filt: dict[str, Any] = {
            "$and": [
                {"user_id": uid},
                _session_not_revoked_clause(),
            ]
        }
        if session_kind is not None:
            filt["$and"].append({"session_kind": SessionKind(session_kind).value})
        try:
            result = await self._collection.update_many(
                filt,
                {"$set": {"revoked_at": revoked_at, "revocation_reason": cleaned}},
                **self._session_kw(session),
            )
            return int(result.modified_count)
        except OperationFailure as exc:
            raise IdentityStorageError("No se pudo revocar sesiones.") from exc
        except PyMongoError as exc:
            raise IdentityStorageError("No se pudo revocar sesiones.") from exc

    async def touch_activity(
        self,
        auth_session: AuthSession,
        *,
        expected_last_seen_at: datetime,
        session: object | None = None,
    ) -> AuthSession:
        sid = require_user_uuid_v4(auth_session.session_id, "session_id")
        try:
            result = await self._collection.update_one(
                {
                    "$and": [
                        {"_id": sid},
                        {"last_seen_at": expected_last_seen_at},
                        _session_not_revoked_clause(),
                    ]
                },
                {
                    "$set": {
                        "last_seen_at": auth_session.last_seen_at,
                        "idle_expires_at": auth_session.idle_expires_at,
                    }
                },
                **self._session_kw(session),
            )
            if result.matched_count == 0:
                raise SessionUpdateConflictError("Conflicto al actualizar actividad de sesión.")
        except SessionUpdateConflictError:
            raise
        except OperationFailure as exc:
            raise IdentityStorageError("No se pudo actualizar sesión.") from exc
        except PyMongoError as exc:
            raise IdentityStorageError("No se pudo actualizar sesión.") from exc
        restored = await self.get_by_id(sid, session=session)
        if restored is None:
            raise SessionNotFoundError("Sesión no encontrada tras actualización.")
        return restored

    async def update_gym_tenant_selection(
        self,
        auth_session: AuthSession,
        *,
        expected_last_seen_at: datetime,
        session: object | None = None,
    ) -> AuthSession:
        sid = require_user_uuid_v4(auth_session.session_id, "session_id")
        update_fields: dict[str, Any] = {
            "last_seen_at": auth_session.last_seen_at,
        }
        if auth_session.active_tenant_id is not None:
            update_fields["active_tenant_id"] = auth_session.active_tenant_id
        else:
            update_fields["active_tenant_id"] = None
        if auth_session.gym_membership_authz_epoch is not None:
            update_fields["gym_membership_authz_epoch"] = auth_session.gym_membership_authz_epoch
        else:
            update_fields["gym_membership_authz_epoch"] = None
        try:
            result = await self._collection.update_one(
                {
                    "$and": [
                        {"_id": sid},
                        {"session_kind": SessionKind.GYM.value},
                        {"last_seen_at": expected_last_seen_at},
                        _session_not_revoked_clause(),
                    ]
                },
                {"$set": update_fields},
                **self._session_kw(session),
            )
            if result.matched_count == 0:
                raise SessionUpdateConflictError("Conflicto al seleccionar tenant gym.")
        except SessionUpdateConflictError:
            raise
        except OperationFailure as exc:
            raise IdentityStorageError("No se pudo actualizar sesión.") from exc
        except PyMongoError as exc:
            raise IdentityStorageError("No se pudo actualizar sesión.") from exc
        restored = await self.get_by_id(sid, session=session)
        if restored is None:
            raise SessionNotFoundError("Sesión no encontrada tras selección de tenant.")
        return restored
