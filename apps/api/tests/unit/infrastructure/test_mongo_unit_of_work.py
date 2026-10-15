from unittest.mock import AsyncMock, MagicMock

import pytest
from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo.errors import OperationFailure

from gym_erp_api.core.config import Settings
from gym_erp_api.infrastructure.mongo.mongo_databases import MongoDatabases
from gym_erp_api.infrastructure.mongo.mongo_unit_of_work import (
    DEFAULT_MAX_COMMIT_TIME_MS,
    MongoUnitOfWork,
)
from gym_erp_api.infrastructure.mongo.uow_errors import (
    MongoTransactionCommitUncertainError,
    MongoUnitOfWorkInactiveError,
)
from gym_erp_api.modules.organization.application.ports.unit_of_work import OrganizationUnitOfWork


def _make_databases() -> tuple[MongoDatabases, MagicMock]:
    client = MagicMock()
    settings = Settings(
        app_env="test",
        mongodb_uri=None,
        mongodb_platform_db="gym_platform",
        mongodb_operational_db="gym_operational",
    )
    return MongoDatabases(client, settings), client


def _wire_session_context(client: MagicMock, session: MagicMock) -> None:
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    client.start_session.return_value = session_cm


def _wire_transaction_context(session: MagicMock, *, exit_side_effect=None) -> MagicMock:
    tx_cm = MagicMock()
    tx_cm.__aenter__ = AsyncMock(return_value=tx_cm)
    if exit_side_effect is not None:
        tx_cm.__aexit__ = AsyncMock(side_effect=exit_side_effect)
    else:
        tx_cm.__aexit__ = AsyncMock(return_value=None)
    session.start_transaction = AsyncMock(return_value=tx_cm)
    return tx_cm


@pytest.mark.asyncio
async def test_uow_starts_session_and_transaction_with_commit_time():
    databases, client = _make_databases()
    session = MagicMock(spec=AsyncClientSession)
    _wire_session_context(client, session)
    tx_cm = _wire_transaction_context(session)

    async with MongoUnitOfWork(databases, max_commit_time_ms=12_000) as uow:
        assert uow.session is session

    client.start_session.assert_called_once()
    session.start_transaction.assert_awaited_once_with(max_commit_time_ms=12_000)
    tx_cm.__aexit__.assert_awaited_once()
    assert tx_cm.__aexit__.await_args[0][0] is None


@pytest.mark.asyncio
async def test_uow_aborts_when_body_raises():
    databases, client = _make_databases()
    session = MagicMock(spec=AsyncClientSession)
    _wire_session_context(client, session)
    tx_cm = _wire_transaction_context(session)

    with pytest.raises(RuntimeError, match="fallo"):
        async with MongoUnitOfWork(databases) as _uow:
            raise RuntimeError("fallo")

    tx_cm.__aexit__.assert_awaited_once()
    exc_type = tx_cm.__aexit__.await_args[0][0]
    assert exc_type is RuntimeError


@pytest.mark.asyncio
async def test_uow_closes_session_after_success():
    databases, client = _make_databases()
    session = MagicMock(spec=AsyncClientSession)
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    client.start_session.return_value = session_cm
    _wire_transaction_context(session)

    async with MongoUnitOfWork(databases):
        pass

    session_cm.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
async def test_uow_session_unavailable_outside_context():
    databases, _client = _make_databases()
    uow = MongoUnitOfWork(databases)
    with pytest.raises(MongoUnitOfWorkInactiveError):
        _ = uow.session


@pytest.mark.asyncio
async def test_uow_maps_unknown_commit_result_to_uncertain_error():
    databases, client = _make_databases()
    session = MagicMock(spec=AsyncClientSession)
    _wire_session_context(client, session)
    uncertain = OperationFailure("commit uncertain", 251)
    uncertain._add_error_label("UnknownTransactionCommitResult")
    _wire_transaction_context(session, exit_side_effect=uncertain)

    with pytest.raises(MongoTransactionCommitUncertainError) as exc_info:
        async with MongoUnitOfWork(databases):
            pass

    assert isinstance(exc_info.value.__cause__, OperationFailure)


@pytest.mark.asyncio
async def test_uow_implements_organization_port():
    databases, client = _make_databases()
    session = MagicMock(spec=AsyncClientSession)
    _wire_session_context(client, session)
    _wire_transaction_context(session)

    uow = MongoUnitOfWork(databases)
    assert isinstance(uow, OrganizationUnitOfWork)


def test_default_max_commit_time_is_reasonable():
    assert DEFAULT_MAX_COMMIT_TIME_MS == 30_000


@pytest.mark.asyncio
async def test_uow_closes_session_when_transaction_start_fails():
    databases, client = _make_databases()
    session = MagicMock(spec=AsyncClientSession)
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    client.start_session.return_value = session_cm
    session.start_transaction = AsyncMock(side_effect=RuntimeError("tx fail"))

    uow = MongoUnitOfWork(databases)
    with pytest.raises(RuntimeError, match="tx fail"):
        async with uow:
            pass

    session_cm.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
async def test_uow_cannot_be_reused_after_successful_run():
    databases, client = _make_databases()
    session = MagicMock(spec=AsyncClientSession)
    _wire_session_context(client, session)
    _wire_transaction_context(session)

    uow = MongoUnitOfWork(databases)
    async with uow:
        pass
    with pytest.raises(MongoUnitOfWorkInactiveError, match="reutilización"):
        async with uow:
            pass
