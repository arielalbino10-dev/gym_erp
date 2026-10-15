from datetime import UTC, datetime

import pytest

from gym_erp_api.modules.organization.domain.enums import TenantStatus
from gym_erp_api.modules.organization.domain.errors import InvalidOrganizationPersistenceError
from gym_erp_api.modules.organization.domain.tenant import Tenant
from gym_erp_api.modules.organization.infrastructure.mongo.tenant_document_mapper import (
    tenant_from_document,
    tenant_to_document,
)
from tests.support.tenant_fixtures import TENANT_A_ID, USER_A_ID


def test_tenant_round_trip_document():
    moment = datetime(2026, 3, 1, 8, 0, tzinfo=UTC)
    tenant = Tenant.create(
        legal_name="Legal SA",
        display_name="Brand",
        tenant_id=TENANT_A_ID,
        commercial_email="a@example.com",
        created_by_user_id=USER_A_ID,
        now=moment,
    ).transition_status(TenantStatus.ACTIVE, now=moment)
    doc = tenant_to_document(tenant)
    assert doc["_id"] == TENANT_A_ID
    assert doc["tenant_id"] == TENANT_A_ID
    restored = tenant_from_document(doc)
    assert restored == tenant


def test_tenant_from_document_rejects_missing_status():
    with pytest.raises(InvalidOrganizationPersistenceError):
        tenant_from_document({"_id": TENANT_A_ID, "tenant_id": TENANT_A_ID})
