"""Validación de sesiones PyMongo Async para repositorios."""

from __future__ import annotations

from typing import Any

from pymongo.asynchronous.client_session import AsyncClientSession

from gym_erp_api.infrastructure.mongo.uow_errors import InvalidMongoSessionError


def ensure_pymongo_session(
    session: object | None,
    *,
    expected_client: Any | None = None,
    require_in_transaction: bool = False,
) -> AsyncClientSession | None:
    """Acepta None o una AsyncClientSession vinculada al cliente del repositorio."""
    if session is None:
        return None
    if not isinstance(session, AsyncClientSession):
        raise InvalidMongoSessionError(
            "session debe ser pymongo.asynchronous.client_session.AsyncClientSession o None."
        )
    if session.has_ended:
        raise InvalidMongoSessionError("session finalizada.")
    if require_in_transaction and not session.in_transaction:
        raise InvalidMongoSessionError("session sin transacción activa.")
    if expected_client is not None and session.client is not expected_client:
        raise InvalidMongoSessionError("session no pertenece al AsyncMongoClient del repositorio.")
    return session


def session_mongo_kwargs(
    session: object | None,
    *,
    expected_client: Any | None = None,
    require_in_transaction: bool = True,
) -> dict[str, AsyncClientSession]:
    validated = ensure_pymongo_session(
        session,
        expected_client=expected_client,
        require_in_transaction=require_in_transaction,
    )
    if validated is None:
        return {}
    return {"session": validated}
