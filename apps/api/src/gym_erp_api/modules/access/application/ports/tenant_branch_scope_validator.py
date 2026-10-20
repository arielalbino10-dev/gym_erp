"""Validación de sucursales contra tenant (consulta operational en adaptador, no en dominio)."""

from __future__ import annotations

from typing import Protocol


class TenantBranchScopeValidator(Protocol):
    async def ensure_all_branches_belong_to_tenant(
        self,
        *,
        tenant_id: str,
        branch_ids: frozenset[str],
        session: object | None = None,
    ) -> None:
        """Fallo si algún branch_id no pertenece al tenant en gym_operational."""
