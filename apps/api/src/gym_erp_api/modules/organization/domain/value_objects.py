"""Objetos de valor del dominio organization."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from gym_erp_api.modules.organization.domain.errors import (
    InvalidOrganizationFieldError,
    InvalidOrganizationPersistenceError,
)
from gym_erp_api.modules.organization.domain.validators import (
    require_country_code,
    require_non_empty_name,
)


@dataclass(frozen=True, slots=True)
class BranchAddress:
    """Dirección mínima de sucursal (opcional en Branch).

    Si se proporciona, exige al menos ``line1`` y ``city`` (MVP México).
    ``country_code`` por defecto ``MX``.
    """

    line1: str
    city: str
    line2: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country_code: str = "MX"

    @classmethod
    def create(
        cls,
        *,
        line1: str,
        city: str,
        line2: str | None = None,
        state: str | None = None,
        postal_code: str | None = None,
        country_code: str = "MX",
    ) -> BranchAddress:
        normalized_line1 = require_non_empty_name(line1, "address.line1")
        normalized_city = require_non_empty_name(city, "address.city")
        normalized_line2 = _optional_trimmed(line2, "address.line2")
        normalized_state = _optional_trimmed(state, "address.state")
        normalized_postal = _optional_trimmed(postal_code, "address.postal_code")
        normalized_country = require_country_code(country_code)
        return cls(
            line1=normalized_line1,
            city=normalized_city,
            line2=normalized_line2,
            state=normalized_state,
            postal_code=normalized_postal,
            country_code=normalized_country,
        )

    @classmethod
    def from_persistence(cls, raw: Mapping[str, Any]) -> BranchAddress:
        if raw.get("line1") is None or raw.get("city") is None:
            raise InvalidOrganizationPersistenceError("address incompleta en persistencia.")
        return cls.create(
            line1=str(raw["line1"]),
            city=str(raw["city"]),
            line2=str(raw["line2"]) if raw.get("line2") is not None else None,
            state=str(raw["state"]) if raw.get("state") is not None else None,
            postal_code=str(raw["postal_code"]) if raw.get("postal_code") is not None else None,
            country_code=str(raw.get("country_code", "MX")),
        )


def _optional_trimmed(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidOrganizationFieldError(f"{field_name} debe ser una cadena.")
    trimmed = value.strip()
    return trimmed or None
