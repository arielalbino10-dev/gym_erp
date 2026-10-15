"""Entidad Branch — sucursal operational (ADR-0009)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any

from gym_erp_api.modules.organization.domain.enums import (
    BRANCH_ALLOWED_TRANSITIONS,
    BranchStatus,
)
from gym_erp_api.modules.organization.domain.errors import (
    InvalidOrganizationPersistenceError,
    InvalidOrganizationStateTransitionError,
    OrganizationImmutabilityError,
)
from gym_erp_api.modules.organization.domain.persistence_utils import (
    ensure_utc,
    parse_utc_datetime,
)
from gym_erp_api.modules.organization.domain.validators import (
    normalize_branch_code,
    require_non_empty_name,
    require_timezone,
    require_uuid_v4,
)
from gym_erp_api.modules.organization.domain.value_objects import BranchAddress
from gym_erp_api.shared_kernel.identifiers import new_uuid

DEFAULT_BRANCH_TIMEZONE = "America/Mexico_City"


@dataclass(frozen=True, slots=True)
class Branch:
    branch_id: str
    tenant_id: str
    name: str
    status: BranchStatus
    timezone: str
    created_at: datetime
    updated_at: datetime
    code: str | None = None
    address: BranchAddress | None = None
    created_by_user_id: str | None = None
    updated_by_user_id: str | None = None

    @classmethod
    def create(
        cls,
        *,
        tenant_id: str,
        name: str,
        timezone: str = DEFAULT_BRANCH_TIMEZONE,
        code: str | None = None,
        address: BranchAddress | None = None,
        branch_id: str | None = None,
        created_by_user_id: str | None = None,
        now: datetime | None = None,
    ) -> Branch:
        tid = require_uuid_v4(tenant_id, "tenant_id")
        bid = require_uuid_v4(branch_id or new_uuid(), "branch_id")
        branch_name = require_non_empty_name(name, "name")
        tz = require_timezone(timezone)
        normalized_code = normalize_branch_code(code)
        creator = (
            require_uuid_v4(created_by_user_id, "created_by_user_id")
            if created_by_user_id is not None
            else None
        )
        moment = ensure_utc(now or datetime.now(UTC))
        return cls(
            branch_id=bid,
            tenant_id=tid,
            name=branch_name,
            status=BranchStatus.ACTIVE,
            timezone=tz,
            code=normalized_code,
            address=address,
            created_at=moment,
            updated_at=moment,
            created_by_user_id=creator,
        )

    def transition_status(
        self,
        new_status: BranchStatus,
        *,
        updated_by_user_id: str | None = None,
        now: datetime | None = None,
    ) -> Branch:
        target = BranchStatus(new_status)
        allowed = BRANCH_ALLOWED_TRANSITIONS.get(self.status, frozenset())
        if target not in allowed:
            raise InvalidOrganizationStateTransitionError(
                f"Transición de sucursal no permitida: {self.status.value} → {target.value}."
            )
        updater = (
            require_uuid_v4(updated_by_user_id, "updated_by_user_id")
            if updated_by_user_id is not None
            else self.updated_by_user_id
        )
        moment = ensure_utc(now or datetime.now(UTC))
        return replace(
            self,
            status=target,
            updated_at=moment,
            updated_by_user_id=updater,
        )

    @classmethod
    def from_persistence(cls, raw: Mapping[str, Any]) -> Branch:
        if not isinstance(raw, Mapping):
            raise InvalidOrganizationPersistenceError("El documento branch debe ser un mapping.")
        raw_bid = raw.get("branch_id") if raw.get("branch_id") is not None else raw.get("_id")
        if raw_bid is None:
            raise InvalidOrganizationPersistenceError("Falta branch_id en documento.")
        branch_id = require_uuid_v4(str(raw_bid), "branch_id")
        if raw.get("tenant_id") is None:
            raise InvalidOrganizationPersistenceError("Falta tenant_id en documento branch.")
        tenant_id = require_uuid_v4(str(raw["tenant_id"]), "tenant_id")
        try:
            status = BranchStatus(str(raw["status"]))
        except (KeyError, ValueError) as exc:
            raise InvalidOrganizationPersistenceError("status branch inválido.") from exc
        name = require_non_empty_name(str(raw["name"]), "name")
        tz = require_timezone(str(raw["timezone"]))
        code_raw = raw.get("code")
        code = normalize_branch_code(str(code_raw)) if code_raw is not None else None
        address = _address_from_persistence(raw.get("address"))
        creator = raw.get("created_by_user_id")
        updater = raw.get("updated_by_user_id")
        return cls(
            branch_id=branch_id,
            tenant_id=tenant_id,
            name=name,
            status=status,
            timezone=tz,
            code=code,
            address=address,
            created_at=parse_utc_datetime(raw.get("created_at"), "created_at"),
            updated_at=parse_utc_datetime(raw.get("updated_at"), "updated_at"),
            created_by_user_id=(
                require_uuid_v4(str(creator), "created_by_user_id") if creator is not None else None
            ),
            updated_by_user_id=(
                require_uuid_v4(str(updater), "updated_by_user_id") if updater is not None else None
            ),
        )

    def with_reassigned_tenant(self, _tenant_id: str) -> Branch:
        raise OrganizationImmutabilityError("tenant_id de sucursal es inmutable.")

    def with_new_branch_id(self, _branch_id: str) -> Branch:
        raise OrganizationImmutabilityError("branch_id es inmutable.")


def _address_from_persistence(raw: Any) -> BranchAddress | None:
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise InvalidOrganizationPersistenceError("address debe ser un documento.")
    return BranchAddress.from_persistence(raw)
