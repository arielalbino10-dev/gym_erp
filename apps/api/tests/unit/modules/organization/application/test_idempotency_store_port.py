"""Contrato IdempotencyStore sin PyMongo."""

import inspect

import pytest

from gym_erp_api.modules.organization.application.idempotency_constants import (
    CREATE_ORGANIZATION_OPERATION,
)
from gym_erp_api.modules.organization.application.ports.idempotency_store import (
    IdempotencyRecord,
    IdempotencyRecordStatus,
    IdempotencyReservation,
    IdempotencyStore,
)


class _FakeIdempotencyStore:
    async def find_by_operation_and_key(
        self,
        operation: str,
        idempotency_key: str,
        *,
        session: object | None = None,
    ) -> IdempotencyRecord | None:
        return None

    async def reserve(self, reservation: IdempotencyReservation, *, session: object) -> None:
        return None

    async def mark_completed(
        self,
        operation: str,
        idempotency_key: str,
        *,
        result: object,
        session: object,
    ) -> None:
        return None


def test_fake_satisfies_idempotency_store_protocol():
    assert isinstance(_FakeIdempotencyStore(), IdempotencyStore)


def test_idempotency_store_methods_accept_opaque_session():
    reserve_sig = inspect.signature(IdempotencyStore.reserve)
    assert reserve_sig.parameters["session"].annotation in (object, "object")
    find_sig = inspect.signature(IdempotencyStore.find_by_operation_and_key)
    session_param = find_sig.parameters["session"]
    assert session_param.default is None


def test_create_organization_operation_constant():
    assert CREATE_ORGANIZATION_OPERATION == "create_organization"


def test_idempotency_record_status_values():
    assert IdempotencyRecordStatus.PENDING == "pending"
    assert IdempotencyRecordStatus.COMPLETED == "completed"


def test_reservation_is_frozen():
    reservation = IdempotencyReservation(
        operation=CREATE_ORGANIZATION_OPERATION,
        idempotency_key="req-abc-123456",
        tenant_id="550e8400-e29b-41d4-a716-446655440001",
        branch_id="990e8400-e29b-41d4-a716-446655440030",
        request_fingerprint="abc123",
    )
    with pytest.raises(Exception):
        reservation.tenant_id = "other"  # type: ignore[misc]
