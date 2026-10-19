"""Puerto de hashing de contraseñas (ADR-0003)."""

from typing import Protocol


class PasswordHasher(Protocol):
    def hash(self, plaintext: str) -> str:
        """Devuelve hash Argon2id codificado (PHC string)."""

    def verify(self, plaintext: str, stored_hash: str) -> bool:
        """True si la contraseña coincide; False si no. Hashes inválidos lanzan error."""

    def needs_rehash(self, stored_hash: str) -> bool:
        """True si los parámetros del hash están obsoletos respecto a la configuración actual."""
