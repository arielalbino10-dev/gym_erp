"""Utilidades compartidas para pruebas HTTP auth + integración Mongo."""

from __future__ import annotations

import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from gym_erp_api.core.config import Settings
from gym_erp_api.infrastructure.access.access_container import (
    AccessInfrastructure,
    build_access_infrastructure,
)
from gym_erp_api.infrastructure.http.http_security_container import HttpSecurityInfrastructure
from gym_erp_api.infrastructure.identity.identity_container import IdentityInfrastructure
from gym_erp_api.infrastructure.mongo.mongo_csrf_token_repository import MongoCsrfTokenRepository
from gym_erp_api.infrastructure.mongo.mongo_databases import MongoDatabases
from gym_erp_api.infrastructure.mongo.mongo_rate_limit_repository import MongoRateLimitRepository
from gym_erp_api.main import create_app
from gym_erp_api.modules.identity.infrastructure.mongo.mongo_auth_session_repository import (
    MongoAuthSessionRepository,
)
from gym_erp_api.modules.identity.infrastructure.mongo.mongo_credential_repository import (
    MongoCredentialRepository,
)
from gym_erp_api.modules.identity.infrastructure.mongo.mongo_identity_repository import (
    MongoIdentityRepository,
)
from gym_erp_api.modules.identity.infrastructure.mongo.mongo_platform_mfa_repositories import (
    MongoPlatformMfaChallengeRepository,
    MongoPlatformMfaSessionAuthorizationRepository,
    MongoPlatformMfaStepConsumptionRepository,
    MongoPlatformTotpEnrollmentRepository,
)
from gym_erp_api.presentation.http_security.csrf import CsrfProtectionService
from gym_erp_api.presentation.http_security.rate_limit import HttpRateLimiter
from tests.support.ephemeral_identity_infrastructure import build_ephemeral_identity_infrastructure
from tests.support.integration_environment import EXPECTED_PLATFORM_DB
from tests.support.mfa_test_crypto import TEST_MFA_AES256_KEY

AUTH_HTTP_ORIGIN = "http://127.0.0.1:5173"


def integration_settings_with_mfa(base: Settings) -> Settings:
    import base64

    key_b64 = base64.b64encode(TEST_MFA_AES256_KEY).decode()
    return base.model_copy(update={"platform_mfa_encryption_key": SecretStr(key_b64)})


def build_auth_http_identity_stack(
    *,
    settings: Settings,
    mongo_identity_repository: MongoIdentityRepository,
    mongo_credential_repository: MongoCredentialRepository,
    mongo_auth_session_repository: MongoAuthSessionRepository,
    mongo_platform_totp_enrollment_repository: MongoPlatformTotpEnrollmentRepository,
    mongo_platform_mfa_challenge_repository: MongoPlatformMfaChallengeRepository,
    mongo_platform_mfa_step_repository: MongoPlatformMfaStepConsumptionRepository,
    mongo_platform_mfa_session_authorization_repository: (
        MongoPlatformMfaSessionAuthorizationRepository
    ),
    access_memberships_collection: Any,
    access_tenants_collection: Any,
) -> tuple[
    MongoDatabases,
    IdentityInfrastructure,
    Any,
    HttpSecurityInfrastructure,
    AccessInfrastructure,
]:
    mongo_client = mongo_identity_repository._collection.database.client  # noqa: SLF001
    databases = MongoDatabases(mongo_client, settings)
    db = mongo_client[EXPECTED_PLATFORM_DB]
    suffix = secrets.token_hex(6)
    continuations = db[f"gym_erp_id_authcont_{suffix}"]
    operator_eligibility = db[f"gym_erp_id_popelig_{suffix}"]
    rate_limits = db[f"gym_erp_http_rl_{suffix}"]
    csrf_tokens = db[f"gym_erp_http_csrf_{suffix}"]
    rate_repo = MongoRateLimitRepository(rate_limits)
    csrf_repo = MongoCsrfTokenRepository(csrf_tokens)
    http_security = HttpSecurityInfrastructure(
        rate_limit_repository=rate_repo,
        csrf_token_repository=csrf_repo,
        rate_limiter=HttpRateLimiter(repository=rate_repo, settings=settings),
        csrf_protection=CsrfProtectionService(repository=csrf_repo),
    )
    infra = build_ephemeral_identity_infrastructure(
        settings=settings,
        identities=mongo_identity_repository._collection,  # noqa: SLF001
        credentials=mongo_credential_repository._collection,  # noqa: SLF001
        sessions=mongo_auth_session_repository._collection,  # noqa: SLF001
        continuations=continuations,
        mfa_totp=mongo_platform_totp_enrollment_repository._collection,  # noqa: SLF001
        mfa_challenges=mongo_platform_mfa_challenge_repository._collection,  # noqa: SLF001
        mfa_steps=mongo_platform_mfa_step_repository._collection,  # noqa: SLF001
        mfa_authz=mongo_platform_mfa_session_authorization_repository._collection,  # noqa: SLF001
        operator_eligibility=operator_eligibility,
    )
    access = build_access_infrastructure(
        databases,
        session_repository=infra.auth_session_repository,
        memberships_collection=access_memberships_collection,
        tenants_collection=access_tenants_collection,
    )
    return databases, infra, operator_eligibility, http_security, access


