from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gym_erp_api.core.config import Settings, get_settings
from gym_erp_api.infrastructure.access.access_container import build_access_infrastructure
from gym_erp_api.infrastructure.http.http_security_container import (
    build_http_security_infrastructure,
)
from gym_erp_api.infrastructure.identity.identity_container import build_identity_infrastructure
from gym_erp_api.infrastructure.identity.platform_storage import (
    ensure_platform_identity_storage_indexes,
)
from gym_erp_api.infrastructure.mongo.database import create_mongo_client
from gym_erp_api.infrastructure.mongo.mongo_databases import MongoDatabases
from gym_erp_api.infrastructure.platform_admin.platform_admin_container import (
    build_platform_admin_infrastructure,
)
from gym_erp_api.modules.identity.application.errors import PlatformMfaConfigurationError
from gym_erp_api.presentation.api_v1.router import api_v1_router
from gym_erp_api.presentation.http_security.handlers import (
    register_http_security_exception_handlers,
)
from gym_erp_api.presentation.http_security.middleware import SecurityHeadersMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    client = create_mongo_client(settings)
    app.state.mongo_client = client
    app.state.mongo_databases = MongoDatabases(client, settings) if client is not None else None
    app.state.identity_infrastructure = None
    app.state.access_infrastructure = None
    app.state.platform_admin_infrastructure = None
    app.state.http_rate_limiter = None
    app.state.csrf_protection = None
    if app.state.mongo_databases is not None:
        await ensure_platform_identity_storage_indexes(app.state.mongo_databases)
        http_security = build_http_security_infrastructure(app.state.mongo_databases, settings)
        app.state.http_rate_limiter = http_security.rate_limiter
        app.state.csrf_protection = http_security.csrf_protection
        try:
            identity = build_identity_infrastructure(
                app.state.mongo_databases,
                settings,
            )
            app.state.identity_infrastructure = identity
            app.state.access_infrastructure = build_access_infrastructure(
                app.state.mongo_databases,
                session_repository=identity.auth_session_repository,
            )
            app.state.platform_admin_infrastructure = build_platform_admin_infrastructure(
                app.state.mongo_databases.platform,
            )
        except PlatformMfaConfigurationError:
            app.state.identity_infrastructure = None
            app.state.access_infrastructure = None
            app.state.platform_admin_infrastructure = None
    try:
        yield
    finally:
        if client is not None:
            await client.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    app = FastAPI(
        title="Gym ERP API",
        version="0.1.0",
        docs_url="/docs" if resolved.app_env == "development" else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.settings = resolved
    register_http_security_exception_handlers(app)
    app.add_middleware(SecurityHeadersMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Accept", "Content-Type", "Origin", "X-CSRF-Token"],
        expose_headers=["X-CSRF-Token"],
    )

    app.include_router(api_v1_router)
    return app


app = create_app()
