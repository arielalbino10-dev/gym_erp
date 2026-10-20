"""Composición de servicios HTTP security (gym_platform)."""

from __future__ import annotations

from dataclasses import dataclass

from gym_erp_api.core.config import Settings
from gym_erp_api.infrastructure.mongo.mongo_csrf_token_repository import (
    HTTP_CSRF_TOKENS_COLLECTION,
    MongoCsrfTokenRepository,
)
from gym_erp_api.infrastructure.mongo.mongo_databases import MongoDatabases
from gym_erp_api.infrastructure.mongo.mongo_rate_limit_repository import (
    HTTP_RATE_LIMIT_COLLECTION,
    MongoRateLimitRepository,
)
from gym_erp_api.presentation.http_security.csrf import CsrfProtectionService
from gym_erp_api.presentation.http_security.rate_limit import HttpRateLimiter


@dataclass(frozen=True, slots=True)
class HttpSecurityInfrastructure:
    rate_limit_repository: MongoRateLimitRepository
    csrf_token_repository: MongoCsrfTokenRepository
    rate_limiter: HttpRateLimiter
    csrf_protection: CsrfProtectionService


def build_http_security_infrastructure(
    databases: MongoDatabases,
    settings: Settings,
) -> HttpSecurityInfrastructure:
    platform = databases.platform
    rate_repo = MongoRateLimitRepository(platform[HTTP_RATE_LIMIT_COLLECTION])
    csrf_repo = MongoCsrfTokenRepository(platform[HTTP_CSRF_TOKENS_COLLECTION])
    return HttpSecurityInfrastructure(
        rate_limit_repository=rate_repo,
        csrf_token_repository=csrf_repo,
        rate_limiter=HttpRateLimiter(repository=rate_repo, settings=settings),
        csrf_protection=CsrfProtectionService(repository=csrf_repo),
    )
