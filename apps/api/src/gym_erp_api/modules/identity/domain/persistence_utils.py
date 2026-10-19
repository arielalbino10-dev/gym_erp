"""Utilidades de rehidratación desde persistencia (sin PyMongo)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from gym_erp_api.modules.identity.domain.errors import InvalidIdentityPersistenceError


def parse_utc_datetime(value: Any, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise InvalidIdentityPersistenceError(f"{field_name} debe ser datetime timezone-aware.")
    if value.tzinfo is None:
        raise InvalidIdentityPersistenceError(f"{field_name} debe incluir zona horaria.")
    from gym_erp_api.modules.identity.domain.time_utils import truncate_utc_to_milliseconds

    return truncate_utc_to_milliseconds(value.astimezone(UTC))
