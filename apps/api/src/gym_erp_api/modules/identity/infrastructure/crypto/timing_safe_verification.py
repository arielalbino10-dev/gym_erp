"""Hash Argon2id ficticio para equalización de tiempo (cuenta inexistente)."""

from __future__ import annotations

from functools import lru_cache

from gym_erp_api.modules.identity.infrastructure.crypto.argon2_password_hasher import (
    Argon2PasswordHasher,
)

_DUMMY_PLAINTEXT = "gym-erp-timing-equalization-dummy-12"


@lru_cache(maxsize=1)
def dummy_credential_hash_for_timing() -> str:
    """Hash estable en proceso; nunca se persiste en MongoDB."""
    return Argon2PasswordHasher().hash(_DUMMY_PLAINTEXT)


async def verify_password_async(
    hasher: Argon2PasswordHasher,
    plaintext: str,
    stored_hash: str,
) -> bool:
    import asyncio

    return await asyncio.to_thread(hasher.verify, plaintext, stored_hash)
