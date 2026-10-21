import base64
import os
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

from gym_erp_api.core.config import Settings
from gym_erp_api.infrastructure.identity.identity_container import build_identity_infrastructure
from gym_erp_api.infrastructure.mongo.mongo_databases import MongoDatabases
from gym_erp_api.modules.identity.application.errors import PlatformMfaConfigurationError


def _settings_with_mfa_key() -> Settings:
    key_b64 = base64.b64encode(os.urandom(32)).decode()
    return Settings(
        app_env="test",
        mongodb_uri=None,
        platform_mfa_encryption_key=SecretStr(key_b64),
    )


def test_build_identity_infrastructure_wires_platform_repos():
    settings = _settings_with_mfa_key()
    client = MagicMock()
    platform_db = MagicMock()
    operational_db = MagicMock()

    def get_db(name: str):
        if name == settings.mongodb_platform_db:
            return platform_db
        return operational_db

    client.__getitem__.side_effect = get_db
    platform_db.__getitem__.side_effect = lambda n: MagicMock(name=n)

    databases = MongoDatabases(client, settings)
    infra = build_identity_infrastructure(databases, settings)
    assert infra.credential_verification is not None
    assert infra.create_platform_session is not None
    assert infra.complete_auth_continuation_mfa is not None
    assert infra.mfa_encryptor.key_version == settings.platform_mfa_encryption_key_version


def test_build_identity_fails_without_mfa_key_when_optional_resolve(monkeypatch):
    monkeypatch.delenv("MFA_PLATFORM_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("PLATFORM_MFA_ENCRYPTION_REQUIRED", raising=False)
    settings = Settings(
        app_env="test",
        mongodb_uri=None,
        platform_mfa_encryption_key=None,
        _env_file=None,
    )
    client = MagicMock()
    databases = MongoDatabases(client, settings)
    with pytest.raises(PlatformMfaConfigurationError):
        build_identity_infrastructure(databases, settings)
