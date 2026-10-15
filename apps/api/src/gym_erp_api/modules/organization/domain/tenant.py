"""Entidad Tenant — empresa cliente SaaS (platform, ADR-0009)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any

from gym_erp_api.modules.organization.domain.enums import (
    TENANT_ALLOWED_TRANSITIONS,
    TenantStatus,
)
from gym_erp_api.modules.organization.domain.errors import (
    InvalidOrganizationPersistenceError,
    InvalidOrganizationStateTransitionError,
)
from gym_erp_api.modules.organization.domain.persistence_utils import (
    ensure_utc,
    parse_utc_datetime,
)
from gym_erp_api.modules.organization.domain.validators import (
    normalize_commercial_email,
    require_non_empty_name,
    require_timezone,
    require_uuid_v4,
)
from gym_erp_api.shared_kernel.identifiers import new_uuid

DEFAULT_TENANT_TIMEZONE = "America/Mexico_City"


@dataclass(frozen=True, slots=True)
class Tenant:
    tenant_id: str
    legal_name: str
    display_name: str
    status: TenantStatus
    timezone: str
    created_at: datetime
    updated_at: datetime
    commercial_email: str | None = None
    commercial_email_normalized: str | None = None
    created_by_user_id: str | None = None
    updated_by_user_id: str | None = None

    @classmethod
    def create(
        cls,
        *,
        legal_name: str,
        display_name: str,
        timezone: str = DEFAULT_TENANT_TIMEZONE,
        commercial_email: str | None = None,
        tenant_id: str | None = None,
        created_by_user_id: str | None = None,
        now: datetime | None = None,
    ) -> Tenant:
        tid = require_uuid_v4(tenant_id or new_uuid(), "tenant_id")
        legal = require_non_empty_name(legal_name, "legal_name")
        display = require_non_empty_name(display_name, "display_name")
        tz = require_timezone(timezone)
        email_visible, email_normalized = normalize_commercial_email(commercial_email)
        creator = (
            require_uuid_v4(created_by_user_id, "created_by_user_id")
            if created_by_user_id is not None
            else None
        )
        moment = ensure_utc(now or datetime.now(UTC))
        return cls(
            tenant_id=tid,
            legal_name=legal,
            display_name=display,
            status=TenantStatus.PROVISIONING,
            timezone=tz,
            commercial_email=email_visible,
            commercial_email_normalized=email_normalized,
            created_at=moment,
            updated_at=moment,
            created_by_user_id=creator,
        )

    def transition_status(
        self,
        new_status: TenantStatus,
        *,
        updated_by_user_id: str | None = None,
        now: datetime | None = None,
    ) -> Tenant:
        target = TenantStatus(new_status)
        allowed = TENANT_ALLOWED_TRANSITIONS.get(self.status, frozenset())
        if target not in allowed:
            raise InvalidOrganizationStateTransitionError(
                f"Transición de tenant no permitida: {self.status.value} → {target.value}."
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

    def with_updated_names(
        self,
        *,
        legal_name: str | None = None,
        display_name: str | None = None,
        updated_by_user_id: str | None = None,
        now: datetime | None = None,
    ) -> Tenant:
        if legal_name is not None:
            legal = require_non_empty_name(legal_name, "legal_name")
        else:
            legal = self.legal_name
        display = (
            require_non_empty_name(display_name, "display_name")
            if display_name is not None
            else self.display_name
        )
        updater = (
            require_uuid_v4(updated_by_user_id, "updated_by_user_id")
            if updated_by_user_id is not None
            else self.updated_by_user_id
        )
        moment = ensure_utc(now or datetime.now(UTC))
        return replace(
            self,
            legal_name=legal,
            display_name=display,
            updated_at=moment,
            updated_by_user_id=updater,
        )

    @classmethod
    def from_persistence(cls, raw: Mapping[str, Any]) -> Tenant:
        if not isinstance(raw, Mapping):
            raise InvalidOrganizationPersistenceError("El documento tenant debe ser un mapping.")
        raw_id = raw.get("tenant_id") if raw.get("tenant_id") is not None else raw.get("_id")
        if raw_id is None:
            raise InvalidOrganizationPersistenceError("Falta tenant_id en documento.")
        tenant_id = require_uuid_v4(str(raw_id), "tenant_id")
        try:
            status = TenantStatus(str(raw["status"]))
        except (KeyError, ValueError) as exc:
            raise InvalidOrganizationPersistenceError("status tenant inválido.") from exc
        legal = require_non_empty_name(str(raw["legal_name"]), "legal_name")
        display = require_non_empty_name(str(raw["display_name"]), "display_name")
        tz = require_timezone(str(raw["timezone"]))
        email_raw = raw.get("commercial_email")
        email_visible: str | None
        email_normalized: str | None
        if email_raw is None:
            email_visible = None
            email_normalized = None
        else:
            email_visible, email_normalized = normalize_commercial_email(str(email_raw))
            stored_norm = raw.get("commercial_email_normalized")
            if stored_norm is not None and str(stored_norm) != email_normalized:
                raise InvalidOrganizationPersistenceError(
                    "commercial_email_normalized inconsistente con commercial_email."
                )
        creator = raw.get("created_by_user_id")
        updater = raw.get("updated_by_user_id")
        return cls(
            tenant_id=tenant_id,
            legal_name=legal,
            display_name=display,
            status=status,
            timezone=tz,
            commercial_email=email_visible,
            commercial_email_normalized=email_normalized,
            created_at=parse_utc_datetime(raw.get("created_at"), "created_at"),
            updated_at=parse_utc_datetime(raw.get("updated_at"), "updated_at"),
            created_by_user_id=(
                require_uuid_v4(str(creator), "created_by_user_id") if creator is not None else None
            ),
            updated_by_user_id=(
                require_uuid_v4(str(updater), "updated_by_user_id") if updater is not None else None
            ),
        )
