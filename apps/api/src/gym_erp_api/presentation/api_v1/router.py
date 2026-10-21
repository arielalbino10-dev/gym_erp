from fastapi import APIRouter

from gym_erp_api.presentation.api_v1.gym.auth import router as gym_auth_router
from gym_erp_api.presentation.api_v1.gym.branches import router as gym_branches_router
from gym_erp_api.presentation.api_v1.health import router as health_router
from gym_erp_api.presentation.api_v1.platform.auth import router as platform_auth_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(gym_auth_router, prefix="/gym")
api_v1_router.include_router(gym_branches_router, prefix="/gym")
api_v1_router.include_router(platform_auth_router, prefix="/platform")
