"""Utilidades BSON / UTC para access (platform)."""

from __future__ import annotations

from datetime import UTC, datetime


def ensure_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def parse_utc_datetime(raw: object) -> datetime:
    if not isinstance(raw, datetime):
        raise TypeError("Se esperaba datetime UTC en documento de membresía.")
    return ensure_utc(raw)
