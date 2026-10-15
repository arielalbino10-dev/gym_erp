"""Mapper IdempotencyRecord ↔ BSON (colección platform)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from gym_erp_api.modules.organization.application.commands.create_organization import (
    CreateOrganizationResult,
)
from gym_erp_api.modules.organization.application.errors import IdempotencyDocumentInvalidError
from gym_erp_api.modules.organization.application.idempotency_constants import (
    CREATE_ORGANIZATION_OPERATION,
)
from gym_erp_api.modules.organization.application.ports.idempotency_store import (
    IdempotencyRecord,
    IdempotencyRecordStatus,
    IdempotencyReservation,
)
from gym_erp_api.modules.organization.domain.enums import BranchStatus, TenantStatus
from gym_erp_api.modules.organization.domain.errors import (
    InvalidOrganizationIdentifierError,
    InvalidOrganizationPersistenceError,
)
from gym_erp_api.modules.organization.domain.persistence_utils import parse_utc_datetime
from gym_erp_api.modules.organization.domain.validators import require_uuid_v4

ORGANIZATION_IDEMPOTENCY_COLLECTION = "organization_provisioning_idempotency"

_ID_SEPARATOR = "\x1e"
_ALLOWED_OPERATIONS = frozenset({CREATE_ORGANIZATION_OPERATION})


def build_idempotency_document_id(operation: str, idempotency_key: str) -> str:
    _validate_operation(operation)
    _validate_idempotency_key(idempotency_key)
    return f"{operation}{_ID_SEPARATOR}{idempotency_key}"


def parse_idempotency_document_id(document_id: str) -> tuple[str, str]:
    if _ID_SEPARATOR not in document_id:
        raise IdempotencyDocumentInvalidError("_id de idempotencia mal formado.")
    operation, key = document_id.split(_ID_SEPARATOR, 1)
    if not operation or not key:
        raise IdempotencyDocumentInvalidError("_id de idempotencia mal formado.")
    return operation, key


def reservation_to_insert_document(
    reservation: IdempotencyReservation,
    *,
    now: datetime,
) -> dict[str, Any]:
    moment = now.astimezone(UTC)
    doc_id = build_idempotency_document_id(reservation.operation, reservation.idempotency_key)
    tenant_id = require_uuid_v4(reservation.tenant_id, "tenant_id")
    branch_id = require_uuid_v4(reservation.branch_id, "branch_id")
    fingerprint = reservation.request_fingerprint.strip()
    if not fingerprint:
        raise IdempotencyDocumentInvalidError("request_fingerprint vacío en reserva.")
    return {
        "_id": doc_id,
        "operation": reservation.operation,
        "idempotency_key": reservation.idempotency_key,
        "status": IdempotencyRecordStatus.PENDING.value,
        "request_fingerprint": fingerprint,
        "tenant_id": tenant_id,
        "branch_id": branch_id,
        "created_at": moment,
        "updated_at": moment,
    }


def completed_update_fields(
    result: CreateOrganizationResult,
    *,
    now: datetime,
) -> dict[str, Any]:
    moment = now.astimezone(UTC)
    tenant_id = require_uuid_v4(result.tenant_id, "tenant_id")
    branch_id = require_uuid_v4(result.branch_id, "branch_id")
    return {
        "status": IdempotencyRecordStatus.COMPLETED.value,
        "tenant_id": tenant_id,
        "branch_id": branch_id,
        "result": {
            "tenant_id": tenant_id,
            "branch_id": branch_id,
            "tenant_status": result.tenant_status.value,
            "branch_status": result.branch_status.value,
            "idempotency_replayed": result.idempotency_replayed,
            "created_at": result.created_at.astimezone(UTC),
        },
        "updated_at": moment,
    }


def idempotency_from_document(raw: dict[str, Any] | None) -> IdempotencyRecord | None:
    if raw is None:
        return None
    try:
        doc_id = str(raw["_id"])
        operation, idempotency_key = parse_idempotency_document_id(doc_id)
        if raw.get("operation") != operation or raw.get("idempotency_key") != idempotency_key:
            raise IdempotencyDocumentInvalidError("operation/key no coinciden con _id.")
        status = IdempotencyRecordStatus(str(raw["status"]))
        fingerprint = str(raw["request_fingerprint"])
        if not fingerprint:
            raise IdempotencyDocumentInvalidError("request_fingerprint vacío.")
        tenant_raw = raw.get("tenant_id")
        branch_raw = raw.get("branch_id")
        tenant_id = require_uuid_v4(str(tenant_raw), "tenant_id") if tenant_raw else None
        branch_id = require_uuid_v4(str(branch_raw), "branch_id") if branch_raw else None
        result_doc = raw.get("result")
        result: CreateOrganizationResult | None = None
        if result_doc is not None:
            if not isinstance(result_doc, dict):
                raise IdempotencyDocumentInvalidError("result debe ser documento.")
            result = CreateOrganizationResult(
                tenant_id=require_uuid_v4(str(result_doc["tenant_id"]), "tenant_id"),
                branch_id=require_uuid_v4(str(result_doc["branch_id"]), "branch_id"),
                tenant_status=TenantStatus(str(result_doc["tenant_status"])),
                branch_status=BranchStatus(str(result_doc["branch_status"])),
                idempotency_replayed=bool(result_doc["idempotency_replayed"]),
                created_at=parse_utc_datetime(result_doc["created_at"], "created_at"),
            )
        record = IdempotencyRecord(
            operation=operation,
            idempotency_key=idempotency_key,
            status=status,
            request_fingerprint=fingerprint,
            tenant_id=tenant_id,
            branch_id=branch_id,
            result=result,
        )
        return record
    except IdempotencyDocumentInvalidError:
        raise
    except (
        KeyError,
        TypeError,
        ValueError,
        InvalidOrganizationPersistenceError,
        InvalidOrganizationIdentifierError,
    ) as exc:
        raise IdempotencyDocumentInvalidError("Documento de idempotencia inválido.") from exc


def _validate_operation(operation: str) -> None:
    if operation not in _ALLOWED_OPERATIONS:
        raise IdempotencyDocumentInvalidError(f"operation no soportada: {operation!r}.")


def _validate_idempotency_key(key: str) -> None:
    if not isinstance(key, str) or len(key) < 8 or len(key) > 128:
        raise IdempotencyDocumentInvalidError("idempotency_key inválida en persistencia.")
