"""Puerto de persistencia de UserIdentity (implementación Mongo en H2-B.3)."""

from typing import Protocol

from gym_erp_api.modules.identity.domain.user_identity import UserIdentity


class IdentityRepository(Protocol):
    async def get_by_email_normalized(self, email_normalized: str) -> UserIdentity | None:
        """Busca identidad por email normalizado (único lógico)."""

    async def get_by_id(self, user_id: str) -> UserIdentity | None:
        """Busca identidad por user_id."""

    async def save(self, identity: UserIdentity) -> None:
        """Inserta o actualiza identidad."""
