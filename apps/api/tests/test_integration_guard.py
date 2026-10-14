"""Pruebas unitarias de la guardia de URI y entorno de integración (sin MongoDB)."""

import pytest

from tests.support.integration_environment import (
    EXPECTED_INTEGRATION_USER,
    validate_integration_authenticated_roles,
    validate_integration_environment,
    validate_integration_mongodb_uri,
)
from tests.support.mongodb_uri_guard import validate_integration_mongodb_uri as guard_entrypoint


def _valid_uri(
    user: str = EXPECTED_INTEGRATION_USER,
    db: str = "gym_operational_test",
) -> str:
    return f"mongodb://{user}:secret@127.0.0.1:27017/{db}?replicaSet=rs0&authSource=admin"


def test_accepts_full_integration_uri():
    validate_integration_mongodb_uri(_valid_uri())
    guard_entrypoint(_valid_uri())


def test_validate_integration_environment_joint():
    uri = _valid_uri()
    validate_integration_environment(
        uri=uri,
        platform_db="gym_platform_test",
        operational_db="gym_operational_test",
    )


def test_rejects_forbidden_platform_database_in_uri():
    with pytest.raises(ValueError, match="prohibida"):
        validate_integration_mongodb_uri(_valid_uri(db="gym_platform"))


def test_rejects_forbidden_operational_database_in_uri():
    with pytest.raises(ValueError, match="prohibida"):
        validate_integration_mongodb_uri(_valid_uri(db="gym_operational"))


def test_rejects_non_allowlist_test_database():
    with pytest.raises(ValueError, match="allowlist"):
        validate_integration_mongodb_uri(_valid_uri(db="gym_erp_ci_test"))


def test_rejects_remote_host():
    uri = _valid_uri().replace("127.0.0.1", "mongo.example.com")
    with pytest.raises(ValueError, match="localhost"):
        validate_integration_mongodb_uri(uri)


def test_rejects_mongodb_srv_scheme():
    with pytest.raises(ValueError, match="mongodb"):
        validate_integration_mongodb_uri("mongodb+srv://localhost/gym_operational_test")


def test_rejects_app_user():
    with pytest.raises(ValueError, match="prohibido"):
        validate_integration_mongodb_uri(_valid_uri(user="gym_erp_app"))


def test_rejects_admin_user():
    with pytest.raises(ValueError, match="prohibido"):
        validate_integration_mongodb_uri(_valid_uri(user="gym_erp_admin"))


def test_rejects_missing_replica_set():
    uri = (
        "mongodb://gym_erp_integration:secret@127.0.0.1:27017/gym_operational_test?authSource=admin"
    )
    with pytest.raises(ValueError, match="replicaSet"):
        validate_integration_mongodb_uri(uri)


def test_rejects_wrong_auth_source():
    uri = (
        "mongodb://gym_erp_integration:secret@127.0.0.1:27017/gym_operational_test"
        "?replicaSet=rs0&authSource=gym_operational_test"
    )
    with pytest.raises(ValueError, match="authSource"):
        validate_integration_mongodb_uri(uri)


def test_rejects_wrong_platform_db_setting():
    with pytest.raises(ValueError, match="prohibida"):
        validate_integration_environment(
            uri=_valid_uri(),
            platform_db="gym_platform",
            operational_db="gym_operational_test",
        )


def test_rejects_wrong_operational_db_setting():
    with pytest.raises(ValueError, match="prohibida"):
        validate_integration_environment(
            uri=_valid_uri(),
            platform_db="gym_platform_test",
            operational_db="gym_operational",
        )


def test_connection_status_roles_accept_minimal_integration_grants():
    validate_integration_authenticated_roles(
        {
            "authenticatedUsers": [{"user": "gym_erp_integration", "db": "admin"}],
            "authenticatedUserRoles": [
                {"role": "readWrite", "db": "gym_platform_test"},
                {"role": "readWrite", "db": "gym_operational_test"},
            ],
        }
    )


def test_connection_status_roles_reject_root():
    with pytest.raises(ValueError, match="privilegiado"):
        validate_integration_authenticated_roles(
            {
                "authenticatedUsers": [{"user": "gym_erp_integration", "db": "admin"}],
                "authenticatedUserRoles": [{"role": "root", "db": "admin"}],
            }
        )


def test_connection_status_roles_reject_production_database():
    with pytest.raises(ValueError, match="no autorizada"):
        validate_integration_authenticated_roles(
            {
                "authenticatedUsers": [{"user": "gym_erp_integration", "db": "admin"}],
                "authenticatedUserRoles": [{"role": "readWrite", "db": "gym_operational"}],
            }
        )
