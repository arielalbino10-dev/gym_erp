from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "bootstrap_local_platform_root.py"
_spec = importlib.util.spec_from_file_location("bootstrap_local_platform_root", _SCRIPT_PATH)
assert _spec and _spec.loader
bootstrap = importlib.util.module_from_spec(_spec)
sys.modules["bootstrap_local_platform_root"] = bootstrap
_spec.loader.exec_module(bootstrap)


def test_require_bootstrap_opt_in():
    with pytest.raises(bootstrap.BootstrapError, match="GYM_ERP_BOOTSTRAP_PLATFORM_ROOT"):
        bootstrap.require_bootstrap_opt_in({"GYM_ERP_BOOTSTRAP_PLATFORM_ROOT": "0"})


def test_validate_app_env_rejects_production():
    with pytest.raises(bootstrap.BootstrapError, match="production"):
        bootstrap.validate_app_env_for_bootstrap("production")


def test_collect_inputs_requires_email_and_password():
    with pytest.raises(bootstrap.BootstrapError, match="EMAIL"):
        bootstrap.collect_bootstrap_inputs({}, inspect_only=False)
    with pytest.raises(bootstrap.BootstrapError, match="12"):
        bootstrap.collect_bootstrap_inputs(
            {
                "GYM_ERP_DEV_BOOTSTRAP_PLATFORM_EMAIL": "root@local.test",
                "GYM_ERP_DEV_BOOTSTRAP_PASSWORD": "short",
            },
            inspect_only=False,
        )


def test_collect_inputs_inspect_skips_password_length():
    email, password = bootstrap.collect_bootstrap_inputs(
        {"GYM_ERP_DEV_BOOTSTRAP_PLATFORM_EMAIL": "root@local.test"},
        inspect_only=True,
    )
    assert email == "root@local.test"
    assert password == ""


def test_existing_identity_requires_confirm_before_root_promotion():
    with pytest.raises(bootstrap.BootstrapError, match="CONFIRM_EXISTING"):
        bootstrap.require_promotion_consent_for_existing_identity(
            identity_preexisted=True,
            already_root=False,
            env={},
        )


def test_existing_root_is_idempotent_without_confirm_flag():
    bootstrap.require_promotion_consent_for_existing_identity(
        identity_preexisted=True,
        already_root=True,
        env={},
    )


def test_new_identity_does_not_require_confirm():
    bootstrap.require_promotion_consent_for_existing_identity(
        identity_preexisted=False,
        already_root=False,
        env={},
    )
