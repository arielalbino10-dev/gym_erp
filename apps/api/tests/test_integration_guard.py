"""Pruebas unitarias de la guardia de URI de integración (sin MongoDB)."""

import pytest

from tests.support.mongodb_uri_guard import validate_integration_mongodb_uri


def test_accepts_local_test_database():
    validate_integration_mongodb_uri(
        "mongodb://127.0.0.1:27017/gym_erp_ci_test?replicaSet=rs0&authSource=admin"
    )


def test_rejects_forbidden_platform_database():
    with pytest.raises(ValueError, match="prohibida"):
        validate_integration_mongodb_uri("mongodb://127.0.0.1:27017/gym_platform")


def test_rejects_forbidden_operational_database():
    with pytest.raises(ValueError, match="prohibida"):
        validate_integration_mongodb_uri("mongodb://localhost:27017/gym_operational")


def test_rejects_non_test_suffix():
    with pytest.raises(ValueError, match="_test"):
        validate_integration_mongodb_uri("mongodb://127.0.0.1:27017/gym_erp_dev")


def test_rejects_remote_host():
    with pytest.raises(ValueError, match="localhost"):
        validate_integration_mongodb_uri("mongodb://mongo.example.com:27017/gym_erp_ci_test")


def test_rejects_mongodb_srv_scheme():
    with pytest.raises(ValueError, match="mongodb"):
        validate_integration_mongodb_uri("mongodb+srv://localhost/gym_erp_ci_test")


def test_rejects_multi_host_netloc():
    with pytest.raises(ValueError, match="localhost"):
        validate_integration_mongodb_uri("mongodb://127.0.0.1,evil:27017/gym_erp_ci_test")
