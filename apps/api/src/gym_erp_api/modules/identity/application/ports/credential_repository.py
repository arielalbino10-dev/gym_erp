"""Puerto de persistencia de credenciales (hash Argon2id)."""

from datetime import datetime
from typing import Protocol

from gym_erp_api.modules.identity.domain.user_credential import UserCredential


class CredentialRepository(Protocol):
    async def get_by_user_id(self, user_id: str) -> UserCredential | None:
        """Devuelve la credencial del usuario o None."""

    async def insert(self, credential: UserCredential) -> None:
        """Inserta credencial (una por user_id)."""

    async def save(
        self,
        credential: UserCredential,
        *,
        expected_updated_at: datetime,
    ) -> None:
        """Actualiza credencial con concurrencia optimista."""
