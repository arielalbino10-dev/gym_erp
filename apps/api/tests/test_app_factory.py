from fastapi import FastAPI

from gym_erp_api.core.config import Settings
from gym_erp_api.main import app, create_app


def test_create_app_returns_fastapi_instance():
    settings = Settings(app_env="test", mongodb_uri=None)
    instance = create_app(settings=settings)
    assert isinstance(instance, FastAPI)


def test_create_app_registers_api_v1_routes():
    settings = Settings(app_env="test", mongodb_uri=None)
    instance = create_app(settings=settings)
    paths = set(instance.openapi()["paths"])
    assert "/api/v1/health/live" in paths
    assert "/api/v1/health/ready" in paths


def test_module_level_app_is_fastapi():
    assert isinstance(app, FastAPI)
