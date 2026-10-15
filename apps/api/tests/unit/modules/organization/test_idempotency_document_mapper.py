from datetime import UTC, datetime

import pytest

from gym_erp_api.modules.organization.application.errors import IdempotencyDocumentInvalidError
from gym_erp_api.modules.organization.application.idempotency_constants import (
    CREATE_ORGANIZATION_OPERATION,
)
from gym_erp_api.modules.organization.application.ports.idempotency_store import (
    IdempotencyRecordStatus,
    IdempotencyReservation,
)
from gym_erp_api.modules.organization.infrastructure.mongo.idempotency_document_mapper import (
    build_idempotency_document_id,
    idempotency_from_document,
    reservation_to_insert_document,
)
from tests.support.tenant_fixtures import BRANCH_X_ID, TENANT_A_ID


def test_document_id_separates_operation_and_key():
    id_a = build_idempotency_document_id(CREATE_ORGANIZATION_OPERATION, "req-abc-123456")
    id_b = build_idempotency_document_id(CREATE_ORGANIZATION_OPERATION, "req-xyz-987654")
    assert id_a != id_b


def test_reservation_insert_document_shape():
    moment = datetime(2026, 7, 1, tzinfo=UTC)
    reservation = IdempotencyReservation(
        operation=CREATE_ORGANIZATION_OPERATION,
        idempotency_key="req-abc-123456",
        tenant_id=TENANT_A_ID,
        branch_id=BRANCH_X_ID,
        request_fingerprint="deadbeef",
    )
    doc = reservation_to_insert_document(reservation, now=moment)
    assert doc["status"] == IdempotencyRecordStatus.PENDING.value
    assert doc["_id"] == build_idempotency_document_id(
        CREATE_ORGANIZATION_OPERATION,
        "req-abc-123456",
    )
    assert "result" not in doc


def test_from_document_rejects_naive_datetime():
    doc = {
        "_id": build_idempotency_document_id(CREATE_ORGANIZATION_OPERATION, "req-abc-123456"),
        "operation": CREATE_ORGANIZATION_OPERATION,
        "idempotency_key": "req-abc-123456",
        "status": "completed",
        "request_fingerprint": "fp",
        "tenant_id": TENANT_A_ID,
        "branch_id": BRANCH_X_ID,
        "result": {
            "tenant_id": TENANT_A_ID,
            "branch_id": BRANCH_X_ID,
            "tenant_status": "active",
            "branch_status": "active",
            "idempotency_replayed": True,
            "created_at": datetime(2026, 1, 1, 12, 0),
        },
    }
    with pytest.raises(IdempotencyDocumentInvalidError):
        idempotency_from_document(doc)


def test_from_document_rejects_invalid_uuid():
    doc = {
        "_id": build_idempotency_document_id(CREATE_ORGANIZATION_OPERATION, "req-abc-123456"),
        "operation": CREATE_ORGANIZATION_OPERATION,
        "idempotency_key": "req-abc-123456",
        "status": "pending",
        "request_fingerprint": "fp",
        "tenant_id": "not-a-uuid",
        "branch_id": BRANCH_X_ID,
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
        "updated_at": datetime(2026, 1, 1, tzinfo=UTC),
    }
    with pytest.raises(IdempotencyDocumentInvalidError):
        idempotency_from_document(doc)


def test_from_document_completed_round_trip():
    moment = datetime(2026, 7, 2, 8, 0, tzinfo=UTC)
    doc_id = build_idempotency_document_id(CREATE_ORGANIZATION_OPERATION, "req-abc-123456")
    raw = {
        "_id": doc_id,
        "operation": CREATE_ORGANIZATION_OPERATION,
        "idempotency_key": "req-abc-123456",
        "status": "completed",
        "request_fingerprint": "fp1",
        "tenant_id": TENANT_A_ID,
        "branch_id": BRANCH_X_ID,
        "result": {
            "tenant_id": TENANT_A_ID,
            "branch_id": BRANCH_X_ID,
            "tenant_status": "active",
            "branch_status": "active",
            "idempotency_replayed": False,
            "created_at": moment,
        },
    }
    record = idempotency_from_document(raw)
    assert record is not None
    assert record.status == IdempotencyRecordStatus.COMPLETED
    assert record.result is not None
    assert record.result.created_at.tzinfo is not None
