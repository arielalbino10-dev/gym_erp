from typing import Protocol

from gym_erp_api.modules.identity.domain.platform_mfa.encrypted_secret import EncryptedMfaSecret


class MfaSecretEncryptor(Protocol):
    def encrypt(self, plaintext: bytes) -> EncryptedMfaSecret:
        """Cifra secreto TOTP (AES-GCM autenticado)."""

    def decrypt(self, encrypted: EncryptedMfaSecret) -> bytes:
        """Descifra secreto TOTP."""
