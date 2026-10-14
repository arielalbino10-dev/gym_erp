from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gym_erp_api.core.config import Settings, get_settings
from gym_erp_api.infrastructure.mongo.database import create_mongo_client
from gym_erp_api.infrastructure.mongo.mongo_databases import MongoDatabases
from gym_erp_api.presentation.api_v1.router import api_v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    client = create_mongo_client(settings)
    app.state.mongo_client = client
    app.state.mongo_databases = MongoDatabases(client, settings) if client is not None else None
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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(api_v1_router)
    return app


app = create_app()
