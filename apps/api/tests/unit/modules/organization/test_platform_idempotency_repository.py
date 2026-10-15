from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo.errors import DuplicateKeyError

from gym_erp_api.infrastructure.mongo.uow_errors import InvalidMongoSessionError
from gym_erp_api.modules.organization.application.commands.create_organization import (
    CreateOrganizationResult,
)
from gym_erp_api.modules.organization.application.errors import (
    IdempotencyAlreadyCompletedError,
    IdempotencyDocumentInvalidError,
    IdempotencyInProgressError,
    IdempotencyPayloadConflictError,
    IdempotencyReservationMissingError,
)
from gym_erp_api.modules.organization.application.idempotency_constants import (
    CREATE_ORGANIZATION_OPERATION,
)
from gym_erp_api.modules.organization.application.ports.idempotency_store import (
    IdempotencyRecordStatus,
    IdempotencyReservation,
    IdempotencyStore,
)
from gym_erp_api.modules.organization.domain.enums import BranchStatus, TenantStatus
from gym_erp_api.modules.organization.infrastructure.mongo.idempotency_document_mapper import (
    build_idempotency_document_id,
)
from gym_erp_api.modules.organization.infrastructure.mongo.platform_idempotency_repository import (
    PlatformIdempotencyRepository,
)
from tests.support.tenant_fixtures import BRANCH_X_ID, TENANT_A_ID


@pytest.fixture
def mongo_client():
    return MagicMock()


@pytest.fixture
def session(mongo_client):
    s = MagicMock(spec=AsyncClientSession)
    s.has_ended = False
    s.in_transaction = True
    s.client = mongo_client
    return s


@pytest.fixture
def collection(mongo_client):
    coll = MagicMock()
    coll.database = MagicMock()
    coll.database.client = mongo_client
    coll.insert_one = AsyncMock()
    coll.find_one = AsyncMock(return_value=None)
    coll.update_one = AsyncMock(return_value=MagicMock(matched_count=1))
    return coll


@pytest.fixture
def repo(collection) -> PlatformIdempotencyRepository:
    return PlatformIdempotencyRepository(collection)


def _reservation(**kwargs) -> IdempotencyReservation:
    base = {
        "operation": CREATE_ORGANIZATION_OPERATION,
        "idempotency_key": "req-abc-123456",
        "tenant_id": TENANT_A_ID,
        "branch_id": BRANCH_X_ID,
        "request_fingerprint": "fingerprint-a",
    }
    base.update(kwargs)
    return IdempotencyReservation(**base)


def _completed_doc(**overrides):
    moment = datetime(2026, 8, 1, tzinfo=UTC)
    doc_id = build_idempotency_document_id(CREATE_ORGANIZATION_OPERATION, "req-abc-123456")
    doc = {
        "_id": doc_id,
        "operation": CREATE_ORGANIZATION_OPERATION,
        "idempotency_key": "req-abc-123456",
        "status": "completed",
        "request_fingerprint": "fingerprint-a",
        "tenant_id": TENANT_A_ID,
        "branch_id": BRANCH_X_ID,
        "result": {
            "tenant_id": TENANT_A_ID,
            "branch_id": BRANCH_X_ID,
            "tenant_status": "active",
            "branch_status": "active",
            "idempotency_replayed": True,
            "created_at": moment,
        },
    }
    doc.update(overrides)
    return doc


@pytest.mark.asyncio
async def test_reserve_inserts_pending_document(repo, collection, session):
    await repo.reserve(_reservation(), session=session)
    collection.insert_one.assert_awaited_once()
    doc = collection.insert_one.await_args[0][0]
    assert doc["status"] == "pending"
    assert collection.insert_one.await_args.kwargs["session"] is session


@pytest.mark.asyncio
async def test_reserve_requires_valid_session(repo, collection):
    with pytest.raises(InvalidMongoSessionError):
        await repo.reserve(_reservation(), session=object())


@pytest.mark.asyncio
async def test_reserve_requires_active_transaction(repo, collection, mongo_client):
    session = MagicMock(spec=AsyncClientSession)
    session.has_ended = False
    session.in_transaction = False
    session.client = mongo_client
    with pytest.raises(InvalidMongoSessionError):
        await repo.reserve(_reservation(), session=session)


@pytest.mark.asyncio
async def test_duplicate_key_with_visible_completed_same_fingerprint(repo, collection, session):
    collection.insert_one = AsyncMock(side_effect=DuplicateKeyError("dup"))
    collection.find_one = AsyncMock(return_value=_completed_doc())
    with pytest.raises(IdempotencyAlreadyCompletedError):
        await repo.reserve(_reservation(), session=session)


