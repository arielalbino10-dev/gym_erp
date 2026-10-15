"""Unit of Work MongoDB sobre un único AsyncMongoClient (PyMongo 4.x async).

Patrón de transacción (réplica set / sharded >= 4.2)::

    async with client.start_session() as session:
        async with await session.start_transaction():
            await collection.insert_one(doc, session=session)

``MongoUnitOfWork`` encapsula sesión + transacción y expone ``session`` para repositorios.

Límites de tiempo
-----------------
``max_commit_time_ms`` se pasa a ``start_transaction`` como límite del comando
``commitTransaction`` en el servidor (``maxCommitTimeMS``). No acota la duración
total del bloque de negocio ni el tiempo de operaciones CRUD previas al commit.

Errores MongoDB (tratamiento posterior, sin reintento automático aquí)
----------------------------------------------------------------------
* **TransientTransactionError** (etiqueta en ``OperationFailure`` / ``ConnectionFailure``):
  la transacción no pudo completarse de forma transitoria; el callback de negocio puede
  reintentarse en un **nuevo** Unit of Work (H1-D.3.3+). Este UoW no reejecuta el bloque.

* **UnknownTransactionCommitResult**: el commit pudo aplicarse o no. Se traduce a
  ``MongoTransactionCommitUncertainError``. No afirmar rollback; reconciliar en capa
  de aplicación cuando exista idempotencia.

* Abort ante excepción en el cuerpo: PyMongo invoca ``abort_transaction`` al salir del
  contexto de transacción con error; errores de abort se ignoran en el driver. Eso no
  garantiza al 100 % estado en red caída, pero es el contrato del driver.

* No usar ``session.with_transaction`` aquí: reintenta callback y commit, contrario al
  alcance H1-D.3.2.
"""

from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING, Any

from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo.errors import PyMongoError

from gym_erp_api.infrastructure.mongo.mongo_databases import MongoDatabases
from gym_erp_api.infrastructure.mongo.uow_errors import (
    MongoTransactionCommitUncertainError,
    MongoUnitOfWorkInactiveError,
)

if TYPE_CHECKING:
    from pymongo.asynchronous.mongo_client import AsyncMongoClient

DEFAULT_MAX_COMMIT_TIME_MS = 30_000

_UNCERTAIN_COMMIT_LABEL = "UnknownTransactionCommitResult"


class MongoUnitOfWork:
    """Sesión y transacción exclusivas por instancia; no concurrentes ni reutilizables."""

    def __init__(
        self,
        databases: MongoDatabases,
        *,
        max_commit_time_ms: int = DEFAULT_MAX_COMMIT_TIME_MS,
    ) -> None:
        self._client: AsyncMongoClient[Any] = databases.client
        self._max_commit_time_ms = max_commit_time_ms
        self._session: AsyncClientSession | None = None
        self._session_cm: Any = None
        self._transaction_cm: Any = None
        self._active = False
        self._consumed = False
        if max_commit_time_ms <= 0:
            raise ValueError("max_commit_time_ms debe ser positivo.")

    @property
    def session(self) -> AsyncClientSession:
        if not self._active or self._session is None:
            raise MongoUnitOfWorkInactiveError(
                "La sesión solo está disponible dentro de 'async with MongoUnitOfWork(...)'."
            )
        return self._session

    async def __aenter__(self) -> MongoUnitOfWork:
        if self._consumed:
            raise MongoUnitOfWorkInactiveError("MongoUnitOfWork no admite reutilización.")
        self._consumed = True
        self._session_cm = self._client.start_session()
        try:
            self._session = await self._session_cm.__aenter__()
            self._transaction_cm = await self._session.start_transaction(
                max_commit_time_ms=self._max_commit_time_ms,
            )
            await self._transaction_cm.__aenter__()
        except BaseException:
            await self._session_cm.__aexit__(None, None, None)
            self._session_cm = None
            self._session = None
            self._transaction_cm = None
            raise
        self._active = True
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        commit_exc: BaseException | None = None
        try:
            if self._transaction_cm is not None:
                try:
                    await self._transaction_cm.__aexit__(exc_type, exc_val, exc_tb)
                except PyMongoError as error:
                    if exc_type is None and error.has_error_label(_UNCERTAIN_COMMIT_LABEL):
                        commit_exc = MongoTransactionCommitUncertainError(
                            "Commit con resultado desconocido; no asumir rollback ni éxito."
                        )
                        commit_exc.__cause__ = error
                    else:
                        commit_exc = error
        finally:
            self._active = False
            if self._session_cm is not None:
                await self._session_cm.__aexit__(None, None, None)
            self._session = None
            self._session_cm = None
            self._transaction_cm = None
        if commit_exc is not None:
            raise commit_exc
