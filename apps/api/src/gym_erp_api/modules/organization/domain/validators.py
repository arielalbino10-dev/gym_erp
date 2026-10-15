"""Validadores reutilizables del dominio organization."""

from __future__ import annotations

import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from gym_erp_api.modules.organization.domain.errors import (
    InvalidOrganizationFieldError,
    InvalidOrganizationIdentifierError,
)
from gym_erp_api.shared_kernel.email_normalization import normalize_email
from gym_erp_api.shared_kernel.identifiers import assert_uuid_v4

_NAME_MIN_LEN = 1
_NAME_MAX_LEN = 200
_BRANCH_CODE_PATTERN = re.compile(r"^[A-Z0-9_-]{2,32}$")
_COUNTRY_CODE_PATTERN = re.compile(r"^[A-Z]{2}$")


def require_uuid_v4(value: str, field_name: str) -> str:
    try:
        return assert_uuid_v4(value, field_name)
    except Exception as exc:
        raise InvalidOrganizationIdentifierError(str(exc)) from exc


def require_non_empty_name(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise InvalidOrganizationFieldError(f"{field_name} debe ser una cadena.")
    trimmed = value.strip()
    if len(trimmed) < _NAME_MIN_LEN:
        raise InvalidOrganizationFieldError(f"{field_name} no puede estar vacío.")
    if len(trimmed) > _NAME_MAX_LEN:
        raise InvalidOrganizationFieldError(
            f"{field_name} no puede superar {_NAME_MAX_LEN} caracteres."
        )
    return trimmed


def require_timezone(value: str, field_name: str = "timezone") -> str:
    if not isinstance(value, str):
        raise InvalidOrganizationFieldError(f"{field_name} debe ser una cadena.")
    tz = value.strip()
    if not tz:
        raise InvalidOrganizationFieldError(f"{field_name} no puede estar vacío.")
    try:
        ZoneInfo(tz)
    except ZoneInfoNotFoundError as exc:
        raise InvalidOrganizationFieldError(f"{field_name} IANA inválido: {tz!r}.") from exc
    return tz


def normalize_branch_code(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidOrganizationFieldError("code debe ser una cadena.")
    normalized = value.strip().upper()
    if not normalized:
        return None
    if not _BRANCH_CODE_PATTERN.fullmatch(normalized):
        raise InvalidOrganizationFieldError("code debe tener 2–32 caracteres (A-Z, 0-9, _, -).")
    return normalized


def normalize_commercial_email(
    value: str | None,
) -> tuple[str | None, str | None]:
    """Devuelve (email visible, email_normalized) o (None, None)."""
    if value is None:
        return None, None
    if not isinstance(value, str):
        raise InvalidOrganizationFieldError("commercial_email debe ser una cadena.")
    visible = value.strip()
    if not visible:
        return None, None
    try:
        normalized = normalize_email(visible)
    except ValueError as exc:
        raise InvalidOrganizationFieldError(str(exc)) from exc
    return visible, normalized


def require_country_code(value: str) -> str:
    code = value.strip().upper()
    if not _COUNTRY_CODE_PATTERN.fullmatch(code):
        raise InvalidOrganizationFieldError("country_code debe ser ISO 3166-1 alpha-2.")
    return code