@pytest.mark.asyncio
async def test_duplicate_key_with_fingerprint_conflict(repo, collection, session):
    collection.insert_one = AsyncMock(side_effect=DuplicateKeyError("dup"))
    collection.find_one = AsyncMock(return_value=_completed_doc(request_fingerprint="other-fp"))
    with pytest.raises(IdempotencyPayloadConflictError):
        await repo.reserve(_reservation(), session=session)


@pytest.mark.asyncio
async def test_duplicate_key_without_visible_document(repo, collection, session):
    collection.insert_one = AsyncMock(side_effect=DuplicateKeyError("dup"))
    collection.find_one = AsyncMock(return_value=None)
    with pytest.raises(IdempotencyInProgressError, match="no hizo commit"):
        await repo.reserve(_reservation(), session=session)


@pytest.mark.asyncio
async def test_find_completed_record(repo, collection):
    collection.find_one = AsyncMock(return_value=_completed_doc())
    record = await repo.find_by_operation_and_key(
        CREATE_ORGANIZATION_OPERATION,
        "req-abc-123456",
    )
    assert record is not None
    assert record.status == IdempotencyRecordStatus.COMPLETED
    assert record.result is not None
    assert record.result.idempotency_replayed is True


@pytest.mark.asyncio
async def test_find_rejects_corrupt_document(repo, collection):
    collection.find_one = AsyncMock(return_value={"_id": "broken", "status": "pending"})
    with pytest.raises(IdempotencyDocumentInvalidError):
        await repo.find_by_operation_and_key(
            CREATE_ORGANIZATION_OPERATION,
            "req-abc-123456",
        )


@pytest.mark.asyncio
async def test_mark_completed_updates_pending(repo, collection, session):
    moment = datetime(2026, 8, 2, tzinfo=UTC)
    result = CreateOrganizationResult(
        tenant_id=TENANT_A_ID,
        branch_id=BRANCH_X_ID,
        tenant_status=TenantStatus.ACTIVE,
        branch_status=BranchStatus.ACTIVE,
        idempotency_replayed=False,
        created_at=moment,
    )
    await repo.mark_completed(
        CREATE_ORGANIZATION_OPERATION,
        "req-abc-123456",
        result=result,
        session=session,
    )
    collection.update_one.assert_awaited_once()
    filter_doc = collection.update_one.await_args[0][0]
    assert filter_doc["status"] == "pending"
    assert collection.update_one.await_args.kwargs["session"] is session


@pytest.mark.asyncio
async def test_mark_completed_without_reservation(repo, collection, session):
    collection.update_one = AsyncMock(return_value=MagicMock(matched_count=0))
    collection.find_one = AsyncMock(return_value=None)
    moment = datetime(2026, 8, 2, tzinfo=UTC)
    result = CreateOrganizationResult(
        tenant_id=TENANT_A_ID,
        branch_id=BRANCH_X_ID,
        tenant_status=TenantStatus.ACTIVE,
        branch_status=BranchStatus.ACTIVE,
        idempotency_replayed=False,
        created_at=moment,
    )
    with pytest.raises(IdempotencyReservationMissingError):
        await repo.mark_completed(
            CREATE_ORGANIZATION_OPERATION,
            "req-abc-123456",
            result=result,
            session=session,
        )


@pytest.mark.asyncio
async def test_mark_completed_when_already_completed(repo, collection, session):
    collection.update_one = AsyncMock(return_value=MagicMock(matched_count=0))
    collection.find_one = AsyncMock(return_value=_completed_doc())
    moment = datetime(2026, 8, 2, tzinfo=UTC)
    result = CreateOrganizationResult(
        tenant_id=TENANT_A_ID,
        branch_id=BRANCH_X_ID,
        tenant_status=TenantStatus.ACTIVE,
        branch_status=BranchStatus.ACTIVE,
        idempotency_replayed=False,
        created_at=moment,
    )
    with pytest.raises(IdempotencyAlreadyCompletedError):
        await repo.mark_completed(
            CREATE_ORGANIZATION_OPERATION,
            "req-abc-123456",
            result=result,
            session=session,
        )


def test_repository_satisfies_idempotency_store_protocol(repo):
    assert isinstance(repo, IdempotencyStore)


@pytest.mark.asyncio
async def test_reserve_uses_composite_document_id(repo, collection, session):
    await repo.reserve(_reservation(), session=session)
    doc_id = collection.insert_one.await_args[0][0]["_id"]
    expected = build_idempotency_document_id(
        CREATE_ORGANIZATION_OPERATION,
        "req-abc-123456",
    )
    assert doc_id == expected
