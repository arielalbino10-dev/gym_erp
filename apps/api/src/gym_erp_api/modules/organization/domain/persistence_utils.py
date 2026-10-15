"""Utilidades de rehidratación desde persistencia (sin PyMongo)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from gym_erp_api.modules.organization.domain.errors import InvalidOrganizationPersistenceError


def parse_utc_datetime(value: Any, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise InvalidOrganizationPersistenceError(f"{field_name} debe ser datetime timezone-aware.")
    if value.tzinfo is None:
        raise InvalidOrganizationPersistenceError(f"{field_name} debe incluir zona horaria.")
    return value.astimezone(UTC)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Las marcas de tiempo de auditoría deben ser timezone-aware (UTC).")
    return value.astimezone(UTC)
