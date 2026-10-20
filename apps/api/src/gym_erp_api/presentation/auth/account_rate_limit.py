"""Claves de rate limit sin almacenar email en claro."""

from __future__ import annotations

import hashlib

from gym_erp_api.modules.identity.domain.errors import InvalidIdentityFieldError
from gym_erp_api.modules.identity.domain.validators import normalize_identity_email


def login_account_rate_limit_key(email: str) -> str:
    try:
        _, normalized = normalize_identity_email(email)
    except InvalidIdentityFieldError:
        normalized = email.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
