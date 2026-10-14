from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from gym_erp_api.core.config import get_settings
from gym_erp_api.infrastructure.mongo.database import ping_mongodb

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def health_live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready(request: Request) -> JSONResponse:
    settings = get_settings()
    client = getattr(request.app.state, "mongo_client", None)
    timeout_ms = settings.mongodb_ping_timeout_ms
    if await ping_mongodb(client, timeout_ms):
        return JSONResponse(status_code=200, content={"status": "ready"})
    return JSONResponse(status_code=503, content={"status": "not_ready"})
