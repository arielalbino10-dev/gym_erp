"""Adaptador: comprueba sucursales en operational scoped por tenant."""

from __future__ import annotations

from collections.abc import Callable

from gym_erp_api.modules.access.application.errors import BranchScopeValidationError
from gym_erp_api.modules.organization.application.ports.branch_repository import BranchRepository
from gym_erp_api.modules.organization.domain.validators import require_uuid_v4


class OrganizationBranchScopeValidator:
    """Recibe factory ``tenant_id -> BranchRepository`` (operational scoped, sin bypass)."""

    def __init__(
        self,
        *,
        branch_repository_for_tenant: Callable[[str], BranchRepository],
    ) -> None:
        self._branch_repository_for_tenant = branch_repository_for_tenant

    async def ensure_all_branches_belong_to_tenant(
        self,
        *,
        tenant_id: str,
        branch_ids: frozenset[str],
        session: object | None = None,
    ) -> None:
        tid = require_uuid_v4(tenant_id, "tenant_id")
        if not branch_ids:
            return
        branches = self._branch_repository_for_tenant(tid)
        for branch_id in branch_ids:
            require_uuid_v4(branch_id, "branch_id")
            found = await branches.get_by_id(branch_id, session=session)
            if found is None:
                raise BranchScopeValidationError("La sucursal no pertenece al tenant o no existe.")