@asynccontextmanager
async def mounted_auth_http_client(
    *,
    settings: Settings,
    identity_infrastructure: IdentityInfrastructure | None,
    databases: MongoDatabases | None = None,
    http_security: HttpSecurityInfrastructure | None = None,
    access_infrastructure: AccessInfrastructure | None = None,
    include_security_probe: bool = False,
) -> AsyncIterator[AsyncClient]:
    app = create_app(settings=settings)
    if include_security_probe:
        from tests.support.security_probe_router import (
            gym_auth_probe_router,
        )
        from tests.support.security_probe_router import (
            router as security_probe_router,
        )

        app.include_router(security_probe_router, prefix="/api/v1")
        app.include_router(gym_auth_probe_router, prefix="/api/v1")
    if http_security is None and databases is not None:
        raise ValueError("Proveer http_security efímero desde build_auth_http_identity_stack.")
    app.state.identity_infrastructure = identity_infrastructure
    app.state.access_infrastructure = access_infrastructure
    if http_security is not None:
        app.state.http_rate_limiter = http_security.rate_limiter
        app.state.csrf_protection = http_security.csrf_protection
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


def csrf_headers_and_cookies(
    *,
    token: str,
    cookie_name: str,
    origin: str = AUTH_HTTP_ORIGIN,
) -> tuple[dict[str, str], dict[str, str]]:
    from gym_erp_api.modules.identity.application.security.http_auth_contracts import CsrfPolicy

    policy = CsrfPolicy()
    headers = {"Origin": origin, policy.header_name: token}
    cookies = {cookie_name: token}
    return headers, cookies


async def revoke_platform_operator_eligibility(
    operator_eligibility_collection: Any,
    *,
    user_id: str,
) -> None:
    from gym_erp_api.modules.identity.infrastructure.mongo.mongo_platform_operator_eligibility_repository import (  # noqa: E501
        MongoPlatformOperatorEligibilityRepository,
    )

    repo = MongoPlatformOperatorEligibilityRepository(operator_eligibility_collection)
    await repo.revoke_eligibility(user_id=user_id)


async def grant_platform_operator_eligibility(
    operator_eligibility_collection: Any,
    *,
    user_id: str,
    granted_at: Any,
) -> None:
    from gym_erp_api.modules.identity.infrastructure.mongo.mongo_platform_operator_eligibility_repository import (  # noqa: E501
        MongoPlatformOperatorEligibilityRepository,
    )

    repo = MongoPlatformOperatorEligibilityRepository(operator_eligibility_collection)
    await repo.grant_eligibility(user_id=user_id, granted_at=granted_at)
