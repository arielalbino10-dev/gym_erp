"""Dominio TenantMembership (H2-C.2)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from gym_erp_api.modules.access.domain.enums import BranchScopeMode, GymRole, MembershipStatus
from gym_erp_api.modules.access.domain.errors import (
    InvalidGymRoleAssignmentError,
    InvalidMembershipFieldError,
    InvalidMembershipStateTransitionError,
)
from gym_erp_api.modules.access.domain.tenant_membership import TenantMembership
from gym_erp_api.modules.organization.domain.errors import InvalidOrganizationIdentifierError
from gym_erp_api.shared_kernel.identifiers import new_uuid
from tests.support.tenant_fixtures import BRANCH_X_ID, BRANCH_Y_ID, TENANT_A_ID, USER_A_ID


def _moment() -> datetime:
    return datetime(2026, 6, 1, 12, 0, tzinfo=UTC)


def test_create_active_membership_valid():
    membership = TenantMembership.create_active(
        user_id=USER_A_ID,
        tenant_id=TENANT_A_ID,
        gym_roles=frozenset({GymRole.GYM_OWNER}),
        branch_scope_mode=BranchScopeMode.ALL_BRANCHES,
        now=_moment(),
    )
    assert membership.status is MembershipStatus.ACTIVE
    assert membership.authz_epoch == 0
    assert membership.context_allowed_branch_ids() is None


def test_invalid_uuid_rejected():
    with pytest.raises(InvalidOrganizationIdentifierError):
        TenantMembership.create_active(
            user_id="not-a-uuid",
            tenant_id=TENANT_A_ID,
            gym_roles=frozenset({GymRole.GYM_ADMIN}),
            branch_scope_mode=BranchScopeMode.ALL_BRANCHES,
            now=_moment(),
        )


def test_membership_state_transitions():
    moment = _moment()
    invited = TenantMembership.create_invited(
        user_id=USER_A_ID,
        tenant_id=TENANT_A_ID,
        gym_roles=frozenset({GymRole.GYM_ADMIN}),
        branch_scope_mode=BranchScopeMode.ALL_BRANCHES,
        now=moment,
    )
    active = invited.accept_invitation(now=moment + timedelta(minutes=1))
    assert active.status is MembershipStatus.ACTIVE
    assert active.authz_epoch == 1
    suspended = active.suspend(now=moment + timedelta(minutes=2))
    assert suspended.status is MembershipStatus.SUSPENDED
    assert suspended.authz_epoch == 2
    reactivated = suspended.reactivate(now=moment + timedelta(minutes=3))
    assert reactivated.status is MembershipStatus.ACTIVE
    assert reactivated.authz_epoch == 3


def test_transitions_invited_active_revoked():
    moment = _moment()
    invited = TenantMembership.create_invited(
        user_id=USER_A_ID,
        tenant_id=TENANT_A_ID,
        gym_roles=frozenset({GymRole.GYM_ADMIN}),
        branch_scope_mode=BranchScopeMode.ALL_BRANCHES,
        now=moment,
    )
    active = invited.accept_invitation(now=moment + timedelta(seconds=1))
    revoked = active.revoke(now=moment + timedelta(seconds=2))
    assert revoked.status is MembershipStatus.REVOKED
    assert revoked.authz_epoch == 2
    with pytest.raises(InvalidMembershipStateTransitionError):
        revoked.accept_invitation()


def test_suspended_membership_domain():
    active = TenantMembership.create_active(
        user_id=USER_A_ID,
        tenant_id=TENANT_A_ID,
        gym_roles=frozenset({GymRole.GYM_OWNER}),
        branch_scope_mode=BranchScopeMode.ALL_BRANCHES,
        now=_moment(),
    )
    suspended = active.suspend()
    assert suspended.status is MembershipStatus.SUSPENDED


def test_accept_invitation_rejects_suspended():
    moment = _moment()
    active = TenantMembership.create_active(
        user_id=USER_A_ID,
        tenant_id=TENANT_A_ID,
        gym_roles=frozenset({GymRole.GYM_OWNER}),
        branch_scope_mode=BranchScopeMode.ALL_BRANCHES,
        now=moment,
    )
    suspended = active.suspend(now=moment + timedelta(seconds=1))
    with pytest.raises(InvalidMembershipStateTransitionError):
        suspended.accept_invitation()


def test_revoked_requires_explicit_reinvite_grant():
    moment = _moment()
    active = TenantMembership.create_active(
        user_id=USER_A_ID,
        tenant_id=TENANT_A_ID,
        gym_roles=frozenset({GymRole.GYM_OWNER}),
        branch_scope_mode=BranchScopeMode.ALL_BRANCHES,
        now=moment,
    )
    revoked = active.revoke(now=moment + timedelta(seconds=1))
    reinvited = revoked.apply_reinvite_grant(
        gym_roles=frozenset({GymRole.GYM_ADMIN}),
        branch_scope_mode=BranchScopeMode.ALL_BRANCHES,
        now=moment + timedelta(seconds=2),
    )
    assert reinvited.status is MembershipStatus.INVITED
    assert reinvited.accepted_at is None
    assert GymRole.GYM_OWNER not in reinvited.gym_roles
    assert GymRole.GYM_ADMIN in reinvited.gym_roles


def test_apply_reinvite_grant_rejects_non_revoked():
    active = TenantMembership.create_active(
        user_id=USER_A_ID,
        tenant_id=TENANT_A_ID,
        gym_roles=frozenset({GymRole.GYM_ADMIN}),
        branch_scope_mode=BranchScopeMode.ALL_BRANCHES,
        now=_moment(),
    )
    with pytest.raises(InvalidMembershipStateTransitionError):
        active.apply_reinvite_grant(
            gym_roles=frozenset({GymRole.GYM_ADMIN}),
            branch_scope_mode=BranchScopeMode.ALL_BRANCHES,
        )


def test_all_branches_scope():
    membership = TenantMembership.create_active(
        user_id=USER_A_ID,
        tenant_id=TENANT_A_ID,
        gym_roles=frozenset({GymRole.GYM_ADMIN}),
        branch_scope_mode=BranchScopeMode.ALL_BRANCHES,
        now=_moment(),
    )
    assert membership.allowed_branch_ids is None
    assert membership.context_allowed_branch_ids() is None


def test_explicit_branches_scope():
    branches = frozenset({BRANCH_X_ID, BRANCH_Y_ID})
    membership = TenantMembership.create_active(
        user_id=USER_A_ID,
        tenant_id=TENANT_A_ID,
        gym_roles=frozenset({GymRole.BRANCH_ADMIN}),
        branch_scope_mode=BranchScopeMode.EXPLICIT_BRANCHES,
        allowed_branch_ids=branches,
        now=_moment(),
    )
    assert membership.context_allowed_branch_ids() == branches


def test_explicit_empty_not_allowed_for_active():
    with pytest.raises(InvalidMembershipFieldError):
        TenantMembership.create_active(
            user_id=USER_A_ID,
            tenant_id=TENANT_A_ID,
            gym_roles=frozenset({GymRole.GYM_ADMIN}),
            branch_scope_mode=BranchScopeMode.EXPLICIT_BRANCHES,
            allowed_branch_ids=frozenset(),
            now=_moment(),
        )


def test_multiple_tenants_same_user_distinct_memberships():
    m1 = TenantMembership.create_active(
        user_id=USER_A_ID,
        tenant_id=TENANT_A_ID,
        gym_roles=frozenset({GymRole.GYM_OWNER}),
        branch_scope_mode=BranchScopeMode.ALL_BRANCHES,
        now=_moment(),
    )
    m2 = TenantMembership.create_active(
        user_id=USER_A_ID,
        tenant_id=new_uuid(),
        gym_roles=frozenset({GymRole.GYM_ADMIN}),
        branch_scope_mode=BranchScopeMode.ALL_BRANCHES,
        now=_moment(),
    )
    assert m1.tenant_id != m2.tenant_id
    assert m1.user_id == m2.user_id


def test_authz_epoch_increments_on_role_change():
    membership = TenantMembership.create_active(
        user_id=USER_A_ID,
        tenant_id=TENANT_A_ID,
        gym_roles=frozenset({GymRole.GYM_ADMIN}),
        branch_scope_mode=BranchScopeMode.ALL_BRANCHES,
        now=_moment(),
    )
    updated = membership.with_roles(frozenset({GymRole.GYM_OWNER}), now=_moment())
    assert updated.authz_epoch == 1


def test_branch_admin_requires_explicit_branches():
    with pytest.raises(InvalidGymRoleAssignmentError):
        TenantMembership.create_active(
            user_id=USER_A_ID,
            tenant_id=TENANT_A_ID,
            gym_roles=frozenset({GymRole.BRANCH_ADMIN}),
            branch_scope_mode=BranchScopeMode.ALL_BRANCHES,
            now=_moment(),
        )


def test_gym_roles_controlled_enum():
    assert GymRole.GYM_OWNER.value == "gym_owner"
    assert "root_admin" not in {role.value for role in GymRole}
    assert "platform_admin" not in {role.value for role in GymRole}
