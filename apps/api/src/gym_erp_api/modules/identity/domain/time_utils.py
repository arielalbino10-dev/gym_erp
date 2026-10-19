"""Marcas de tiempo alineadas con precisión BSON (milisegundos)."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now_ms() -> datetime:
    return truncate_utc_to_milliseconds(datetime.now(UTC))


def truncate_utc_to_milliseconds(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    else:
        moment = moment.astimezone(UTC)
    micro = (moment.microsecond // 1000) * 1000
    return moment.replace(microsecond=micro)
