from __future__ import annotations

import importlib.util
import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import SecretStr

from gym_erp_api.core.config import Settings
from gym_erp_api.modules.organization.domain.errors import InvalidOrganizationIdentifierError
from gym_erp_api.modules.organization.domain.validators import require_uuid_v4

_SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "bootstrap_local_gym_dev.py"
_spec = importlib.util.spec_from_file_location("bootstrap_local_gym_dev", _SCRIPT_PATH)
assert _spec and _spec.loader
bootstrap = importlib.util.module_from_spec(_spec)
sys.modules["bootstrap_local_gym_dev"] = bootstrap
_spec.loader.exec_module(bootstrap)


def _dev_settings(**overrides) -> Settings:
    base = dict(
        app_env="development",
        mongodb_uri=SecretStr("mongodb://127.0.0.1:27017/?replicaSet=rs0"),
        mongodb_platform_db="gym_platform",
        mongodb_operational_db="gym_operational",
        allow_insecure_cookies=True,
    )
    base.update(overrides)
    return Settings(**base)


def test_uuid5_is_rejected_by_organization_validator_reproducing_traceback():
    """Regresión: uuid5 provoca InvalidOrganizationIdentifierError en get_by_id."""
    tenant_v5 = str(uuid.uuid5(uuid.NAMESPACE_URL, "https://local.test/gym-erp/bootstrap/v1/x"))
    assert uuid.UUID(tenant_v5).version == 5
    with pytest.raises(InvalidOrganizationIdentifierError):
        require_uuid_v4(tenant_v5, "tenant_id")


def test_parse_tenant_override_rejects_uuid5():
    tenant_v5 = str(uuid.uuid5(uuid.NAMESPACE_URL, "x"))
    with pytest.raises(bootstrap.BootstrapError, match="UUID v4"):
        bootstrap.parse_tenant_id_override(tenant_v5)


def test_parse_tenant_override_accepts_uuid4():
    tenant_v4 = str(uuid.uuid4())
    assert bootstrap.parse_tenant_id_override(tenant_v4) == tenant_v4


def test_collect_inputs_requires_opt_in_and_password():
    with pytest.raises(bootstrap.BootstrapError):
        bootstrap.collect_bootstrap_inputs({"GYM_ERP_BOOTSTRAP_GYM": "0"})
    with pytest.raises(bootstrap.BootstrapError):
        bootstrap.collect_bootstrap_inputs(
            {
                "GYM_ERP_BOOTSTRAP_GYM": "1",
                "GYM_ERP_DEV_BOOTSTRAP_PASSWORD": "short",
            },
        )


def test_validate_settings_rejects_test_databases_in_development():
    settings = _dev_settings(mongodb_platform_db="gym_platform_test")
    with pytest.raises(bootstrap.BootstrapError):
        bootstrap.validate_settings_for_bootstrap(
            settings,
            {"GYM_ERP_BOOTSTRAP_ALLOW_TEST_DB": "0"},
        )


def test_validate_app_env_rejects_production():
    with pytest.raises(bootstrap.BootstrapError):
        bootstrap.validate_app_env("production")


@pytest.mark.asyncio
async def test_resolve_tenant_uses_membership_not_display_name_only():
    tenant_v4 = str(uuid.uuid4())
    memberships = MagicMock()
    tenants = MagicMock()
    memberships.list_active_by_user_id = AsyncMock(
        return_value=(
            MagicMock(
                tenant_id=tenant_v4,
                gym_roles=frozenset({bootstrap.GymRole.GYM_OWNER}),
            ),
        ),
    )
    tenants.get_by_id = AsyncMock(
        return_value=MagicMock(
            display_name=bootstrap._BOOTSTRAP_DISPLAY_NAME,
            legal_name=bootstrap._BOOTSTRAP_LEGAL_NAME,
        ),
    )

    resolved = await bootstrap.resolve_dev_tenant_id(
        email="dev.gym.owner@local.test",
        tenant_id_override=None,
        user_id=str(uuid.uuid4()),
        memberships=memberships,
        tenants=tenants,
        session=None,
    )
    assert resolved == tenant_v4
    assert uuid.UUID(resolved).version == 4


