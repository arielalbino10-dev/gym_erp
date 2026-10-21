"""Alta de sucursal en tenant activo (permiso branches.create)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from pymongo.errors import DuplicateKeyError

from gym_erp_api.modules.access.application.authorization.gym_authorization_service import (
    GymAuthorizationService,
)
from gym_erp_api.modules.access.application.services.tenant_context_factory import (
    ResolvedTenantContext,
)
from gym_erp_api.modules.access.domain.gym_permission import GymPermission
from gym_erp_api.modules.organization.application.commands.gym_branch_commands import (
    CreateAuthorizedBranchCommand,
)
from gym_erp_api.modules.organization.application.dto.branch_public_view import BranchPublicView
from gym_erp_api.modules.organization.application.errors import BranchDuplicateApplicationError
from gym_erp_api.modules.organization.application.ports.tenant_context_branch_repository_factory import (  # noqa: E501
    TenantContextBranchRepositoryFactory,
)
from gym_erp_api.modules.organization.domain.branch import DEFAULT_BRANCH_TIMEZONE, Branch
from gym_erp_api.shared_kernel.identifiers import new_uuid


class CreateAuthorizedBranchUseCase:
    def __init__(
        self,
        *,
        authorization: GymAuthorizationService,
        branch_repository_factory: TenantContextBranchRepositoryFactory,
        id_generator: Callable[[], str] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._authorization = authorization
        self._branch_factory = branch_repository_factory
        self._id_generator = id_generator or new_uuid
        self._clock = clock or (lambda: datetime.now(UTC))

    async def execute(
        self,
        *,
        tenant: ResolvedTenantContext,
        command: CreateAuthorizedBranchCommand,
    ) -> BranchPublicView:
        auth = self._authorization.trusted_context_from_resolved(tenant)
        self._authorization.require_permission(
            auth=auth,
            permission=GymPermission.BRANCHES_CREATE,
        )
        moment = self._clock()
        branch = Branch.create(
            tenant_id=tenant.context.tenant_id,
            name=command.name,
            timezone=command.timezone or DEFAULT_BRANCH_TIMEZONE,
            code=command.code,
            branch_id=self._id_generator(),
            created_by_user_id=tenant.context.user_id,
            now=moment,
        )
        repo = self._branch_factory.for_context(tenant.context)
        try:
            await repo.insert(branch)
        except DuplicateKeyError as exc:
            raise BranchDuplicateApplicationError(
                "Ya existe una sucursal con el identificador o código indicado."
            ) from exc
        return BranchPublicView.from_branch(branch)
