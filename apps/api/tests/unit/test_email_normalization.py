import pytest

from gym_erp_api.shared_kernel.email_normalization import normalize_email


def test_normalize_email_trims_and_lowercases():
    assert normalize_email("  Ana@Ejemplo.MX  ") == "ana@ejemplo.mx"


def test_normalize_email_rejects_empty():
    with pytest.raises(ValueError):
        normalize_email("   ")


def test_normalize_email_is_idempotent():
    once = normalize_email("  Ana@Ejemplo.MX  ")
    twice = normalize_email(once)
    assert once == twice
