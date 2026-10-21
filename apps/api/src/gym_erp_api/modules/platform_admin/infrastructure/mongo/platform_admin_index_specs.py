"""Índices MongoDB — administración platform."""

from __future__ import annotations

from pymongo.asynchronous.collection import AsyncCollection


async def ensure_platform_role_assignment_indexes(collection: AsyncCollection) -> None:
    await collection.create_index("roles")
    await collection.create_index("updated_at")


async def ensure_platform_audit_event_indexes(collection: AsyncCollection) -> None:
    await collection.create_index([("recorded_at", -1)])
    await collection.create_index("actor_user_id")
    await collection.create_index([("resource_type", 1), ("resource_id", 1)])
