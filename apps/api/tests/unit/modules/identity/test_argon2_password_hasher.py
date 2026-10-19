import pytest
from argon2 import PasswordHasher as LibHasher
from argon2 import Type

from gym_erp_api.modules.identity.infrastructure.crypto.argon2_config import Argon2PasswordConfig
from gym_erp_api.modules.identity.infrastructure.crypto.argon2_password_hasher import (
    Argon2PasswordHasher,
    InvalidStoredPasswordHashError,
)


def test_hash_produces_argon2id_phc_string():
    hasher = Argon2PasswordHasher()
    stored = hasher.hash("correct-horse-battery-staple-12")
    assert stored.startswith("$argon2id$")


def test_verify_success():
    hasher = Argon2PasswordHasher()
    stored = hasher.hash("correct-horse-battery-staple-12")
    assert hasher.verify("correct-horse-battery-staple-12", stored) is True


def test_verify_failure_returns_false():
    hasher = Argon2PasswordHasher()
    stored = hasher.hash("correct-horse-battery-staple-12")
    assert hasher.verify("wrong-secret-value", stored) is False


def test_verify_corrupt_hash_raises():
    hasher = Argon2PasswordHasher()
    with pytest.raises(InvalidStoredPasswordHashError):
        hasher.verify("any", "not-a-valid-phc-hash")


def test_verify_wrong_algorithm_raises():
    legacy = LibHasher(type=Type.I)
    stored = legacy.hash("correct-horse-battery-staple-12")
    hasher = Argon2PasswordHasher()
    with pytest.raises(InvalidStoredPasswordHashError):
        hasher.verify("correct-horse-battery-staple-12", stored)


def test_needs_rehash_when_parameters_outdated():
    old_cfg = Argon2PasswordConfig(time_cost=2, memory_cost_kib=8192, parallelism=1)
    old_hasher = Argon2PasswordHasher(old_cfg)
    stored = old_hasher.hash("correct-horse-battery-staple-12")
    current = Argon2PasswordHasher()
    assert current.needs_rehash(stored) is True


def test_needs_rehash_false_for_fresh_hash():
    hasher = Argon2PasswordHasher()
    stored = hasher.hash("correct-horse-battery-staple-12")
    assert hasher.needs_rehash(stored) is False


def test_argon2_config_defaults_match_documentation():
    cfg = Argon2PasswordConfig()
    assert cfg.time_cost == 3
    assert cfg.memory_cost_kib == 65536
    assert cfg.parallelism == 4
    assert cfg.hash_len == 32
    assert cfg.salt_len == 16


def test_hash_rejects_empty_password():
    hasher = Argon2PasswordHasher()
    with pytest.raises(ValueError):
        hasher.hash("")
