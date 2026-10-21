"""Listado de sucursales visibles para el miembro gym."""

from __future__ import annotations

from gym_erp_api.modules.access.application.authorization.gym_authorization_service import (
    GymAuthorizationService,
)
from gym_erp_api.modules.access.application.services.tenant_context_factory import (
    ResolvedTenantContext,
)
from gym_erp_api.modules.access.domain.gym_permission import GymPermission
from gym_erp_api.modules.organization.application.dto.branch_public_view import BranchPublicView
from gym_erp_api.modules.organization.application.ports.tenant_context_branch_repository_factory import (  # noqa: E501
    TenantContextBranchRepositoryFactory,
)
from gym_erp_api.modules.organization.domain.enums import BranchStatus


class ListAuthorizedBranchesUseCase:
    def __init__(
        self,
        *,
        authorization: GymAuthorizationService,
        branch_repository_factory: TenantContextBranchRepositoryFactory,
    ) -> None:
        self._authorization = authorization
        self._branch_factory = branch_repository_factory

    async def execute(
        self,
        *,
        tenant: ResolvedTenantContext,
    ) -> tuple[BranchPublicView, ...]:
        auth = self._authorization.trusted_context_from_resolved(tenant)
        self._authorization.require_permission(
            auth=auth,
            permission=GymPermission.BRANCHES_READ,
            list_operation=True,
        )
        repo = self._branch_factory.for_context(tenant.context)
        rows = await repo.list_branches(status=BranchStatus.ACTIVE)
        return tuple(BranchPublicView.from_branch(row) for row in rows)
