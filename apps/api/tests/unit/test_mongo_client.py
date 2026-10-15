from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from gym_erp_api.core.config import Settings
from gym_erp_api.infrastructure.mongo.database import create_mongo_client, mongo_client_options
from gym_erp_api.modules.organization.domain.errors import InvalidOrganizationPersistenceError
from gym_erp_api.modules.organization.domain.persistence_utils import parse_utc_datetime
from gym_erp_api.modules.organization.domain.tenant import Tenant
from tests.support.tenant_fixtures import TENANT_A_ID


def test_mongo_client_options_enables_tz_aware_utc():
    opts = mongo_client_options(server_selection_timeout_ms=1500)
    assert opts["tz_aware"] is True
    assert opts["tzinfo"] is UTC
    assert opts["serverSelectionTimeoutMS"] == 1500


@patch("gym_erp_api.infrastructure.mongo.database.AsyncMongoClient")
def test_create_mongo_client_passes_tz_aware(mock_client_cls):
    mock_client_cls.return_value = MagicMock()
    settings = Settings(
        app_env="test",
        mongodb_uri=SecretStr("mongodb://127.0.0.1:27017/gym_operational?replicaSet=rs0"),
        mongodb_ping_timeout_ms=2000,
    )
    client = create_mongo_client(settings)
    assert client is mock_client_cls.return_value
    mock_client_cls.assert_called_once_with(
        "mongodb://127.0.0.1:27017/gym_operational?replicaSet=rs0",
        tz_aware=True,
        tzinfo=UTC,
        serverSelectionTimeoutMS=2000,
    )


def test_create_mongo_client_returns_none_without_uri():
    settings = Settings(app_env="test", mongodb_uri=None)
    assert create_mongo_client(settings) is None


def test_parse_utc_datetime_rejects_naive():
    with pytest.raises(InvalidOrganizationPersistenceError, match="zona horaria"):
        parse_utc_datetime(datetime(2026, 1, 1, 12, 0), "created_at")


def test_parse_utc_datetime_normalizes_to_utc():
    aware = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    assert parse_utc_datetime(aware, "created_at").tzinfo is UTC


def test_tenant_from_persistence_rejects_naive_timestamps():
    with pytest.raises(InvalidOrganizationPersistenceError):
        Tenant.from_persistence(
            {
                "_id": TENANT_A_ID,
                "tenant_id": TENANT_A_ID,
                "legal_name": "L",
                "display_name": "D",
                "status": "active",
                "timezone": "America/Mexico_City",
                "created_at": datetime(2026, 1, 1),
                "updated_at": datetime(2026, 1, 1, tzinfo=UTC),
            }
        )
