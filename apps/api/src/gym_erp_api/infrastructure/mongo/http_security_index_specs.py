from pymongo.asynchronous.collection import AsyncCollection


async def ensure_http_security_indexes(
    *,
    rate_limits: AsyncCollection,
    csrf_tokens: AsyncCollection,
) -> None:
    await rate_limits.create_index("expires_at", expireAfterSeconds=0, name="ttl_rate_limit")
    await csrf_tokens.create_index("expires_at", expireAfterSeconds=0, name="ttl_csrf")