@pytest.mark.asyncio
async def test_resolve_tenant_new_user_returns_uuid_v4():
    resolved = await bootstrap.resolve_dev_tenant_id(
        email="dev.gym.owner@local.test",
        tenant_id_override=None,
        user_id=None,
        memberships=MagicMock(),
        tenants=MagicMock(),
        session=None,
    )
    assert uuid.UUID(resolved).version == 4


@pytest.mark.asyncio
async def test_resolve_tenant_ignores_membership_on_non_bootstrap_tenant():
    tenant_v4 = str(uuid.uuid4())
    memberships = MagicMock()
    tenants = MagicMock()
    memberships.list_active_by_user_id = AsyncMock(
        return_value=(
            MagicMock(
                tenant_id=tenant_v4,
                gym_roles=frozenset({bootstrap.GymRole.GYM_OWNER}),
            ),
        ),
    )
    tenants.get_by_id = AsyncMock(
        return_value=MagicMock(
            display_name=bootstrap._BOOTSTRAP_DISPLAY_NAME,
            legal_name="Otro legal",
        ),
    )
    resolved = await bootstrap.resolve_dev_tenant_id(
        email="dev.gym.owner@local.test",
        tenant_id_override=None,
        user_id=str(uuid.uuid4()),
        memberships=memberships,
        tenants=tenants,
        session=None,
    )
    assert resolved != tenant_v4
    assert uuid.UUID(resolved).version == 4


@pytest.mark.asyncio
async def test_run_bootstrap_idempotent_second_run_uses_membership_tenant(monkeypatch):
    tenant_v4 = str(uuid.uuid4())
    inputs = bootstrap.BootstrapInputs(
        email="dev.gym.owner@local.test",
        password="valid-password-12",
        tenant_id_override=None,
    )
    settings = _dev_settings()
    identity = MagicMock(user_id=str(uuid.uuid4()))

    identities = MagicMock()
    identities.get_by_email_normalized = AsyncMock(return_value=identity)
    credentials = MagicMock()
    credentials.get_by_user_id = AsyncMock(return_value=MagicMock())

    apply_mock = AsyncMock(return_value=tenant_v4)
    monkeypatch.setattr(bootstrap, "create_mongo_client", lambda _s: MagicMock(close=AsyncMock()))
    monkeypatch.setattr(bootstrap, "MongoDatabases", lambda _c, _s: MagicMock())
    monkeypatch.setattr(bootstrap, "MongoIdentityRepository", lambda _c: identities)
    monkeypatch.setattr(bootstrap, "MongoCredentialRepository", lambda _c: credentials)
    monkeypatch.setattr(bootstrap, "apply_bootstrap_writes", apply_mock)
    monkeypatch.setattr(
        bootstrap,
        "MongoUnitOfWork",
        lambda _d: MagicMock(
            __aenter__=AsyncMock(return_value=MagicMock(session=MagicMock())),
            __aexit__=AsyncMock(return_value=None),
        ),
    )

    resolved, cred_exists = await bootstrap.run_bootstrap(settings, inputs)
    assert resolved == tenant_v4
    assert cred_exists is True


@pytest.mark.asyncio
async def test_tenant_override_rejects_existing_foreign_tenant():
    tenant_v4 = str(uuid.uuid4())
    memberships = MagicMock()
    memberships.get_by_user_and_tenant = AsyncMock(return_value=None)
    tenants = MagicMock()
    tenants.get_by_id = AsyncMock(return_value=MagicMock())
    with pytest.raises(bootstrap.BootstrapError):
        await bootstrap.assert_tenant_override_authorized(
            tenant_id=tenant_v4,
            tenant_id_override=tenant_v4,
            user_id=str(uuid.uuid4()),
            memberships=memberships,
            tenants=tenants,
            session=None,
        )


def test_inspect_report_notes_partial_state():
    report = bootstrap.BootstrapInspectReport(
        email="dev.gym.owner@local.test",
        identity_present=True,
        credential_present=True,
        bootstrap_membership_tenant_ids=(),
        notes=("Estado parcial probable: identidad y credencial sin membresía bootstrap.",),
    )
    text = bootstrap.format_inspect_report(report)
    assert "identity_present=True" in text
    assert "Estado parcial" in text
