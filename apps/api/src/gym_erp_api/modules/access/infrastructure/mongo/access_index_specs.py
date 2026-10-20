"""Índices platform para access (gym_platform)."""

from __future__ import annotations

from pymongo.asynchronous.collection import AsyncCollection


async def ensure_tenant_memberships_indexes(collection: AsyncCollection) -> None:
    """Unicidad canónica (tenant_id, user_id) — estrategia A H2-C.2."""
    await collection.create_index(
        [("tenant_id", 1), ("user_id", 1)],
        unique=True,
        name="uniq_tenant_user",
    )
    await collection.create_index(
        [("user_id", 1), ("status", 1)],
        name="idx_user_status",
    )
    await collection.create_index(
        [("tenant_id", 1), ("status", 1)],
        name="idx_tenant_status",
    )


async def ensure_access_platform_indexes(
    *,
    memberships: AsyncCollection,
) -> None:
    await ensure_tenant_memberships_indexes(memberships)


def duplicate_key_field(exc: object) -> str | None:
    details = getattr(exc, "details", None) or {}
    key_pattern = details.get("keyPattern") or {}
    if isinstance(key_pattern, dict) and key_pattern:
        return next(iter(key_pattern.keys()), None)
    return None
