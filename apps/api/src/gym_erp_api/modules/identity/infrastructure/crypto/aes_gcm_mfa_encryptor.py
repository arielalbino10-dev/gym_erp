"""Cifrado autenticado AES-256-GCM para secretos MFA."""

from __future__ import annotations

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from gym_erp_api.modules.identity.domain.platform_mfa.encrypted_secret import EncryptedMfaSecret


class AesGcmMfaSecretEncryptor:
    """Formato: version(1 byte) | nonce(12) | ciphertext+tag."""

    def __init__(self, *, key: bytes, key_version: int = 1) -> None:
        if len(key) != 32:
            raise ValueError("La clave MFA debe tener 32 bytes.")
        if key_version < 1:
            raise ValueError("key_version inválido.")
        self._key_version = key_version
        self._aes = AESGCM(key)

    @property
    def key_version(self) -> int:
        return self._key_version

    def encrypt(self, plaintext: bytes) -> EncryptedMfaSecret:
        if not plaintext:
            raise ValueError("plaintext vacío.")
        nonce = os.urandom(12)
        ct = self._aes.encrypt(nonce, plaintext, associated_data=None)
        blob = bytes([self._key_version]) + nonce + ct
        return EncryptedMfaSecret(key_version=self._key_version, ciphertext=blob)

    def decrypt(self, encrypted: EncryptedMfaSecret) -> bytes:
        blob = encrypted.ciphertext
        if len(blob) < 1 + 12 + 16:
            raise ValueError("ciphertext demasiado corto.")
        version = blob[0]
        if version != self._key_version:
            raise ValueError("Versión de clave MFA no soportada.")
        nonce = blob[1:13]
        ct = blob[13:]
        return self._aes.decrypt(nonce, ct, associated_data=None)
