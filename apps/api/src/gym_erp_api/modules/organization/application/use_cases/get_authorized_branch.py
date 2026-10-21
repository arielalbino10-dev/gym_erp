"""Consulta de sucursal por ID con aislamiento tenant + alcance."""

from __future__ import annotations

from gym_erp_api.modules.access.application.authorization.gym_authorization_service import (
    GymAuthorizationService,
)
from gym_erp_api.modules.access.application.services.tenant_context_factory import (
    ResolvedTenantContext,
)
from gym_erp_api.modules.access.domain.gym_permission import GymPermission
from gym_erp_api.modules.organization.application.dto.branch_public_view import BranchPublicView
from gym_erp_api.modules.organization.application.errors import BranchNotFoundApplicationError
from gym_erp_api.modules.organization.application.ports.tenant_context_branch_repository_factory import (  # noqa: E501
    TenantContextBranchRepositoryFactory,
)
from gym_erp_api.modules.organization.domain.validators import require_uuid_v4


class GetAuthorizedBranchUseCase:
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
        branch_id: str,
    ) -> BranchPublicView:
        auth = self._authorization.trusted_context_from_resolved(tenant)
        self._authorization.require_permission(
            auth=auth,
            permission=GymPermission.BRANCHES_READ,
            list_operation=True,
        )
        bid = require_uuid_v4(branch_id, "branch_id")
        repo = self._branch_factory.for_context(tenant.context)
        loaded = await repo.get_by_id(bid)
        if loaded is None:
            raise BranchNotFoundApplicationError("Sucursal no encontrada.")
        return BranchPublicView.from_branch(loaded)
