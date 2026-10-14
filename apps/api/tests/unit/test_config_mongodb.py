import pytest
from pydantic import ValidationError

from gym_erp_api.core.config import Settings


def test_default_database_names_are_valid():
    settings = Settings(app_env="test", mongodb_uri=None)
    assert settings.mongodb_platform_db == "gym_platform"
    assert settings.mongodb_operational_db == "gym_operational"


def test_rejects_empty_database_name():
    with pytest.raises(ValidationError) as exc:
        Settings(app_env="test", mongodb_uri=None, mongodb_platform_db="   ")
    assert "mongodb" in str(exc.value).lower() or "vacío" in str(exc.value).lower()
    assert "mongodb://" not in str(exc.value)


def test_rejects_identical_database_names():
    with pytest.raises(ValidationError) as exc:
        Settings(
            app_env="test",
            mongodb_uri=None,
            mongodb_platform_db="same_db",
            mongodb_operational_db="same_db",
        )
    assert "distintos" in str(exc.value)
    assert "mongodb://" not in str(exc.value)


def test_rejects_reserved_database_name():
    with pytest.raises(ValidationError):
        Settings(app_env="test", mongodb_uri=None, mongodb_operational_db="admin")
