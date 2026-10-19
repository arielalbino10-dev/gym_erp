"""Estados de identidad global (sin roles ni tenant)."""

from enum import StrEnum


class UserIdentityStatus(StrEnum):
    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    LOCKED = "locked"
    DISABLED = "disabled"


IDENTITY_ALLOWED_TRANSITIONS: dict[UserIdentityStatus, frozenset[UserIdentityStatus]] = {
    UserIdentityStatus.PENDING_VERIFICATION: frozenset({UserIdentityStatus.DISABLED}),
    UserIdentityStatus.ACTIVE: frozenset({UserIdentityStatus.LOCKED, UserIdentityStatus.DISABLED}),
    UserIdentityStatus.LOCKED: frozenset({UserIdentityStatus.ACTIVE, UserIdentityStatus.DISABLED}),
    UserIdentityStatus.DISABLED: frozenset({UserIdentityStatus.ACTIVE}),
}
