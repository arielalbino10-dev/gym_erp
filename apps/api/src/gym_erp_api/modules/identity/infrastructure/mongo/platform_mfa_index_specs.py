from pymongo.asynchronous.collection import AsyncCollection


async def ensure_platform_auth_continuation_indexes(
    continuations: AsyncCollection,
) -> None:
    await continuations.create_index("token_hash", unique=True, name="uniq_token_hash")
    await continuations.create_index("user_id", name="idx_user_id")
    await continuations.create_index(
        "expires_at",
        expireAfterSeconds=0,
        name="ttl_continuation_cleanup",
    )


async def ensure_platform_mfa_indexes(
    *,
    totp: AsyncCollection,
    challenges: AsyncCollection,
    steps: AsyncCollection,
    authorizations: AsyncCollection,
) -> None:
    await totp.create_index("user_id", unique=True, name="uniq_user_id")
    await challenges.create_index("user_id", name="idx_user_id")
    await challenges.create_index("expires_at", expireAfterSeconds=0, name="ttl_challenge_cleanup")
    await steps.create_index("expires_at", expireAfterSeconds=86400, name="ttl_step_cleanup")
    await authorizations.create_index("authorization_id", unique=True, name="uniq_authorization")
    await authorizations.create_index(
        "expires_at",
        expireAfterSeconds=0,
        name="ttl_authorization_cleanup",
    )
