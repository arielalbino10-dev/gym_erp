"""Anti-escalada de grants de roles (H2-C.4)."""

from __future__ import annotations

import pytest

from gym_erp_api.modules.access.application.authorization.role_grant_policy import (
    validate_permission_grant_via_roles,
    validate_role_grant,
)
from gym_erp_api.modules.access.application.errors import PermissionDeniedError
from gym_erp_api.modules.access.domain.enums import GymRole

_MEMBERSHIP_A = "880e8400-e29b-41d4-a716-446655440020"
_MEMBERSHIP_B = "990e8400-e29b-41d4-a716-446655440030"


def test_gym_admin_cannot_grant_owner():
    with pytest.raises(PermissionDeniedError):
        validate_role_grant(
            actor_roles=frozenset({GymRole.GYM_ADMIN}),
            proposed_roles=frozenset({GymRole.GYM_OWNER}),
            target_membership_id=_MEMBERSHIP_B,
            actor_membership_id=_MEMBERSHIP_A,
        )


def test_branch_admin_cannot_grant_roles():
    with pytest.raises(PermissionDeniedError):
        validate_role_grant(
            actor_roles=frozenset({GymRole.BRANCH_ADMIN}),
            proposed_roles=frozenset({GymRole.BRANCH_ADMIN}),
            target_membership_id=_MEMBERSHIP_B,
            actor_membership_id=_MEMBERSHIP_A,
        )


def test_owner_may_grant_admin():
    validate_role_grant(
        actor_roles=frozenset({GymRole.GYM_OWNER}),
        proposed_roles=frozenset({GymRole.GYM_ADMIN}),
        target_membership_id=_MEMBERSHIP_B,
        actor_membership_id=_MEMBERSHIP_A,
    )


def test_cannot_elevate_own_roles():
    with pytest.raises(PermissionDeniedError):
        validate_role_grant(
            actor_roles=frozenset({GymRole.GYM_ADMIN}),
            proposed_roles=frozenset({GymRole.GYM_ADMIN, GymRole.GYM_OWNER}),
            target_membership_id=_MEMBERSHIP_A,
            actor_membership_id=_MEMBERSHIP_A,
        )


def test_cannot_grant_permissions_actor_lacks():
    with pytest.raises(PermissionDeniedError):
        validate_permission_grant_via_roles(
            actor_roles=frozenset({GymRole.GYM_ADMIN}),
            proposed_roles=frozenset({GymRole.GYM_OWNER}),
        )
