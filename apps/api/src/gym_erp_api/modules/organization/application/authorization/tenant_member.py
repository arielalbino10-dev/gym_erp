"""Acceso tenant-scoped basado en TenantContext confiable (tests / futuro post-auth)."""

from __future__ import annotations

from dataclasses import dataclass

from gym_erp_api.modules.organization.application.errors import (
    BranchAccessDeniedApplicationError,
    TenantAccessDeniedApplicationError,
)
from gym_erp_api.modules.organization.domain.validators import require_uuid_v4
from gym_erp_api.shared_kernel.tenant_context import TenantContext


@dataclass(frozen=True, slots=True)
class TenantMemberAccess:
    """Contrato mínimo para operaciones operational de un miembro en un tenant.

    No interpreta headers, query ni body como fuente de ``tenant_id``.
    El ``TenantContext`` debe construirse en capa bootstrap cuando exista ADR-0003;
    en H1-D.3.1 solo tests y casos de uso internos lo instancian explícitamente.
    """

    context: TenantContext

    @classmethod
    def bind(cls, context: TenantContext) -> TenantMemberAccess:
        return cls(context=context)

    @property
    def tenant_id(self) -> str:
        return self.context.tenant_id

    def require_matching_tenant(self, requested_tenant_id: str) -> None:
        """Rechaza identificadores de empresa enviados por capas externas."""
        requested = require_uuid_v4(requested_tenant_id, "tenant_id")
        if requested != self.context.tenant_id:
            raise TenantAccessDeniedApplicationError(
                "El tenant solicitado no coincide con el contexto autorizado."
            )

    def require_branch_in_scope(self, branch_id: str) -> None:
        branch = require_uuid_v4(branch_id, "branch_id")
        allowed = self.context.allowed_branch_ids
        if allowed is not None and branch not in allowed:
            raise BranchAccessDeniedApplicationError(
                "La sucursal está fuera del alcance permitido por el contexto."
            )

    def filter_branch_ids(self, branch_ids: frozenset[str]) -> frozenset[str]:
        allowed = self.context.allowed_branch_ids
        if allowed is None:
            return branch_ids
        return frozenset(bid for bid in branch_ids if bid in allowed)
