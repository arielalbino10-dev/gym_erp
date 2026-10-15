"""Política de tenant para operaciones sobre gym_operational."""

from __future__ import annotations

from gym_erp_api.modules.organization.application.errors import (
    TenantNotActiveApplicationError,
    TenantNotFoundApplicationError,
    TenantSuspendedApplicationError,
)
from gym_erp_api.modules.organization.domain.enums import TenantStatus
from gym_erp_api.modules.organization.domain.tenant import Tenant


class TenantOperationalPolicy:
    """Valida que un tenant platform permita mutaciones/lecturas operational."""

    @staticmethod
    def ensure_allows_operational(tenant: Tenant | None) -> Tenant:
        if tenant is None:
            raise TenantNotFoundApplicationError("Tenant no encontrado.")
        if tenant.status is TenantStatus.SUSPENDED:
            raise TenantSuspendedApplicationError(
                "El tenant está suspendido; operación operational rechazada."
            )
        if tenant.status is TenantStatus.PROVISIONING:
            raise TenantNotActiveApplicationError(
                "El tenant aún no está activo; operación operational rechazada."
            )
        if tenant.status is TenantStatus.ACTIVE:
            return tenant
        raise TenantNotActiveApplicationError(
            f"Estado de tenant no permitido para operational: {tenant.status.value!r}."
        )
