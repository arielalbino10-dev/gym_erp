from typing import Protocol


class TotpService(Protocol):
    def generate_secret(self) -> bytes:
        """Genera secreto TOTP (20 bytes típico)."""

    def provisioning_uri(self, *, secret: bytes, account_name: str, issuer: str) -> str:
        """URI otpauth para autenticador (sin loguear en producción)."""

    def verify(
        self,
        *,
        secret: bytes,
        code: str,
        for_time: int | None = None,
    ) -> tuple[bool, int]:
        """Devuelve (válido, time_counter usado). Comparación segura vía librería."""
