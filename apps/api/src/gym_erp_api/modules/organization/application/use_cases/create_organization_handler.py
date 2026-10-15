"""Caso de uso interno: alta transaccional tenant + sucursal inicial (H1-D.3.3.3)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from gym_erp_api.infrastructure.mongo.uow_errors import MongoTransactionCommitUncertainError
from gym_erp_api.modules.organization.application.authorization.platform_provisioning import (
    PlatformProvisioningScope,
)
from gym_erp_api.modules.organization.application.bootstrap_context import (
    CREATE_ORGANIZATION_BOOTSTRAP_MEMBERSHIP_ID,
    CREATE_ORGANIZATION_BOOTSTRAP_USER_ID,
)
from gym_erp_api.modules.organization.application.commands.create_organization import (
    CreateOrganizationCommand,
    CreateOrganizationResult,
)
from gym_erp_api.modules.organization.application.create_organization_fingerprint import (
    create_organization_request_fingerprint,
)
from gym_erp_api.modules.organization.application.errors import (
    IdempotencyAlreadyCompletedError,
    IdempotencyInProgressError,
    IdempotencyPayloadConflictError,
    OrganizationCommitUncertainError,
)
from gym_erp_api.modules.organization.application.idempotency_constants import (
    CREATE_ORGANIZATION_OPERATION,
)
from gym_erp_api.modules.organization.application.ports.idempotency_store import (
    IdempotencyRecord,
    IdempotencyRecordStatus,
    IdempotencyReservation,
    IdempotencyStore,
)
from gym_erp_api.modules.organization.application.ports.operational_branch_repository_factory import (  # noqa: E501
    OperationalBranchRepositoryFactory,
)
from gym_erp_api.modules.organization.application.ports.tenant_repository import TenantRepository
from gym_erp_api.modules.organization.application.ports.unit_of_work_factory import (
    OrganizationUnitOfWorkFactory,
)
from gym_erp_api.modules.organization.domain.branch import Branch
from gym_erp_api.modules.organization.domain.enums import BranchStatus, TenantStatus
from gym_erp_api.modules.organization.domain.tenant import Tenant
from gym_erp_api.shared_kernel.identifiers import new_uuid


class CreateOrganizationHandler:
    """Orquesta platform + operational + idempotencia en un solo MongoUnitOfWork."""

    def __init__(
        self,
        *,
        idempotency_store: IdempotencyStore,
        tenant_repository: TenantRepository,
        branch_repository_factory: OperationalBranchRepositoryFactory,
        unit_of_work_factory: OrganizationUnitOfWorkFactory,
        id_generator: Callable[[], str] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._idempotency = idempotency_store
        self._tenants = tenant_repository
        self._branch_factory = branch_repository_factory
        self._uow_factory = unit_of_work_factory
        self._id_generator = id_generator or new_uuid
        self._clock = clock or (lambda: datetime.now(UTC))

    async def execute(self, command: CreateOrganizationCommand) -> CreateOrganizationResult:
        fingerprint = create_organization_request_fingerprint(command)
        preflight = await self._idempotency.find_by_operation_and_key(
            CREATE_ORGANIZATION_OPERATION,
            command.idempotency_key,
        )
        replay = self._replay_if_completed(preflight, fingerprint)
        if replay is not None:
            return replay
        self._reject_preflight_conflict(preflight, fingerprint)

        tenant_id = self._id_generator()
        branch_id = self._id_generator()
        moment = self._clock()

        tenant = Tenant.create(
            legal_name=command.legal_name,
            display_name=command.display_name,
            timezone=command.tenant_timezone,
            commercial_email=command.commercial_email,
            tenant_id=tenant_id,
            created_by_user_id=command.created_by_user_id,
            now=moment,
        )
        branch = Branch.create(
            tenant_id=tenant_id,
            name=command.branch_name,
            timezone=command.branch_timezone,
            code=command.branch_code,
            address=command.branch_address,
            branch_id=branch_id,
            created_by_user_id=command.created_by_user_id,
            now=moment,
        )

        scope = PlatformProvisioningScope.for_single_tenant(tenant_id)
        scope.require_target_tenant(tenant_id)

        actor_user_id = command.created_by_user_id or CREATE_ORGANIZATION_BOOTSTRAP_USER_ID
        actor_membership_id = CREATE_ORGANIZATION_BOOTSTRAP_MEMBERSHIP_ID
        branch_repo = self._branch_factory.for_provisioned_tenant(
            tenant_id=tenant_id,
            allowed_branch_id=branch_id,
            actor_user_id=actor_user_id,
            actor_membership_id=actor_membership_id,
        )

        reservation = IdempotencyReservation(
            operation=CREATE_ORGANIZATION_OPERATION,
            idempotency_key=command.idempotency_key,
            tenant_id=tenant_id,
            branch_id=branch_id,
            request_fingerprint=fingerprint,
        )

        try:
            async with self._uow_factory() as uow:
                session = uow.session
                await self._idempotency.reserve(reservation, session=session)
                await self._tenants.insert(tenant, session=session)
                await branch_repo.insert(branch, session=session)
                active_tenant = tenant.transition_status(
                    TenantStatus.ACTIVE,
                    updated_by_user_id=command.created_by_user_id,
                    now=moment,
                )
                scope.require_target_tenant(active_tenant.tenant_id)
                await self._tenants.save(active_tenant, session=session)
                result = CreateOrganizationResult(
                    tenant_id=tenant_id,
                    branch_id=branch_id,
                    tenant_status=TenantStatus.ACTIVE,
                    branch_status=BranchStatus.ACTIVE,
                    idempotency_replayed=False,
                    created_at=active_tenant.created_at,
                )
                await self._idempotency.mark_completed(
                    CREATE_ORGANIZATION_OPERATION,
                    command.idempotency_key,
                    result=result,
                    session=session,
                )
        except IdempotencyAlreadyCompletedError:
            return await self._load_replay_after_collision(command.idempotency_key, fingerprint)
        except MongoTransactionCommitUncertainError as exc:
            recovered = await self._recover_after_uncertain_commit(
                command.idempotency_key,
                fingerprint,
            )
            if recovered is not None:
                return recovered
            raise OrganizationCommitUncertainError(
                "Commit incierto y resultado no verificable por idempotencia."
            ) from exc

        return result

    def _replay_if_completed(
        self,
        record: IdempotencyRecord | None,
        fingerprint: str,
    ) -> CreateOrganizationResult | None:
        if record is None or record.status != IdempotencyRecordStatus.COMPLETED:
            return None
        if record.request_fingerprint != fingerprint:
            raise IdempotencyPayloadConflictError(
                "La clave de idempotencia ya existe con datos de negocio distintos."
            )
        if record.result is None:
            raise IdempotencyPayloadConflictError("Registro completed sin resultado almacenado.")
        return CreateOrganizationResult(
            tenant_id=record.result.tenant_id,
            branch_id=record.result.branch_id,
            tenant_status=record.result.tenant_status,
            branch_status=record.result.branch_status,
            idempotency_replayed=True,
            created_at=record.result.created_at,
        )

    def _reject_preflight_conflict(
        self,
        record: IdempotencyRecord | None,
        fingerprint: str,
    ) -> None:
        if record is None:
            return
        if record.request_fingerprint != fingerprint:
            raise IdempotencyPayloadConflictError(
                "La clave de idempotencia ya existe con datos de negocio distintos."
            )
        if record.status == IdempotencyRecordStatus.PENDING:
            raise IdempotencyInProgressError("Alta en curso para esta clave de idempotencia.")
        if record.status == IdempotencyRecordStatus.FAILED:
            raise IdempotencyPayloadConflictError("La clave de idempotencia está en estado failed.")

    async def _load_replay_after_collision(
        self,
        idempotency_key: str,
        fingerprint: str,
    ) -> CreateOrganizationResult:
        record = await self._idempotency.find_by_operation_and_key(
            CREATE_ORGANIZATION_OPERATION,
            idempotency_key,
        )
        replay = self._replay_if_completed(record, fingerprint)
        if replay is not None:
            return replay
        raise IdempotencyInProgressError(
            "Colisión de idempotencia sin resultado completed verificable."
        )

    async def _recover_after_uncertain_commit(
        self,
        idempotency_key: str,
        fingerprint: str,
    ) -> CreateOrganizationResult | None:
        record = await self._idempotency.find_by_operation_and_key(
            CREATE_ORGANIZATION_OPERATION,
            idempotency_key,
        )
        return self._replay_if_completed(record, fingerprint)
