"""Mapa tenant -> sucursales para pruebas de validación de alcance."""

from __future__ import annotations

from gym_erp_api.modules.access.application.errors import BranchScopeValidationError


class InMemoryTenantBranchScopeValidator:
    def __init__(self, *, branches_by_tenant: dict[str, frozenset[str]]) -> None:
        self._map = branches_by_tenant

    async def ensure_all_branches_belong_to_tenant(
        self,
        *,
        tenant_id: str,
        branch_ids: frozenset[str],
        session: object | None = None,
    ) -> None:
        allowed = self._map.get(tenant_id, frozenset())
        foreign = branch_ids - allowed
        if foreign:
            raise BranchScopeValidationError("La sucursal no pertenece al tenant o no existe.")
