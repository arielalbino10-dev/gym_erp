"""Alcance platform acotado a un tenant (bootstrap interno futuro; no admin global)."""

from __future__ import annotations

from dataclasses import dataclass

from gym_erp_api.modules.organization.application.errors import TenantAccessDeniedApplicationError
from gym_erp_api.modules.organization.domain.validators import require_uuid_v4


@dataclass(frozen=True, slots=True)
class PlatformProvisioningScope:
    """Autoriza operaciones platform sobre **un** ``target_tenant_id`` por invocación.

    No concede listados globales ni permisos omniscientes. No equivale a sesión
    autenticada (ADR-0003 Proposed).
    """

    target_tenant_id: str

    def __post_init__(self) -> None:
        normalized = require_uuid_v4(self.target_tenant_id, "target_tenant_id")
        object.__setattr__(self, "target_tenant_id", normalized)

    @classmethod
    def for_single_tenant(cls, target_tenant_id: str) -> PlatformProvisioningScope:
        """Emisión explícita para tests o bootstrap interno autorizado."""
        return cls(target_tenant_id=target_tenant_id)

    def require_target_tenant(self, tenant_id: str) -> None:
        requested = require_uuid_v4(tenant_id, "tenant_id")
        if requested != self.target_tenant_id:
            raise TenantAccessDeniedApplicationError(
                "La operación platform no está autorizada para este tenant."
            )
