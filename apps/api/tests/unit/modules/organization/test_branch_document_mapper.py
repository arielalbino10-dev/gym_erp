from datetime import UTC, datetime

import pytest

from gym_erp_api.modules.organization.domain.branch import Branch
from gym_erp_api.modules.organization.domain.errors import InvalidOrganizationPersistenceError
from gym_erp_api.modules.organization.domain.value_objects import BranchAddress
from gym_erp_api.modules.organization.infrastructure.mongo.branch_document_mapper import (
    branch_from_document,
    branch_to_document,
)
from tests.support.tenant_fixtures import BRANCH_X_ID, TENANT_A_ID


def test_branch_round_trip_with_address():
    moment = datetime(2026, 3, 1, 9, 0, tzinfo=UTC)
    address = BranchAddress.create(line1="Calle 1", city="CDMX")
    branch = Branch.create(
        tenant_id=TENANT_A_ID,
        name="Centro",
        branch_id=BRANCH_X_ID,
        code="centro",
        address=address,
        now=moment,
    )
    doc = branch_to_document(branch)
    assert doc["_id"] == BRANCH_X_ID
    assert doc["address"]["city"] == "CDMX"
    restored = branch_from_document(doc)
    assert restored == branch


def test_branch_from_document_rejects_naive_datetime():
    with pytest.raises(InvalidOrganizationPersistenceError):
        branch_from_document(
            {
                "_id": BRANCH_X_ID,
                "branch_id": BRANCH_X_ID,
                "tenant_id": TENANT_A_ID,
                "name": "X",
                "status": "active",
                "timezone": "America/Mexico_City",
                "created_at": datetime(2026, 1, 1),
                "updated_at": datetime(2026, 1, 1, tzinfo=UTC),
            }
        )
