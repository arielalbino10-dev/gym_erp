"""Validación application de alcance de sucursales antes de persistir membresía."""

from __future__ import annotations

from gym_erp_api.modules.access.application.errors import BranchScopeValidationError
from gym_erp_api.modules.access.application.ports.tenant_branch_scope_validator import (
    TenantBranchScopeValidator,
)
from gym_erp_api.modules.access.domain.enums import BranchScopeMode
from gym_erp_api.modules.organization.domain.validators import require_uuid_v4


async def ensure_membership_branch_scope(
    *,
    tenant_id: str,
    branch_scope_mode: BranchScopeMode,
    allowed_branch_ids: frozenset[str] | None,
    validator: TenantBranchScopeValidator,
    session: object | None = None,
) -> None:
    """No autoriza por UUID válido solo; exige pertenencia al tenant vía adaptador."""
    tid = require_uuid_v4(tenant_id, "tenant_id")
    if branch_scope_mode is BranchScopeMode.ALL_BRANCHES:
        if allowed_branch_ids:
            raise BranchScopeValidationError(
                "all_branches no admite allowed_branch_ids en asignación."
            )
        return
    if not allowed_branch_ids:
        return
    await validator.ensure_all_branches_belong_to_tenant(
        tenant_id=tid,
        branch_ids=allowed_branch_ids,
        session=session,
    )
