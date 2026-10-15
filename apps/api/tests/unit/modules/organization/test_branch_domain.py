from datetime import UTC, datetime

import pytest

from gym_erp_api.modules.organization.domain.branch import Branch
from gym_erp_api.modules.organization.domain.enums import BranchStatus
from gym_erp_api.modules.organization.domain.errors import (
    InvalidOrganizationFieldError,
    InvalidOrganizationIdentifierError,
    InvalidOrganizationStateTransitionError,
    OrganizationImmutabilityError,
)
from gym_erp_api.modules.organization.domain.value_objects import BranchAddress
from gym_erp_api.shared_kernel.identifiers import is_valid_uuid_v4
from tests.support.tenant_fixtures import BRANCH_X_ID, TENANT_A_ID, TENANT_B_ID, USER_A_ID


def test_branch_create_defaults():
    branch = Branch.create(
        tenant_id=TENANT_A_ID,
        name="  Sucursal Centro  ",
        code=" centro-1 ",
    )
    assert branch.name == "Sucursal Centro"
    assert branch.code == "CENTRO-1"
    assert branch.status is BranchStatus.ACTIVE
    assert branch.tenant_id == TENANT_A_ID
    assert is_valid_uuid_v4(branch.branch_id)
    assert branch.timezone == "America/Mexico_City"


def test_branch_with_address():
    address = BranchAddress.create(
        line1="Av. Ficticia 123",
        city="Ciudad de México",
        state="CDMX",
        postal_code="01000",
    )
    branch = Branch.create(
        tenant_id=TENANT_A_ID,
        name="Centro",
        branch_id=BRANCH_X_ID,
        address=address,
    )
    assert branch.address is not None
    assert branch.address.country_code == "MX"
    assert branch.address.city == "Ciudad de México"


def test_branch_status_transitions():
    branch = Branch.create(tenant_id=TENANT_A_ID, name="Centro", branch_id=BRANCH_X_ID)
    inactive = branch.transition_status(BranchStatus.INACTIVE)
    assert inactive.status is BranchStatus.INACTIVE
    active_again = inactive.transition_status(BranchStatus.ACTIVE)
    assert active_again.status is BranchStatus.ACTIVE
    closed = active_again.transition_status(BranchStatus.CLOSED)
    assert closed.status is BranchStatus.CLOSED


def test_branch_closed_is_terminal():
    branch = Branch.create(tenant_id=TENANT_A_ID, name="Centro", branch_id=BRANCH_X_ID)
    closed = branch.transition_status(BranchStatus.CLOSED)
    with pytest.raises(InvalidOrganizationStateTransitionError):
        closed.transition_status(BranchStatus.ACTIVE)


def test_branch_rejects_invalid_code():
    with pytest.raises(InvalidOrganizationFieldError):
        Branch.create(tenant_id=TENANT_A_ID, name="Centro", code="x")


def test_address_rejects_invalid_country_code():
    with pytest.raises(InvalidOrganizationFieldError):
        BranchAddress.create(line1="A", city="B", country_code="MEX")


def test_branch_rejects_invalid_tenant_id():
    with pytest.raises(InvalidOrganizationIdentifierError):
        Branch.create(tenant_id="bad-id", name="Centro")


def test_branch_immutable_tenant_id():
    branch = Branch.create(tenant_id=TENANT_A_ID, name="Centro", branch_id=BRANCH_X_ID)
    with pytest.raises(OrganizationImmutabilityError):
        branch.with_reassigned_tenant(TENANT_B_ID)


def test_branch_immutable_branch_id():
    branch = Branch.create(tenant_id=TENANT_A_ID, name="Centro", branch_id=BRANCH_X_ID)
    with pytest.raises(OrganizationImmutabilityError):
        branch.with_new_branch_id(TENANT_B_ID)


def test_branch_audit_on_transition():
    moment = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)
    branch = Branch.create(
        tenant_id=TENANT_A_ID,
        name="Centro",
        branch_id=BRANCH_X_ID,
        created_by_user_id=USER_A_ID,
        now=moment,
    )
    updated = branch.transition_status(
        BranchStatus.INACTIVE,
        updated_by_user_id=USER_A_ID,
        now=datetime(2026, 2, 2, 12, 0, tzinfo=UTC),
    )
    assert updated.updated_at > branch.updated_at
    assert updated.branch_id == branch.branch_id
    assert updated.tenant_id == branch.tenant_id
