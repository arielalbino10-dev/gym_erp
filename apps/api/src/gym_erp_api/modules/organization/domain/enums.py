"""Estados de tenant y sucursal (ADR-0009)."""

from enum import StrEnum


class TenantStatus(StrEnum):
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class BranchStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CLOSED = "closed"


TENANT_ALLOWED_TRANSITIONS: dict[TenantStatus, frozenset[TenantStatus]] = {
    TenantStatus.PROVISIONING: frozenset({TenantStatus.ACTIVE, TenantStatus.SUSPENDED}),
    TenantStatus.ACTIVE: frozenset({TenantStatus.SUSPENDED}),
    TenantStatus.SUSPENDED: frozenset({TenantStatus.ACTIVE}),
}

BRANCH_ALLOWED_TRANSITIONS: dict[BranchStatus, frozenset[BranchStatus]] = {
    BranchStatus.ACTIVE: frozenset({BranchStatus.INACTIVE, BranchStatus.CLOSED}),
    BranchStatus.INACTIVE: frozenset({BranchStatus.ACTIVE, BranchStatus.CLOSED}),
    BranchStatus.CLOSED: frozenset(),
}
