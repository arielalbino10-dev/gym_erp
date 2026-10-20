"""Resolución segura de clave AES-256-GCM para MFA platform (sin secretos en logs)."""

from __future__ import annotations

import base64
import binascii
from typing import Final

from gym_erp_api.core.config import Settings
from gym_erp_api.modules.identity.application.errors import PlatformMfaConfigurationError

_TEST_KEY_PLAINTEXT: Final[bytes] = bytes(range(32))
_TEST_KEY_B64: Final[str] = base64.b64encode(_TEST_KEY_PLAINTEXT).decode("ascii")


def known_test_mfa_key_base64() -> str:
    """Referencia para tests; no usar en producción."""
    return _TEST_KEY_B64


def _decode_aes256_key(raw: str) -> bytes:
    cleaned = raw.strip()
    if not cleaned:
        raise PlatformMfaConfigurationError("Clave MFA platform ausente o vacía.")
    try:
        key = base64.b64decode(cleaned, validate=True)
    except binascii.Error as exc:
        raise PlatformMfaConfigurationError(
            "Clave MFA platform debe ser base64 válido (32 bytes decodificados)."
        ) from exc
    if len(key) != 32:
        raise PlatformMfaConfigurationError(
            "Clave MFA platform debe decodificar exactamente 32 bytes."
        )
    return key


def is_known_test_mfa_key(key: bytes) -> bool:
    return key == _TEST_KEY_PLAINTEXT


def resolve_platform_mfa_aes256_key(settings: Settings) -> bytes:
    """Obtiene la clave MFA; falla cerrado si la plataforma la exige y falta."""
    if settings.platform_mfa_encryption_key is None:
        if settings.require_platform_mfa_encryption_key:
            raise PlatformMfaConfigurationError(
                "MFA platform requiere MFA_PLATFORM_ENCRYPTION_KEY configurada."
            )
        raise PlatformMfaConfigurationError(
            "MFA platform no configurado (sin MFA_PLATFORM_ENCRYPTION_KEY)."
        )
    secret = settings.platform_mfa_encryption_key.get_secret_value()
    key = _decode_aes256_key(secret)
    if settings.app_env.strip().lower() == "production" and is_known_test_mfa_key(key):
        raise PlatformMfaConfigurationError("Clave MFA de pruebas prohibida en producción.")
    return key
