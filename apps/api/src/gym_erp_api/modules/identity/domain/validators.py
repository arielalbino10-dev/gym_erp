"""Validadores del dominio identity."""

from __future__ import annotations

import re

from gym_erp_api.modules.identity.domain.errors import (
    InvalidIdentityFieldError,
    InvalidIdentityIdentifierError,
)
from gym_erp_api.shared_kernel.email_normalization import normalize_email
from gym_erp_api.shared_kernel.identifiers import assert_uuid_v4

_EMAIL_FORMAT = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def require_user_uuid_v4(value: str, field_name: str = "user_id") -> str:
    try:
        return assert_uuid_v4(value, field_name)
    except Exception as exc:
        raise InvalidIdentityIdentifierError(str(exc)) from exc


def normalize_identity_email(value: str) -> tuple[str, str]:
    """Devuelve (email visible recortado, email_normalized)."""
    if not isinstance(value, str):
        raise InvalidIdentityFieldError("email debe ser una cadena.")
    visible = value.strip()
    if not visible:
        raise InvalidIdentityFieldError("email no puede estar vacío.")
    try:
        normalized = normalize_email(visible)
    except ValueError as exc:
        raise InvalidIdentityFieldError(str(exc)) from exc
    if not _EMAIL_FORMAT.fullmatch(normalized):
        raise InvalidIdentityFieldError("email con formato inválido.")
    return visible, normalized


def require_non_negative_credential_version(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise InvalidIdentityFieldError("credential_version debe ser un entero.")
    if value < 0:
        raise InvalidIdentityFieldError("credential_version no puede ser negativo.")
    return value
