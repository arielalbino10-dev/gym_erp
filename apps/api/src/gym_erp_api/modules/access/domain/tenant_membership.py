"""Membresía usuario–tenant (gym_platform, ADR-0009)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any

from gym_erp_api.modules.access.domain.enums import (
    MEMBERSHIP_ALLOWED_TRANSITIONS,
    BranchScopeMode,
    GymRole,
    MembershipStatus,
)
from gym_erp_api.modules.access.domain.errors import (
    InvalidGymRoleAssignmentError,
    InvalidMembershipFieldError,
    InvalidMembershipStateTransitionError,
)
from gym_erp_api.modules.access.domain.persistence_utils import ensure_utc, parse_utc_datetime
from gym_erp_api.modules.organization.domain.validators import require_uuid_v4
from gym_erp_api.shared_kernel.identifiers import new_uuid


def _normalize_branch_ids(branch_ids: frozenset[str] | None) -> frozenset[str] | None:
    if branch_ids is None:
        return None
    return frozenset(require_uuid_v4(bid, "branch_id") for bid in branch_ids)


def _normalize_gym_roles(roles: frozenset[GymRole]) -> frozenset[GymRole]:
    if not roles:
        raise InvalidMembershipFieldError("gym_roles no puede estar vacío.")
    return frozenset(GymRole(r.value if isinstance(r, GymRole) else r) for r in roles)


@dataclass(frozen=True, slots=True)
class TenantMembership:
    membership_id: str
    user_id: str
    tenant_id: str
    status: MembershipStatus
    branch_scope_mode: BranchScopeMode
    gym_roles: frozenset[GymRole]
    authz_epoch: int
    created_at: datetime
    updated_at: datetime
    allowed_branch_ids: frozenset[str] | None = None
    invited_at: datetime | None = None
    accepted_at: datetime | None = None
    created_by_user_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "membership_id", require_uuid_v4(self.membership_id, "membership_id")
        )
        object.__setattr__(self, "user_id", require_uuid_v4(self.user_id, "user_id"))
        object.__setattr__(self, "tenant_id", require_uuid_v4(self.tenant_id, "tenant_id"))
        if self.authz_epoch < 0:
            raise InvalidMembershipFieldError("authz_epoch debe ser >= 0.")
        normalized_branches = _normalize_branch_ids(self.allowed_branch_ids)
        object.__setattr__(self, "allowed_branch_ids", normalized_branches)
        normalized_roles = _normalize_gym_roles(self.gym_roles)
        object.__setattr__(self, "gym_roles", normalized_roles)
        if self.created_by_user_id is not None:
            object.__setattr__(
                self,
                "created_by_user_id",
                require_uuid_v4(self.created_by_user_id, "created_by_user_id"),
            )
        self._validate_scope_and_roles()
        self._validate_status_timestamps()

    def _validate_scope_and_roles(self) -> None:
        if self.branch_scope_mode is BranchScopeMode.EXPLICIT_BRANCHES:
            if not self.allowed_branch_ids:
                if self.status is MembershipStatus.ACTIVE:
                    raise InvalidMembershipFieldError(
                        "Membresía activa con explicit_branches requiere allowed_branch_ids."
                    )
        elif self.branch_scope_mode is BranchScopeMode.ALL_BRANCHES:
            if self.allowed_branch_ids:
                raise InvalidMembershipFieldError(
                    "all_branches no admite allowed_branch_ids no vacío."
                )
        if GymRole.BRANCH_ADMIN in self.gym_roles:
            if self.branch_scope_mode is not BranchScopeMode.EXPLICIT_BRANCHES:
                raise InvalidGymRoleAssignmentError(
                    "branch_admin exige branch_scope_mode explicit_branches."
                )
            if self.status is MembershipStatus.ACTIVE and not self.allowed_branch_ids:
                raise InvalidGymRoleAssignmentError(
                    "branch_admin activo requiere sucursales explícitas."
                )

    def _validate_status_timestamps(self) -> None:
        if self.status is MembershipStatus.INVITED and self.invited_at is None:
            raise InvalidMembershipFieldError("status invited requiere invited_at.")
        if self.status is MembershipStatus.ACTIVE and self.accepted_at is None:
            raise InvalidMembershipFieldError("status active requiere accepted_at.")

    @classmethod
    def create_invited(
        cls,
        *,
        user_id: str,
        tenant_id: str,
        gym_roles: frozenset[GymRole],
        branch_scope_mode: BranchScopeMode,
        allowed_branch_ids: frozenset[str] | None = None,
        membership_id: str | None = None,
        created_by_user_id: str | None = None,
        now: datetime | None = None,
    ) -> TenantMembership:
        moment = ensure_utc(now or datetime.now(UTC))
        return cls(
            membership_id=membership_id or new_uuid(),
            user_id=user_id,
            tenant_id=tenant_id,
            status=MembershipStatus.INVITED,
            branch_scope_mode=branch_scope_mode,
            allowed_branch_ids=allowed_branch_ids,
            gym_roles=gym_roles,
            authz_epoch=0,
            invited_at=moment,
            accepted_at=None,
            created_at=moment,
            updated_at=moment,
            created_by_user_id=created_by_user_id,
        )

    @classmethod
    def create_active(
        cls,
        *,
        user_id: str,
        tenant_id: str,
        gym_roles: frozenset[GymRole],
        branch_scope_mode: BranchScopeMode,
        allowed_branch_ids: frozenset[str] | None = None,
        membership_id: str | None = None,
        created_by_user_id: str | None = None,
        now: datetime | None = None,
    ) -> TenantMembership:
        moment = ensure_utc(now or datetime.now(UTC))
        return cls(
            membership_id=membership_id or new_uuid(),
            user_id=user_id,
            tenant_id=tenant_id,
            status=MembershipStatus.ACTIVE,
            branch_scope_mode=branch_scope_mode,
            allowed_branch_ids=allowed_branch_ids,
            gym_roles=gym_roles,
            authz_epoch=0,
            invited_at=moment,
            accepted_at=moment,
            created_at=moment,
            updated_at=moment,
            created_by_user_id=created_by_user_id,
        )

    @classmethod
    def from_persistence(cls, raw: Mapping[str, Any]) -> TenantMembership:
        roles_raw = raw.get("gym_roles") or []
        roles = frozenset(GymRole(str(r)) for r in roles_raw)
        branches_raw = raw.get("allowed_branch_ids")
        branches = frozenset(str(b) for b in branches_raw) if branches_raw is not None else None
        invited = raw.get("invited_at")
        accepted = raw.get("accepted_at")
        creator = raw.get("created_by_user_id")
        return cls(
            membership_id=str(raw["_id"]),
            user_id=str(raw["user_id"]),
            tenant_id=str(raw["tenant_id"]),
            status=MembershipStatus(str(raw["status"])),
            branch_scope_mode=BranchScopeMode(str(raw["branch_scope_mode"])),
            allowed_branch_ids=branches,
            gym_roles=roles,
            authz_epoch=int(raw["authz_epoch"]),
            invited_at=parse_utc_datetime(invited) if invited is not None else None,
            accepted_at=parse_utc_datetime(accepted) if accepted is not None else None,
            created_at=parse_utc_datetime(raw["created_at"]),
            updated_at=parse_utc_datetime(raw["updated_at"]),
            created_by_user_id=str(creator) if creator is not None else None,
        )

    def is_operational(self) -> bool:
        return self.status is MembershipStatus.ACTIVE

    def context_allowed_branch_ids(self) -> frozenset[str] | None:
        """Derivación para TenantContext (None = sin restricción explícita en contexto)."""
        if self.branch_scope_mode is BranchScopeMode.ALL_BRANCHES:
            return None
        return self.allowed_branch_ids

    def _transition_to(
        self,
        target: MembershipStatus,
        *,
        now: datetime,
        **extra: Any,
    ) -> TenantMembership:
        allowed = MEMBERSHIP_ALLOWED_TRANSITIONS.get(self.status, frozenset())
        if target not in allowed:
            raise InvalidMembershipStateTransitionError(
                f"Transición {self.status.value!r} → {target.value!r} no permitida."
            )
        moment = ensure_utc(now)
        bumped_epoch = self.authz_epoch + 1
        return replace(
            self,
            status=target,
            authz_epoch=bumped_epoch,
            updated_at=moment,
            **extra,
        )

    def accept_invitation(self, *, now: datetime | None = None) -> TenantMembership:
        if self.status is not MembershipStatus.INVITED:
            raise InvalidMembershipStateTransitionError(
                "accept_invitation solo aplica a membresías invited."
            )
        moment = ensure_utc(now or datetime.now(UTC))
        return self._transition_to(
            MembershipStatus.ACTIVE,
            now=moment,
            accepted_at=moment,
        )

    def suspend(self, *, now: datetime | None = None) -> TenantMembership:
        moment = ensure_utc(now or datetime.now(UTC))
        return self._transition_to(MembershipStatus.SUSPENDED, now=moment)

    def reactivate(self, *, now: datetime | None = None) -> TenantMembership:
        if self.accepted_at is None:
            raise InvalidMembershipFieldError("Reactivación requiere accepted_at previo.")
        moment = ensure_utc(now or datetime.now(UTC))
        return self._transition_to(MembershipStatus.ACTIVE, now=moment)

    def revoke(self, *, now: datetime | None = None) -> TenantMembership:
        moment = ensure_utc(now or datetime.now(UTC))
        return self._transition_to(MembershipStatus.REVOKED, now=moment)

    def apply_reinvite_grant(
        self,
        *,
        gym_roles: frozenset[GymRole],
        branch_scope_mode: BranchScopeMode,
        allowed_branch_ids: frozenset[str] | None = None,
        now: datetime | None = None,
    ) -> TenantMembership:
        """Tras revocación: nuevo grant explícito (no hereda roles ni sucursales previos)."""
        if self.status is not MembershipStatus.REVOKED:
            raise InvalidMembershipStateTransitionError(
                "apply_reinvite_grant solo aplica a membresías revoked."
            )
        moment = ensure_utc(now or datetime.now(UTC))
        return TenantMembership(
            membership_id=self.membership_id,
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            status=MembershipStatus.INVITED,
            branch_scope_mode=branch_scope_mode,
            allowed_branch_ids=allowed_branch_ids,
            gym_roles=_normalize_gym_roles(gym_roles),
            authz_epoch=self.authz_epoch + 1,
            invited_at=moment,
            accepted_at=None,
            created_at=self.created_at,
            updated_at=moment,
            created_by_user_id=self.created_by_user_id,
        )

    def with_roles(
        self,
        gym_roles: frozenset[GymRole],
        *,
        now: datetime | None = None,
    ) -> TenantMembership:
        moment = ensure_utc(now or datetime.now(UTC))
        return replace(
            self,
            gym_roles=_normalize_gym_roles(gym_roles),
            authz_epoch=self.authz_epoch + 1,
            updated_at=moment,
        )

    def with_branch_scope(
        self,
        *,
        branch_scope_mode: BranchScopeMode,
        allowed_branch_ids: frozenset[str] | None,
        now: datetime | None = None,
    ) -> TenantMembership:
        moment = ensure_utc(now or datetime.now(UTC))
        updated = replace(
            self,
            branch_scope_mode=branch_scope_mode,
            allowed_branch_ids=allowed_branch_ids,
            authz_epoch=self.authz_epoch + 1,
            updated_at=moment,
        )
        return TenantMembership(
            membership_id=updated.membership_id,
            user_id=updated.user_id,
            tenant_id=updated.tenant_id,
            status=updated.status,
            branch_scope_mode=updated.branch_scope_mode,
            allowed_branch_ids=updated.allowed_branch_ids,
            gym_roles=updated.gym_roles,
            authz_epoch=updated.authz_epoch,
            invited_at=updated.invited_at,
            accepted_at=updated.accepted_at,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
            created_by_user_id=updated.created_by_user_id,
        )
