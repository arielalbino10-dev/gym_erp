import pytest
from httpx import ASGITransport, AsyncClient

from gym_erp_api.core.config import Settings
from gym_erp_api.main import create_app

pytestmark = pytest.mark.integration


@pytest.fixture
def app_integration(integration_settings: Settings):
    return create_app(settings=integration_settings)


@pytest.mark.asyncio
async def test_health_ready_with_real_mongodb(app_integration):
    async with app_integration.router.lifespan_context(app_integration):
        transport = ASGITransport(app=app_integration)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
    body_lower = response.text.lower()
    assert "password" not in body_lower
    assert "secret" not in body_lower
