import pytest

from gym_erp_api.modules.organization.domain.errors import InvalidOrganizationFieldError
from gym_erp_api.modules.organization.domain.validators import (
    normalize_branch_code,
    normalize_commercial_email,
    require_timezone,
)


def test_normalize_branch_code_uppercases():
    assert normalize_branch_code("ab-12") == "AB-12"


def test_normalize_branch_code_blank_becomes_none():
    assert normalize_branch_code("   ") is None


def test_normalize_commercial_email_empty_is_none_pair():
    assert normalize_commercial_email(None) == (None, None)
    assert normalize_commercial_email("  ") == (None, None)


def test_require_timezone_accepts_iana():
    assert require_timezone("America/Mexico_City") == "America/Mexico_City"


def test_require_timezone_rejects_unknown():
    with pytest.raises(InvalidOrganizationFieldError):
        require_timezone("Invalid/Zone")
