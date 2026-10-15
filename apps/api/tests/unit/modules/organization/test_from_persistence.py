from datetime import UTC, datetime

import pytest

from gym_erp_api.modules.organization.domain.errors import InvalidOrganizationPersistenceError
from gym_erp_api.modules.organization.domain.tenant import Tenant
from tests.support.tenant_fixtures import TENANT_A_ID


def test_tenant_from_persistence_validates_email_consistency():
    moment = datetime(2026, 1, 1, tzinfo=UTC)
    with pytest.raises(InvalidOrganizationPersistenceError):
        Tenant.from_persistence(
            {
                "_id": TENANT_A_ID,
                "tenant_id": TENANT_A_ID,
                "legal_name": "L",
                "display_name": "D",
                "status": "active",
                "timezone": "America/Mexico_City",
                "commercial_email": "a@example.com",
                "commercial_email_normalized": "wrong@example.com",
                "created_at": moment,
                "updated_at": moment,
            }
        )
