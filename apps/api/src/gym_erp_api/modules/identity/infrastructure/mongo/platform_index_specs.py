"""Índices platform para identity (gym_platform)."""

from __future__ import annotations

from typing import Any

from pymongo.asynchronous.collection import AsyncCollection


async def ensure_user_identities_indexes(collection: AsyncCollection) -> None:
    await collection.create_index("email_normalized", unique=True, name="uniq_email_normalized")


async def ensure_user_credentials_indexes(collection: AsyncCollection) -> None:
    await collection.create_index("user_id", unique=True, name="uniq_user_id")


async def ensure_auth_sessions_indexes(collection: AsyncCollection) -> None:
    await collection.create_index("token_hash", unique=True, name="uniq_token_hash")
    await collection.create_index(
        [("user_id", 1), ("session_kind", 1)],
        name="idx_user_kind",
    )
    await collection.create_index(
        "expires_at",
        expireAfterSeconds=0,
        name="ttl_expires_at_cleanup",
    )


async def ensure_identity_platform_indexes(
    *,
    identities: AsyncCollection,
    credentials: AsyncCollection,
    sessions: AsyncCollection,
) -> None:
    await ensure_user_identities_indexes(identities)
    await ensure_user_credentials_indexes(credentials)
    await ensure_auth_sessions_indexes(sessions)


def duplicate_key_field(exc: Any) -> str | None:
    details = getattr(exc, "details", None) or {}
    key_pattern = details.get("keyPattern") or {}
    if isinstance(key_pattern, dict) and key_pattern:
        return next(iter(key_pattern.keys()), None)
    return None
