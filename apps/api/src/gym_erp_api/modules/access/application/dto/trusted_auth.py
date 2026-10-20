"""Contexto autenticado confiable (post ResolveSession; sin datos del navegador como autoridad)."""

from __future__ import annotations

from dataclasses import dataclass

from gym_erp_api.modules.organization.domain.validators import require_uuid_v4


@dataclass(frozen=True, slots=True)
class TrustedGymAuthContext:
    """Identidad ya validada por identity; tenant_id es selección a verificar en access."""

    user_id: str
    selected_tenant_id: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "user_id", require_uuid_v4(self.user_id, "user_id"))
        if self.selected_tenant_id is not None:
            object.__setattr__(
                self,
                "selected_tenant_id",
                require_uuid_v4(self.selected_tenant_id, "tenant_id"),
            )
