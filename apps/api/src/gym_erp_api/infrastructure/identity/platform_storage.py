"""Índices MongoDB identity/MFA en gym_platform (arranque, sin migración automática prod)."""

from __future__ import annotations

from gym_erp_api.infrastructure.mongo.http_security_index_specs import (
    ensure_http_security_indexes,
)
from gym_erp_api.infrastructure.mongo.mongo_csrf_token_repository import (
    HTTP_CSRF_TOKENS_COLLECTION,
)
from gym_erp_api.infrastructure.mongo.mongo_databases import MongoDatabases
from gym_erp_api.infrastructure.mongo.mongo_rate_limit_repository import (
    HTTP_RATE_LIMIT_COLLECTION,
)
from gym_erp_api.modules.identity.infrastructure.mongo.mongo_platform_operator_eligibility_repository import (  # noqa: E501
    PLATFORM_OPERATOR_ELIGIBILITIES_COLLECTION,
)
from gym_erp_api.modules.identity.infrastructure.mongo.platform_auth_continuation_mappers import (
    PLATFORM_AUTH_CONTINUATIONS_COLLECTION,
)
from gym_erp_api.modules.identity.infrastructure.mongo.platform_index_specs import (
    ensure_identity_platform_indexes,
)
from gym_erp_api.modules.identity.infrastructure.mongo.platform_mfa_index_specs import (
    ensure_platform_auth_continuation_indexes,
    ensure_platform_mfa_indexes,
)
from gym_erp_api.modules.identity.infrastructure.mongo.platform_mfa_mappers import (
    PLATFORM_MFA_AUTHORIZATIONS_COLLECTION,
    PLATFORM_MFA_CHALLENGES_COLLECTION,
    PLATFORM_MFA_STEPS_COLLECTION,
    PLATFORM_MFA_TOTP_COLLECTION,
)


async def ensure_platform_identity_storage_indexes(databases: MongoDatabases) -> None:
    platform = databases.platform
    await ensure_identity_platform_indexes(
        identities=platform["user_identities"],
        credentials=platform["user_credentials"],
        sessions=platform["auth_sessions"],
        operator_eligibilities=platform[PLATFORM_OPERATOR_ELIGIBILITIES_COLLECTION],
    )
    await ensure_platform_mfa_indexes(
        totp=platform[PLATFORM_MFA_TOTP_COLLECTION],
        challenges=platform[PLATFORM_MFA_CHALLENGES_COLLECTION],
        steps=platform[PLATFORM_MFA_STEPS_COLLECTION],
        authorizations=platform[PLATFORM_MFA_AUTHORIZATIONS_COLLECTION],
    )
    await ensure_platform_auth_continuation_indexes(
        continuations=platform[PLATFORM_AUTH_CONTINUATIONS_COLLECTION],
    )
    await ensure_http_security_indexes(
        rate_limits=platform[HTTP_RATE_LIMIT_COLLECTION],
        csrf_tokens=platform[HTTP_CSRF_TOKENS_COLLECTION],
    )
