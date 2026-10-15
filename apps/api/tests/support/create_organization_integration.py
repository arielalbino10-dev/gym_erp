"""Wiring de integración para CreateOrganizationHandler (solo tests)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from gym_erp_api.infrastructure.mongo.mongo_unit_of_work import MongoUnitOfWork
from gym_erp_api.infrastructure.mongo.scoped_repository import TenantScopedRepository
from gym_erp_api.modules.organization.application.commands.create_organization import (
    CreateOrganizationCommand,
    CreateOrganizationResult,
)
from gym_erp_api.modules.organization.application.errors import IdempotencyInProgressError
from gym_erp_api.modules.organization.application.use_cases.create_organization_handler import (
    CreateOrganizationHandler,
)
from gym_erp_api.modules.organization.domain.enums import BranchStatus
from gym_erp_api.modules.organization.domain.tenant import Tenant
from gym_erp_api.modules.organization.infrastructure.mongo.operational_branch_repository import (
    OperationalBranchRepository,
)
from gym_erp_api.modules.organization.infrastructure.mongo.platform_idempotency_repository import (
    PlatformIdempotencyRepository,
)
from gym_erp_api.modules.organization.infrastructure.mongo.platform_tenant_repository import (
    PlatformTenantRepository,
)
from gym_erp_api.shared_kernel.tenant_context import TenantContext


class AbortCreateOrganizationProbe(Exception):
    """Provoca abort transaccional controlado durante el alta (sin simular red)."""


class IntegrationOperationalBranchRepositoryFactory:
    """Factory real scoped al tenant recién provisionado (branch_scoped=True)."""

    def __init__(self, operational_branches_collection: Any) -> None:
        self._collection = operational_branches_collection

    def for_provisioned_tenant(
        self,
        *,
        tenant_id: str,
        allowed_branch_id: str,
        actor_user_id: str,
        actor_membership_id: str,
    ) -> OperationalBranchRepository:
        ctx = TenantContext(
            tenant_id=tenant_id,
            user_id=actor_user_id,
            membership_id=actor_membership_id,
            allowed_branch_ids=frozenset({allowed_branch_id}),
        )
        scoped = TenantScopedRepository(self._collection, ctx, branch_scoped=True)
        return OperationalBranchRepository(scoped)


def build_create_organization_handler(
    *,
    tenant_repository: PlatformTenantRepository,
    idempotency_repository: PlatformIdempotencyRepository,
    operational_branches_collection: Any,
    mongo_databases: Any,
) -> CreateOrganizationHandler:
    branch_factory = IntegrationOperationalBranchRepositoryFactory(operational_branches_collection)

    def unit_of_work_factory() -> MongoUnitOfWork:
        return MongoUnitOfWork(mongo_databases)

    return CreateOrganizationHandler(
        idempotency_store=idempotency_repository,
        tenant_repository=tenant_repository,
        branch_repository_factory=branch_factory,
        unit_of_work_factory=unit_of_work_factory,
    )


def integration_create_command(
    *,
    idempotency_key: str,
    legal_name: str = "Integration Legal SA",
    display_name: str = "Integration Gym",
    branch_name: str = "Sucursal Integración",
    **kwargs: Any,
) -> CreateOrganizationCommand:
    return CreateOrganizationCommand.build(
        idempotency_key=idempotency_key,
        legal_name=legal_name,
        display_name=display_name,
        branch_name=branch_name,
        **kwargs,
    )


async def execute_create_organization_with_in_progress_retry(
    handler: CreateOrganizationHandler,
    command: CreateOrganizationCommand,
    *,
    attempts: int = 50,
    delay_seconds: float = 0.02,
) -> CreateOrganizationResult:
    """Reintenta solo IdempotencyInProgressError (misma clave, sin nuevos UUID)."""
    import asyncio

    last: BaseException | None = None
    for _ in range(attempts):
        try:
            return await handler.execute(command)
        except IdempotencyInProgressError as exc:
            last = exc
            await asyncio.sleep(delay_seconds)
    raise AssertionError(
        "CreateOrganization no completó tras reintentos por in-progress."
    ) from last


@dataclass
class SessionCapture:
    session_object_ids: list[int] = field(default_factory=list)

    def record(self, session: object | None) -> None:
        if session is not None:
            self.session_object_ids.append(id(session))


class SessionRecordingTenantRepository:
    """Delega en PlatformTenantRepository y registra sesiones transaccionales."""

    def __init__(self, inner: PlatformTenantRepository, capture: SessionCapture) -> None:
        self._inner = inner
        self._capture = capture

    async def insert(self, tenant: Tenant, *, session: object | None = None) -> None:
        self._capture.record(session)
        await self._inner.insert(tenant, session=session)

    async def get_by_id(self, tenant_id: str, *, session: object | None = None) -> Tenant | None:
        return await self._inner.get_by_id(tenant_id, session=session)

    async def exists_by_id(self, tenant_id: str, *, session: object | None = None) -> bool:
        return await self._inner.exists_by_id(tenant_id, session=session)

    async def save(self, tenant: Tenant, *, session: object | None = None) -> None:
        self._capture.record(session)
        await self._inner.save(tenant, session=session)


class AbortOnTenantSaveRepository(SessionRecordingTenantRepository):
    async def save(self, tenant: Tenant, *, session: object | None = None) -> None:
        self._capture.record(session)
        raise AbortCreateOrganizationProbe("abort before mark_completed")


class SessionRecordingBranchRepository:
    def __init__(self, inner: OperationalBranchRepository, capture: SessionCapture) -> None:
        self._inner = inner
        self._capture = capture

    async def insert(self, branch: object, *, session: object | None = None) -> None:
        self._capture.record(session)
        await self._inner.insert(branch, session=session)

    async def get_by_id(self, branch_id: str, *, session: object | None = None) -> object | None:
        return await self._inner.get_by_id(branch_id, session=session)

    async def list_branches(
        self,
        *,
        status: BranchStatus | None = None,
        session: object | None = None,
    ):
        return await self._inner.list_branches(status=status, session=session)

    async def save(self, branch: object, *, session: object | None = None) -> None:
        self._capture.record(session)
        await self._inner.save(branch, session=session)


class SessionRecordingBranchRepositoryFactory(IntegrationOperationalBranchRepositoryFactory):
    def __init__(
        self,
        operational_branches_collection: Any,
        capture: SessionCapture,
    ) -> None:
        super().__init__(operational_branches_collection)
        self._capture = capture

    def for_provisioned_tenant(
        self,
        *,
        tenant_id: str,
        allowed_branch_id: str,
        actor_user_id: str,
        actor_membership_id: str,
    ) -> SessionRecordingBranchRepository:
        inner = super().for_provisioned_tenant(
            tenant_id=tenant_id,
            allowed_branch_id=allowed_branch_id,
            actor_user_id=actor_user_id,
            actor_membership_id=actor_membership_id,
        )
        return SessionRecordingBranchRepository(inner, self._capture)


class SessionRecordingIdempotencyRepository:
    def __init__(
        self,
        inner: PlatformIdempotencyRepository,
        capture: SessionCapture,
    ) -> None:
        self._inner = inner
        self._capture = capture

    async def find_by_operation_and_key(
        self,
        operation: str,
        idempotency_key: str,
        *,
        session: object | None = None,
    ):
        return await self._inner.find_by_operation_and_key(
            operation,
            idempotency_key,
            session=session,
        )

    async def reserve(self, reservation: object, *, session: object) -> None:
        self._capture.record(session)
        await self._inner.reserve(reservation, session=session)

    async def mark_completed(
        self,
        operation: str,
        idempotency_key: str,
        *,
        result: CreateOrganizationResult,
        session: object,
    ) -> None:
        self._capture.record(session)
        await self._inner.mark_completed(
            operation,
            idempotency_key,
            result=result,
            session=session,
        )
