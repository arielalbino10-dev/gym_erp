"""Puerto de idempotencia (sin PyMongo en application)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable

from gym_erp_api.modules.organization.application.commands.create_organization import (
    CreateOrganizationResult,
)


class IdempotencyRecordStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class IdempotencyRecord:
    """Estado persistido de una operación idempotente (lectura / replay)."""

    operation: str
    idempotency_key: str
    status: IdempotencyRecordStatus
    request_fingerprint: str
    tenant_id: str | None = None
    branch_id: str | None = None
    result: CreateOrganizationResult | None = None

    def __post_init__(self) -> None:
        if self.status == IdempotencyRecordStatus.COMPLETED:
            if self.result is None or self.tenant_id is None or self.branch_id is None:
                raise ValueError("Registro completed requiere result y tenant_id/branch_id.")
        elif self.status == IdempotencyRecordStatus.PENDING:
            if self.result is not None:
                raise ValueError("Registro pending no debe incluir result.")
        elif self.status == IdempotencyRecordStatus.FAILED:
            if self.result is not None:
                raise ValueError("Registro failed no debe incluir result.")


@dataclass(frozen=True, slots=True)
class IdempotencyReservation:
    """Identificadores reservados al iniciar un alta (pending)."""

    operation: str
    idempotency_key: str
    tenant_id: str
    branch_id: str
    request_fingerprint: str


@runtime_checkable
class IdempotencyStore(Protocol):
    """Contrato mínimo para CreateOrganization (H1-D.3.3.1).

    Concurrencia en ``reserve``: si la clave ya existe, el adaptador debe lanzar
    ``IdempotencyInProgressError`` (pending) o ``IdempotencyPayloadConflictError``
    (completed con fingerprint distinto) sin filtrar excepciones PyMongo al handler.

    ``mark_completed`` debe fallar si no hay transición pending→completed.
    """

    async def find_by_operation_and_key(
        self,
        operation: str,
        idempotency_key: str,
        *,
        session: object | None = None,
    ) -> IdempotencyRecord | None:
        """Consulta por namespace ``operation`` + clave (replay / conflictos)."""
        ...

    async def reserve(
        self,
        reservation: IdempotencyReservation,
        *,
        session: object,
    ) -> None:
        """Inserta estado pending en la misma sesión transaccional que el alta."""
        ...

    async def mark_completed(
        self,
        operation: str,
        idempotency_key: str,
        *,
        result: CreateOrganizationResult,
        session: object,
    ) -> None:
        """Marca completed y persiste resultado en la misma sesión que el commit de negocio."""
        ...
