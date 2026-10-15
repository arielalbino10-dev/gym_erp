from datetime import UTC
from typing import Any

from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError

from gym_erp_api.core.config import Settings


def mongo_client_options(*, server_selection_timeout_ms: int | None = None) -> dict[str, Any]:
    """Opciones compartidas para decodificar BSON datetime como UTC aware (Organization)."""
    options: dict[str, Any] = {
        "tz_aware": True,
        "tzinfo": UTC,
    }
    if server_selection_timeout_ms is not None:
        options["serverSelectionTimeoutMS"] = server_selection_timeout_ms
    return options


def create_mongo_client(settings: Settings) -> AsyncMongoClient | None:
    if settings.mongodb_uri is None:
        return None
    uri = settings.mongodb_uri.get_secret_value().strip()
    if not uri:
        return None
    return AsyncMongoClient(
        uri,
        **mongo_client_options(server_selection_timeout_ms=settings.mongodb_ping_timeout_ms),
    )


async def ping_mongodb(client: AsyncMongoClient | None, timeout_ms: int) -> bool:
    if client is None:
        return False
    try:
        await client.admin.command("ping")
        return True
    except PyMongoError:
        return False
