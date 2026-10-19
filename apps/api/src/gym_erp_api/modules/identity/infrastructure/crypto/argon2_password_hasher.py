"""Implementación Argon2id del puerto PasswordHasher."""

from __future__ import annotations

from argon2 import PasswordHasher as _LibHasher
from argon2 import Type, extract_parameters
from argon2.exceptions import InvalidHash, VerificationError, VerifyMismatchError

from gym_erp_api.modules.identity.infrastructure.crypto.argon2_config import Argon2PasswordConfig


class InvalidStoredPasswordHashError(ValueError):
    """Hash almacenado corrupto o con tipo distinto de Argon2id."""


_ARGON2ID_PREFIX = "$argon2id$"


class Argon2PasswordHasher:
    """Hashing de contraseñas con Argon2id exclusivamente (ADR-0003)."""

    def __init__(self, config: Argon2PasswordConfig | None = None) -> None:
        cfg = config or Argon2PasswordConfig()
        self._config = cfg
        self._hasher = _LibHasher(
            time_cost=cfg.time_cost,
            memory_cost=cfg.memory_cost_kib,
            parallelism=cfg.parallelism,
            hash_len=cfg.hash_len,
            salt_len=cfg.salt_len,
            type=Type.ID,
        )

    @property
    def config(self) -> Argon2PasswordConfig:
        return self._config

    def _require_argon2id_hash(self, stored_hash: str) -> None:
        if not stored_hash.startswith(_ARGON2ID_PREFIX):
            raise InvalidStoredPasswordHashError("Solo se aceptan hashes Argon2id.")
        try:
            params = extract_parameters(stored_hash)
        except InvalidHash as exc:
            raise InvalidStoredPasswordHashError(
                "Hash almacenado no válido para Argon2id."
            ) from exc
        if params.type is not Type.ID:
            raise InvalidStoredPasswordHashError("Solo se aceptan hashes Argon2id.")
        cfg = self._config
        if (
            params.time_cost > cfg.max_time_cost
            or params.memory_cost > cfg.max_memory_cost_kib
            or params.parallelism > cfg.max_parallelism
        ):
            raise InvalidStoredPasswordHashError("Parámetros Argon2id fuera de límites permitidos.")

    def hash(self, plaintext: str) -> str:
        if not isinstance(plaintext, str) or not plaintext:
            raise ValueError("La contraseña no puede estar vacía.")
        return self._hasher.hash(plaintext)

    def verify(self, plaintext: str, stored_hash: str) -> bool:
        if not isinstance(plaintext, str) or not isinstance(stored_hash, str):
            raise InvalidStoredPasswordHashError("Entrada de verificación inválida.")
        if not stored_hash.strip():
            raise InvalidStoredPasswordHashError("Hash almacenado vacío.")
        self._require_argon2id_hash(stored_hash)
        try:
            return self._hasher.verify(stored_hash, plaintext)
        except VerifyMismatchError:
            return False
        except (InvalidHash, VerificationError) as exc:
            raise InvalidStoredPasswordHashError(
                "Hash almacenado no válido para Argon2id."
            ) from exc

    def needs_rehash(self, stored_hash: str) -> bool:
        if not isinstance(stored_hash, str) or not stored_hash.strip():
            raise InvalidStoredPasswordHashError("Hash almacenado vacío.")
        self._require_argon2id_hash(stored_hash)
        try:
            return self._hasher.check_needs_rehash(stored_hash)
        except InvalidHash as exc:
            raise InvalidStoredPasswordHashError(
                "Hash almacenado no válido para Argon2id."
            ) from exc
