"""Validación de alcance de sucursales (H2-C.2.1)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from gym_erp_api.modules.access.application.errors import BranchScopeValidationError
from gym_erp_api.modules.access.application.services.membership_branch_scope import (
    ensure_membership_branch_scope,
)
from gym_erp_api.modules.access.application.services.membership_persistence import (
    insert_membership_with_validated_scope,
)
from gym_erp_api.modules.access.domain.enums import BranchScopeMode, GymRole
from gym_erp_api.modules.access.domain.tenant_membership import TenantMembership
from gym_erp_api.shared_kernel.identifiers import new_uuid
from tests.support.in_memory_branch_scope_validator import InMemoryTenantBranchScopeValidator
from tests.support.tenant_fixtures import (
    BRANCH_X_ID,
    BRANCH_Y_ID,
    TENANT_A_ID,
    TENANT_B_ID,
    USER_A_ID,
)


def _moment() -> datetime:
    return datetime(2026, 8, 1, 12, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_cross_tenant_branch_rejected():
    validator = InMemoryTenantBranchScopeValidator(
        branches_by_tenant={TENANT_A_ID: frozenset({BRANCH_X_ID})},
    )
    with pytest.raises(BranchScopeValidationError):
        await ensure_membership_branch_scope(
            tenant_id=TENANT_A_ID,
            branch_scope_mode=BranchScopeMode.EXPLICIT_BRANCHES,
            allowed_branch_ids=frozenset({BRANCH_Y_ID}),
            validator=validator,
        )


@pytest.mark.asyncio
async def test_foreign_branch_for_tenant_b_rejected():
    validator = InMemoryTenantBranchScopeValidator(
        branches_by_tenant={
            TENANT_A_ID: frozenset({BRANCH_X_ID}),
            TENANT_B_ID: frozenset({BRANCH_Y_ID}),
        },
    )
    with pytest.raises(BranchScopeValidationError):
        await ensure_membership_branch_scope(
            tenant_id=TENANT_B_ID,
            branch_scope_mode=BranchScopeMode.EXPLICIT_BRANCHES,
            allowed_branch_ids=frozenset({BRANCH_X_ID}),
            validator=validator,
        )


@pytest.mark.asyncio
async def test_insert_with_validated_scope_calls_repo():
    tenant_id = new_uuid()
    branch_id = new_uuid()
    validator = InMemoryTenantBranchScopeValidator(
        branches_by_tenant={tenant_id: frozenset({branch_id})},
    )

    class _Repo:
        def __init__(self) -> None:
            self.inserted: TenantMembership | None = None

        async def insert(self, membership, *, session=None):
            self.inserted = membership

    repo = _Repo()
    membership = TenantMembership.create_active(
        user_id=USER_A_ID,
        tenant_id=tenant_id,
        gym_roles=frozenset({GymRole.BRANCH_ADMIN}),
        branch_scope_mode=BranchScopeMode.EXPLICIT_BRANCHES,
        allowed_branch_ids=frozenset({branch_id}),
        now=_moment(),
    )
    await insert_membership_with_validated_scope(
        membership,
        repository=repo,
        branch_validator=validator,
    )
    assert repo.inserted == membership
