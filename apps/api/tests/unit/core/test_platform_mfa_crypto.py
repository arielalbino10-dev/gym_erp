import base64
import os

import pytest
from pydantic import SecretStr

from gym_erp_api.core.config import Settings
from gym_erp_api.core.platform_mfa_crypto import (
    is_known_test_mfa_key,
    known_test_mfa_key_base64,
    resolve_platform_mfa_aes256_key,
)
from gym_erp_api.modules.identity.application.errors import PlatformMfaConfigurationError


def test_rejects_missing_key_when_required():
    with pytest.raises(PlatformMfaConfigurationError):
        Settings(
            app_env="production",
            mongodb_uri=None,
            platform_mfa_encryption_required=True,
        )


def test_rejects_invalid_base64():
    with pytest.raises(PlatformMfaConfigurationError):
        Settings(
            app_env="test",
            mongodb_uri=None,
            platform_mfa_encryption_key=SecretStr("not-valid-base64!!!"),
        )


def test_rejects_wrong_length():
    short = base64.b64encode(b"x" * 16).decode()
    with pytest.raises(PlatformMfaConfigurationError):
        Settings(
            app_env="test",
            mongodb_uri=None,
            platform_mfa_encryption_key=SecretStr(short),
        )


def test_accepts_valid_key_in_test_env():
    key_b64 = base64.b64encode(os.urandom(32)).decode()
    settings = Settings(
        app_env="test",
        mongodb_uri=None,
        platform_mfa_encryption_key=SecretStr(key_b64),
    )
    key = resolve_platform_mfa_aes256_key(settings)
    assert len(key) == 32


def test_production_rejects_test_key():
    with pytest.raises(PlatformMfaConfigurationError):
        Settings(
            app_env="production",
            mongodb_uri=None,
            platform_mfa_encryption_key=SecretStr(known_test_mfa_key_base64()),
        )


def test_test_key_detector():
    assert is_known_test_mfa_key(bytes(range(32)))
