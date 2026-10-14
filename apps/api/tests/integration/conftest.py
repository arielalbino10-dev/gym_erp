"""Fixtures solo para pruebas de integración (MongoDB real)."""

import os

import pytest

from tests.support.mongodb_uri_guard import validate_integration_mongodb_uri


@pytest.fixture(scope="session")
def integration_mongodb_uri() -> str:
    if os.environ.get("GYM_ERP_RUN_INTEGRATION") != "1":
        pytest.skip(
            "Integración deshabilitada. Exporte GYM_ERP_RUN_INTEGRATION=1 "
            "y MONGODB_URI_TEST con una BD local *_test."
        )
    uri = os.environ.get("MONGODB_URI_TEST", "").strip()
    if not uri:
        pytest.skip("MONGODB_URI_TEST no configurada.")
    try:
        validate_integration_mongodb_uri(uri)
    except ValueError as exc:
        pytest.fail(f"URI de integración rechazada: {exc}")
    return uri
