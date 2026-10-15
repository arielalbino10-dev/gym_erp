"""Adaptador MongoDB IdempotencyStore (solo platform, operación create_organization).

Visibilidad transaccional
-------------------------
Un ``pending`` insertado en una transacción **no** es visible a otras sesiones hasta
commit. Tras ``DuplicateKeyError`` en ``reserve``, si ``find`` no devuelve documento,
no implica que la otra operación terminó: puede estar pending sin confirmar.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import DuplicateKeyError, OperationFailure

from gym_erp_api.infrastructure.mongo.session_support import (
    ensure_pymongo_session,
    session_mongo_kwargs,
)
from gym_erp_api.infrastructure.mongo.uow_errors import InvalidMongoSessionError
from gym_erp_api.modules.organization.application.commands.create_organization import (
    CreateOrganizationResult,
)
from gym_erp_api.modules.organization.application.errors import (
    IdempotencyAlreadyCompletedError,
    IdempotencyInProgressError,
    IdempotencyPayloadConflictError,
    IdempotencyReservationMissingError,
)
from gym_erp_api.modules.organization.application.ports.idempotency_store import (
    IdempotencyRecord,
    IdempotencyRecordStatus,
    IdempotencyReservation,
)
from gym_erp_api.modules.organization.infrastructure.mongo.idempotency_document_mapper import (
    build_idempotency_document_id,
    completed_update_fields,
    idempotency_from_document,
    reservation_to_insert_document,
)


class PlatformIdempotencyRepository:
    """Persistencia de idempotencia en ``gym_platform`` (sin acceso operational)."""

    def __init__(self, collection: AsyncCollection) -> None:
        self._collection = collection

    async def find_by_operation_and_key(
        self,
        operation: str,
        idempotency_key: str,
        *,
        session: object | None = None,
    ) -> IdempotencyRecord | None:
        doc_id = build_idempotency_document_id(operation, idempotency_key)
        kwargs = session_mongo_kwargs(
            session,
            expected_client=self._collection.database.client,
            require_in_transaction=False,
        )
        raw = await self._collection.find_one({"_id": doc_id}, **kwargs)
        return idempotency_from_document(raw)

    async def reserve(
        self,
        reservation: IdempotencyReservation,
        *,
        session: object,
    ) -> None:
        pymongo_session = self._require_write_session(session)
        doc = reservation_to_insert_document(reservation, now=datetime.now(UTC))
        try:
            await self._collection.insert_one(doc, session=pymongo_session)
        except DuplicateKeyError as exc:
            await self._handle_reserve_duplicate(reservation, cause=exc)
        except OperationFailure as exc:
            if exc.has_error_label("TransientTransactionError"):
                raise IdempotencyInProgressError(
                    "Conflicto transaccional al reservar; otra transacción usa la clave."
                ) from exc
            raise

    async def mark_completed(
        self,
        operation: str,
        idempotency_key: str,
        *,
        result: CreateOrganizationResult,
        session: object,
    ) -> None:
        pymongo_session = self._require_write_session(session)
        doc_id = build_idempotency_document_id(operation, idempotency_key)
        update_fields = completed_update_fields(result, now=datetime.now(UTC))
        filter_doc = {
            "_id": doc_id,
            "status": IdempotencyRecordStatus.PENDING.value,
            "tenant_id": result.tenant_id,
            "branch_id": result.branch_id,
        }
        write_result = await self._collection.update_one(
            filter_doc,
            {"$set": update_fields},
            session=pymongo_session,
        )
        if write_result.matched_count == 1:
            return
        existing = await self.find_by_operation_and_key(
            operation,
            idempotency_key,
            session=pymongo_session,
        )
        if existing is None:
            raise IdempotencyReservationMissingError(
                "No hay reserva pending para completar (o no visible en esta sesión)."
            )
        if existing.status == IdempotencyRecordStatus.COMPLETED:
            raise IdempotencyAlreadyCompletedError("La idempotencia ya está completed.")
        raise IdempotencyReservationMissingError("No se pudo transicionar pending→completed.")

    def _require_write_session(self, session: object) -> Any:
        validated = ensure_pymongo_session(
            session,
            expected_client=self._collection.database.client,
            require_in_transaction=True,
        )
        if validated is None:
            raise InvalidMongoSessionError("session obligatoria para escrituras de idempotencia.")
        return validated

    async def _handle_reserve_duplicate(
        self,
        reservation: IdempotencyReservation,
        *,
        cause: DuplicateKeyError,
    ) -> None:
        existing = await self.find_by_operation_and_key(
            reservation.operation,
            reservation.idempotency_key,
        )
        if existing is None:
            raise IdempotencyInProgressError(
                "Colisión de clave: otra transacción reservó la clave y aún no hizo commit. "
                "No implica que el alta haya finalizado."
            ) from cause
        if existing.request_fingerprint != reservation.request_fingerprint:
            raise IdempotencyPayloadConflictError(
                "La clave de idempotencia ya existe con datos de negocio distintos."
            ) from cause
        if existing.status == IdempotencyRecordStatus.COMPLETED:
            raise IdempotencyAlreadyCompletedError(
                "La operación idempotente ya fue completada."
            ) from cause
        if existing.status == IdempotencyRecordStatus.FAILED:
            raise IdempotencyPayloadConflictError(
                "La clave de idempotencia está en estado failed."
            ) from cause
        raise IdempotencyInProgressError("Reserva pending existente para esta clave.") from cause
