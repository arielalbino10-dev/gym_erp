import base64
import os

import pytest
from pydantic import SecretStr, ValidationError

from gym_erp_api.core.config import Settings


def _production_base(**overrides):
    key = base64.b64encode(os.urandom(32)).decode()
    defaults = dict(
        app_env="production",
        mongodb_uri=None,
        allow_insecure_cookies=False,
        require_https_env=True,
        rate_limit_fail_closed=True,
        platform_mfa_encryption_required=True,
        platform_mfa_encryption_key=SecretStr(key),
        trusted_proxy_ips="10.0.0.1",
        cors_origins="https://app.example.com",
    )
    defaults.update(overrides)
    return Settings(**defaults)


def test_production_rejects_insecure_cookies():
    with pytest.raises(ValidationError, match="ALLOW_INSECURE_COOKIES"):
        _production_base(allow_insecure_cookies=True)


def test_cors_rejects_wildcard():
    with pytest.raises(ValidationError, match="comodines"):
        Settings(
            app_env="test",
            mongodb_uri=None,
            cors_origins="*",
        )


def test_production_rejects_https_disabled():
    with pytest.raises(ValidationError, match="REQUIRE_HTTPS"):
        _production_base(require_https_env=False)


def test_production_rejects_rate_limit_fail_open():
    with pytest.raises(ValidationError, match="RATE_LIMIT_FAIL_CLOSED"):
        _production_base(rate_limit_fail_closed=False)


def test_production_rejects_localhost_cors():
    with pytest.raises(ValidationError, match="localhost"):
        _production_base(cors_origins="https://127.0.0.1:5173")


def test_production_rejects_empty_trusted_proxies():
    with pytest.raises(ValidationError, match="TRUSTED_PROXY_IPS"):
        _production_base(trusted_proxy_ips="")


def test_production_accepts_valid_security_profile():
    settings = _production_base()
    assert settings.https_required is True


def test_app_env_must_be_known():
    with pytest.raises(ValidationError, match="APP_ENV inválido"):
        Settings(app_env="prod", mongodb_uri=None)
