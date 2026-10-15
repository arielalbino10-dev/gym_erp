"""Factory de Unit of Work (sesión transaccional opaca)."""

from typing import Protocol

from gym_erp_api.modules.organization.application.ports.unit_of_work import OrganizationUnitOfWork


class OrganizationUnitOfWorkFactory(Protocol):
    def __call__(self) -> OrganizationUnitOfWork:
        """Nueva instancia por invocación (no reutilizable)."""
        ...
