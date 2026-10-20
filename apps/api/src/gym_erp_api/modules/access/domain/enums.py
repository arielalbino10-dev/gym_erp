"""Estados, alcance y roles gym (sin roles platform)."""

from enum import StrEnum


class MembershipStatus(StrEnum):
    INVITED = "invited"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class BranchScopeMode(StrEnum):
    ALL_BRANCHES = "all_branches"
    EXPLICIT_BRANCHES = "explicit_branches"


class GymRole(StrEnum):
    """Roles operativos de gimnasio (controlados en dominio; no RBAC completo)."""

    GYM_OWNER = "gym_owner"
    GYM_ADMIN = "gym_admin"
    BRANCH_ADMIN = "branch_admin"


MEMBERSHIP_ALLOWED_TRANSITIONS: dict[MembershipStatus, frozenset[MembershipStatus]] = {
    MembershipStatus.INVITED: frozenset(
        {MembershipStatus.ACTIVE, MembershipStatus.REVOKED, MembershipStatus.SUSPENDED}
    ),
    MembershipStatus.ACTIVE: frozenset({MembershipStatus.SUSPENDED, MembershipStatus.REVOKED}),
    MembershipStatus.SUSPENDED: frozenset({MembershipStatus.ACTIVE, MembershipStatus.REVOKED}),
    MembershipStatus.REVOKED: frozenset({MembershipStatus.INVITED}),
}
