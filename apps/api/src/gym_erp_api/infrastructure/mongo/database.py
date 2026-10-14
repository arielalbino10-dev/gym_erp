from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError

from gym_erp_api.core.config import Settings


def create_mongo_client(settings: Settings) -> AsyncMongoClient | None:
    if settings.mongodb_uri is None:
        return None
    uri = settings.mongodb_uri.get_secret_value().strip()
    if not uri:
        return None
    return AsyncMongoClient(
        uri,
        serverSelectionTimeoutMS=settings.mongodb_ping_timeout_ms,
    )


async def ping_mongodb(client: AsyncMongoClient | None, timeout_ms: int) -> bool:
    if client is None:
        return False
    try:
        await client.admin.command("ping")
        return True
    except PyMongoError:
        return False
