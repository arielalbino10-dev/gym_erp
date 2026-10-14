from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from gym_erp_api.core.config import Settings
from gym_erp_api.main import create_app


@pytest.fixture
def app_no_mongo(monkeypatch):
    monkeypatch.delenv("MONGODB_URI", raising=False)
    settings = Settings(app_env="test", mongodb_uri=None)
    return create_app(settings=settings)


@pytest.fixture
def app_empty_mongo_uri(monkeypatch):
    monkeypatch.delenv("MONGODB_URI", raising=False)
    settings = Settings(app_env="test", mongodb_uri=SecretStr(""))
    return create_app(settings=settings)


@pytest.fixture
def app_with_mongo_uri_configured(monkeypatch):
    """URI ficticia: el ping se simula; no requiere MongoDB en ejecución."""
    monkeypatch.delenv("MONGODB_URI", raising=False)
    settings = Settings(
        app_env="test",
        mongodb_uri=SecretStr(
            "mongodb://127.0.0.1:27017/gym_erp_integration_guard_test?replicaSet=rs0"
        ),
    )
    return create_app(settings=settings)


@pytest.mark.asyncio
async def test_health_live_returns_200(app_no_mongo):
    transport = ASGITransport(app=app_no_mongo)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_ready_returns_503_without_mongo_uri(app_no_mongo):
    transport = ASGITransport(app=app_no_mongo)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}


@pytest.mark.asyncio
async def test_health_ready_returns_503_with_empty_mongo_uri(app_empty_mongo_uri):
    transport = ASGITransport(app=app_empty_mongo_uri)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}


@pytest.mark.asyncio
@patch(
    "gym_erp_api.presentation.api_v1.health.ping_mongodb",
    new_callable=AsyncMock,
)
async def test_health_ready_returns_200_when_ping_succeeds(
    mock_ping, app_with_mongo_uri_configured
):
    mock_ping.return_value = True
    transport = ASGITransport(app=app_with_mongo_uri_configured)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
    mock_ping.assert_awaited_once()


@pytest.mark.asyncio
@patch(
    "gym_erp_api.presentation.api_v1.health.ping_mongodb",
    new_callable=AsyncMock,
)
async def test_health_ready_returns_503_when_ping_fails(mock_ping, app_with_mongo_uri_configured):
    mock_ping.return_value = False
    transport = ASGITransport(app=app_with_mongo_uri_configured)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}


@pytest.mark.asyncio
async def test_health_live_response_has_no_sensitive_fields(app_no_mongo):
    transport = ASGITransport(app=app_no_mongo)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health/live")
    body = response.text.lower()
    for forbidden in ("mongodb", "password", "secret", "uri"):
        assert forbidden not in body


@pytest.mark.asyncio
@patch(
    "gym_erp_api.presentation.api_v1.health.ping_mongodb",
    new_callable=AsyncMock,
)
async def test_health_ready_response_has_no_sensitive_fields(
    mock_ping, app_with_mongo_uri_configured
):
    mock_ping.return_value = True
    transport = ASGITransport(app=app_with_mongo_uri_configured)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health/ready")
    body = response.text.lower()
    for forbidden in ("mongodb", "password", "secret", "uri"):
        assert forbidden not in body
