"""Command y result de CreateOrganization (H1-D.3.3.1 — sin persistencia)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from gym_erp_api.modules.organization.application.errors import IdempotencyKeyRequiredError
from gym_erp_api.modules.organization.domain.enums import BranchStatus, TenantStatus
from gym_erp_api.modules.organization.domain.persistence_utils import ensure_utc
from gym_erp_api.modules.organization.domain.tenant import DEFAULT_TENANT_TIMEZONE
from gym_erp_api.modules.organization.domain.validators import (
    normalize_branch_code,
    normalize_commercial_email,
    require_non_empty_name,
    require_timezone,
    require_uuid_v4,
)
from gym_erp_api.modules.organization.domain.value_objects import BranchAddress

_IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")


def _validate_idempotency_key(raw: str | None) -> str:
    if raw is None:
        raise IdempotencyKeyRequiredError("idempotency_key es obligatoria.")
    key = raw.strip()
    if not key:
        raise IdempotencyKeyRequiredError("idempotency_key es obligatoria.")
    if not _IDEMPOTENCY_KEY_PATTERN.fullmatch(key):
        raise IdempotencyKeyRequiredError(
            "idempotency_key debe tener 8–128 caracteres [A-Za-z0-9._:-]."
        )
    return key


def _optional_correlation_id(raw: str | None) -> str | None:
    if raw is None:
        return None
    trimmed = raw.strip()
    return trimmed or None


@dataclass(frozen=True, slots=True)
class CreateOrganizationCommand:
    """Entrada normalizada para el alta transaccional futuro (sin tenant_id/branch_id externos)."""

    idempotency_key: str
    legal_name: str
    display_name: str
    tenant_timezone: str
    branch_name: str
    branch_timezone: str
    commercial_email: str | None = None
    commercial_email_normalized: str | None = None
    branch_code: str | None = None
    branch_address: BranchAddress | None = None
    created_by_user_id: str | None = None
    correlation_id: str | None = None

    @classmethod
    def build(
        cls,
        *,
        idempotency_key: str,
        legal_name: str,
        display_name: str,
        branch_name: str,
        tenant_timezone: str = DEFAULT_TENANT_TIMEZONE,
        branch_timezone: str | None = None,
        commercial_email: str | None = None,
        branch_code: str | None = None,
        branch_address: BranchAddress | None = None,
        created_by_user_id: str | None = None,
        correlation_id: str | None = None,
    ) -> CreateOrganizationCommand:
        key = _validate_idempotency_key(idempotency_key)
        legal = require_non_empty_name(legal_name, "legal_name")
        display = require_non_empty_name(display_name, "display_name")
        branch = require_non_empty_name(branch_name, "branch_name")
        tenant_tz = require_timezone(tenant_timezone, "tenant_timezone")
        branch_tz = (
            tenant_tz
            if branch_timezone is None
            else require_timezone(branch_timezone, "branch_timezone")
        )
        email_visible, email_normalized = normalize_commercial_email(commercial_email)
        code = normalize_branch_code(branch_code)
        creator = (
            require_uuid_v4(created_by_user_id, "created_by_user_id")
            if created_by_user_id is not None
            else None
        )
        return cls(
            idempotency_key=key,
            legal_name=legal,
            display_name=display,
            tenant_timezone=tenant_tz,
            branch_name=branch,
            branch_timezone=branch_tz,
            commercial_email=email_visible,
            commercial_email_normalized=email_normalized,
            branch_code=code,
            branch_address=branch_address,
            created_by_user_id=creator,
            correlation_id=_optional_correlation_id(correlation_id),
        )


@dataclass(frozen=True, slots=True)
class CreateOrganizationResult:
    tenant_id: str
    branch_id: str
    tenant_status: TenantStatus
    branch_status: BranchStatus
    idempotency_replayed: bool
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at", ensure_utc(self.created_at))
