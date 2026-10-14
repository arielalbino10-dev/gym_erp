"""Fixtures solo para pruebas de integración (MongoDB real)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import pytest
from pydantic import SecretStr

from gym_erp_api.core.config import Settings
from tests.support.integration_environment import validate_integration_environment


@dataclass
class IntegrationSessionState:
    """Estado de la sesión; evita limpieza si falló la validación previa a escrituras."""

    security_verified: bool = False
    ephemeral_collection_name: str | None = None
    operational_db: str | None = None
    teardown_enabled: bool = False
    extra: dict = field(default_factory=dict)


@pytest.fixture(scope="session")
def integration_session_state() -> IntegrationSessionState:
    return IntegrationSessionState()


def _require_integration_enabled() -> None:
    if os.environ.get("GYM_ERP_RUN_INTEGRATION") != "1":
        pytest.skip(
            "Integración deshabilitada. Exporte GYM_ERP_RUN_INTEGRATION=1 "
            "y variables de entorno de integración documentadas."
        )


@pytest.fixture(scope="session")
def integration_mongodb_uri() -> str:
    _require_integration_enabled()
    uri = os.environ.get("MONGODB_URI_TEST", "").strip()
    if not uri:
        pytest.skip("MONGODB_URI_TEST no configurada.")
    platform_db = os.environ.get("MONGODB_PLATFORM_DB", "").strip().lower()
    operational_db = os.environ.get("MONGODB_OPERATIONAL_DB", "").strip().lower()
    try:
        validate_integration_environment(
            uri=uri,
            platform_db=platform_db,
            operational_db=operational_db,
        )
    except ValueError as exc:
        pytest.fail(f"Entorno de integración rechazado: {exc}")
    return uri


@pytest.fixture(scope="session")
def integration_settings(integration_mongodb_uri: str) -> Settings:
    platform_db = os.environ["MONGODB_PLATFORM_DB"].strip().lower()
    operational_db = os.environ["MONGODB_OPERATIONAL_DB"].strip().lower()
    return Settings(
        app_env="test",
        mongodb_uri=SecretStr(integration_mongodb_uri),
        mongodb_platform_db=platform_db,
        mongodb_operational_db=operational_db,
    )
