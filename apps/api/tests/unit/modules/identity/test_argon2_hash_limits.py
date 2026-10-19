import pytest
from argon2 import PasswordHasher as LibHasher
from argon2 import Type

from gym_erp_api.modules.identity.infrastructure.crypto.argon2_config import Argon2PasswordConfig
from gym_erp_api.modules.identity.infrastructure.crypto.argon2_password_hasher import (
    Argon2PasswordHasher,
    InvalidStoredPasswordHashError,
)


def test_verify_rejects_extreme_memory_cost_in_stored_hash():
    heavy = LibHasher(
        time_cost=3,
        memory_cost=512 * 1024,
        parallelism=1,
        type=Type.ID,
    )
    stored = heavy.hash("correct-horse-battery-staple-12")
    hasher = Argon2PasswordHasher(
        Argon2PasswordConfig(max_memory_cost_kib=262144),
    )
    with pytest.raises(InvalidStoredPasswordHashError):
        hasher.verify("correct-horse-battery-staple-12", stored)
