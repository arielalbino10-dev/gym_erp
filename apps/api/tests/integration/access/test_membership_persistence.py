"""Persistencia tenant_memberships en gym_platform_test (H2-C.2)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from gym_erp_api.modules.access.application.errors import (
    MembershipDuplicateError,
    MembershipUpdateConflictError,
)
from gym_erp_api.modules.access.domain.enums import BranchScopeMode, GymRole
from gym_erp_api.modules.access.domain.tenant_membership import TenantMembership
from gym_erp_api.shared_kernel.identifiers import new_uuid
from tests.support.tenant_fixtures import BRANCH_X_ID, USER_A_ID

pytestmark = [
    pytest.mark.integration,
    pytest.mark.access_persistence,
    pytest.mark.asyncio(loop_scope="session"),
]


def _moment() -> datetime:
    return datetime(2026, 7, 1, 10, 0, tzinfo=UTC)


async def test_membership_round_trip(mongo_membership_repository):
    tenant_id = new_uuid()
    membership = TenantMembership.create_active(
        user_id=USER_A_ID,
        tenant_id=tenant_id,
        gym_roles=frozenset({GymRole.GYM_OWNER}),
        branch_scope_mode=BranchScopeMode.ALL_BRANCHES,
        now=_moment(),
    )
    await mongo_membership_repository.insert(membership)
    loaded = await mongo_membership_repository.get_by_user_and_tenant(
        user_id=USER_A_ID,
        tenant_id=tenant_id,
    )
    assert loaded == membership


async def test_duplicate_tenant_user_rejected(mongo_membership_repository):
    tenant_id = new_uuid()
    first = TenantMembership.create_active(
        user_id=USER_A_ID,
        tenant_id=tenant_id,
        gym_roles=frozenset({GymRole.GYM_ADMIN}),
        branch_scope_mode=BranchScopeMode.ALL_BRANCHES,
        now=_moment(),
    )
    await mongo_membership_repository.insert(first)
    second = TenantMembership.create_active(
        user_id=USER_A_ID,
        tenant_id=tenant_id,
        gym_roles=frozenset({GymRole.GYM_OWNER}),
        branch_scope_mode=BranchScopeMode.ALL_BRANCHES,
        now=_moment(),
    )
    with pytest.raises(MembershipDuplicateError):
        await mongo_membership_repository.insert(second)


async def test_list_active_by_user_multiple_tenants(mongo_membership_repository):
    user_id = new_uuid()
    tenant_a = new_uuid()
    tenant_b = new_uuid()
    m1 = TenantMembership.create_active(
        user_id=user_id,
        tenant_id=tenant_a,
        gym_roles=frozenset({GymRole.GYM_OWNER}),
        branch_scope_mode=BranchScopeMode.ALL_BRANCHES,
        now=_moment(),
    )
    m2 = TenantMembership.create_active(
        user_id=user_id,
        tenant_id=tenant_b,
        gym_roles=frozenset({GymRole.GYM_ADMIN}),
        branch_scope_mode=BranchScopeMode.ALL_BRANCHES,
        now=_moment(),
    )
    await mongo_membership_repository.insert(m1)
    await mongo_membership_repository.insert(m2)
    active = await mongo_membership_repository.list_active_by_user_id(user_id)
    assert {item.tenant_id for item in active} == {tenant_a, tenant_b}


async def test_update_conflict_on_stale_updated_at(mongo_membership_repository):
    membership = TenantMembership.create_active(
        user_id=USER_A_ID,
        tenant_id=new_uuid(),
        gym_roles=frozenset({GymRole.GYM_ADMIN}),
        branch_scope_mode=BranchScopeMode.ALL_BRANCHES,
        now=_moment(),
    )
    await mongo_membership_repository.insert(membership)
    stale = membership
    updated = membership.suspend(now=_moment() + timedelta(seconds=1))
    await mongo_membership_repository.save(updated, expected_authz_epoch=membership.authz_epoch)
    with pytest.raises(MembershipUpdateConflictError):
        await mongo_membership_repository.save(
            stale.suspend(now=_moment() + timedelta(seconds=2)),
            expected_authz_epoch=stale.authz_epoch,
        )


async def test_reinvite_clears_accepted_at_in_storage(mongo_membership_repository):
    moment = _moment()
    active = TenantMembership.create_active(
        user_id=new_uuid(),
        tenant_id=new_uuid(),
        gym_roles=frozenset({GymRole.GYM_ADMIN}),
        branch_scope_mode=BranchScopeMode.ALL_BRANCHES,
        now=moment,
    )
    await mongo_membership_repository.insert(active)
    revoked = active.revoke(now=moment + timedelta(seconds=1))
    await mongo_membership_repository.save(revoked, expected_authz_epoch=active.authz_epoch)
    reinvited = revoked.apply_reinvite_grant(
        gym_roles=frozenset({GymRole.GYM_ADMIN}),
        branch_scope_mode=BranchScopeMode.ALL_BRANCHES,
        now=moment + timedelta(seconds=2),
    )
    await mongo_membership_repository.save(reinvited, expected_authz_epoch=revoked.authz_epoch)
    loaded = await mongo_membership_repository.get_by_id(active.membership_id)
    assert loaded is not None
    assert loaded.status.value == "invited"
    assert loaded.accepted_at is None


async def test_concurrent_save_second_writer_loses(mongo_membership_repository):
    moment = _moment()
    membership = TenantMembership.create_active(
        user_id=new_uuid(),
        tenant_id=new_uuid(),
        gym_roles=frozenset({GymRole.GYM_ADMIN}),
        branch_scope_mode=BranchScopeMode.ALL_BRANCHES,
        now=moment,
    )
    await mongo_membership_repository.insert(membership)
    t1 = moment + timedelta(seconds=1)
    first = membership.with_roles(frozenset({GymRole.GYM_OWNER}), now=t1)
    second = membership.with_roles(frozenset({GymRole.GYM_ADMIN}), now=t1)
    await mongo_membership_repository.save(first, expected_authz_epoch=membership.authz_epoch)
    with pytest.raises(MembershipUpdateConflictError):
        await mongo_membership_repository.save(second, expected_authz_epoch=membership.authz_epoch)
    loaded = await mongo_membership_repository.get_by_id(membership.membership_id)
    assert loaded is not None
    assert loaded.gym_roles == frozenset({GymRole.GYM_OWNER})
    assert loaded.authz_epoch == 1


async def test_explicit_branch_scope_persisted(mongo_membership_repository):
    membership = TenantMembership.create_active(
        user_id=USER_A_ID,
        tenant_id=new_uuid(),
        gym_roles=frozenset({GymRole.BRANCH_ADMIN}),
        branch_scope_mode=BranchScopeMode.EXPLICIT_BRANCHES,
        allowed_branch_ids=frozenset({BRANCH_X_ID}),
        now=_moment(),
    )
    await mongo_membership_repository.insert(membership)
    loaded = await mongo_membership_repository.get_by_id(membership.membership_id)
    assert loaded is not None
    assert loaded.allowed_branch_ids == frozenset({BRANCH_X_ID})
