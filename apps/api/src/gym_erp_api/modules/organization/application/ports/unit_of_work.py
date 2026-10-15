"""Puerto mínimo de Unit of Work (sin PyMongo en capa de aplicación)."""

from typing import Protocol, Self, runtime_checkable


@runtime_checkable
class OrganizationUnitOfWork(Protocol):
    """Coordina una unidad de trabajo transaccional; expone sesión opaca a repositorios."""

    @property
    def session(self) -> object:
        """Handle de sesión para kwargs ``session=`` en repositorios participantes."""
        ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None: ...
