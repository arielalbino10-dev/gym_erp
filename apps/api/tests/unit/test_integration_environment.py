"""Unitarias adicionales del harness de integración (sin MongoDB)."""

import pytest

from tests.support.integration_environment import (
    INTEGRATION_COLLECTION_PREFIX,
    ORG_OPERATIONAL_COLLECTION_PREFIX,
    ORG_PLATFORM_COLLECTION_PREFIX,
    assert_ephemeral_collection_safe_for_teardown,
    assert_organization_ephemeral_collection_safe_for_teardown,
    generate_ephemeral_collection_name,
    generate_org_operational_collection_name,
    generate_org_platform_collection_name,
)


def test_ephemeral_collection_name_uses_prefix():
    name = generate_ephemeral_collection_name()
    assert name.startswith(INTEGRATION_COLLECTION_PREFIX)
    assert len(name) > len(INTEGRATION_COLLECTION_PREFIX)


def test_teardown_guard_rejects_mismatch():
    name = generate_ephemeral_collection_name()
    with pytest.raises(ValueError, match="no coincide"):
        assert_ephemeral_collection_safe_for_teardown(
            name,
            expected_name=f"{name}x",
            operational_db="gym_operational_test",
        )


def test_org_platform_collection_prefix():
    name = generate_org_platform_collection_name()
    assert name.startswith(ORG_PLATFORM_COLLECTION_PREFIX)


def test_org_operational_collection_prefix():
    name = generate_org_operational_collection_name()
    assert name.startswith(ORG_OPERATIONAL_COLLECTION_PREFIX)


def test_org_teardown_guard_accepts_platform_collection():
    name = generate_org_platform_collection_name()
    assert_organization_ephemeral_collection_safe_for_teardown(
        name,
        expected_name=name,
        database_name="gym_platform_test",
        collection_prefix=ORG_PLATFORM_COLLECTION_PREFIX,
        expected_database="gym_platform_test",
    )


def test_teardown_guard_rejects_wrong_database():
    name = generate_ephemeral_collection_name()
    with pytest.raises(ValueError, match="gym_operational_test"):
        assert_ephemeral_collection_safe_for_teardown(
            name,
            expected_name=name,
            operational_db="gym_platform_test",
        )
