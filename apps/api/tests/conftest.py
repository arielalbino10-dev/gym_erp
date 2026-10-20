import pytest

from gym_erp_api.core.config import Settings, get_settings
from gym_erp_api.main import create_app


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def app_no_mongo(monkeypatch):
    monkeypatch.delenv("MONGODB_URI", raising=False)
    settings = Settings(app_env="test", mongodb_uri=None)
    return create_app(settings=settings)
