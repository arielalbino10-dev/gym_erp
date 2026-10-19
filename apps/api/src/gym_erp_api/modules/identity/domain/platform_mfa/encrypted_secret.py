"""Secreto TOTP cifrado en reposo (sin plaintext en dominio)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class EncryptedMfaSecret:
    key_version: int
    ciphertext: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if self.key_version < 1:
            raise ValueError("key_version inválido.")
        if not isinstance(self.ciphertext, bytes) or not self.ciphertext:
            raise ValueError("ciphertext inválido.")
