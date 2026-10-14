import pytest

from gym_erp_api.shared_kernel.exceptions import InvalidTenantContextError
from gym_erp_api.shared_kernel.identifiers import assert_uuid_v4, is_valid_uuid_v4, new_uuid


def test_new_uuid_is_valid_v4():
    value = new_uuid()
    assert is_valid_uuid_v4(value)


def test_assert_uuid_v4_rejects_invalid():
    with pytest.raises(InvalidTenantContextError):
        assert_uuid_v4("not-a-uuid", "tenant_id")


def test_assert_uuid_v4_rejects_uuid_v1():
    with pytest.raises(InvalidTenantContextError):
        assert_uuid_v4("6ba7b810-9dad-11d1-80b4-00c04fd430c8", "tenant_id")
