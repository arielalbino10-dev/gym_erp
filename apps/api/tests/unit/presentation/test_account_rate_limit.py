from gym_erp_api.presentation.auth.account_rate_limit import login_account_rate_limit_key


def test_account_key_hashes_normalized_email():
    a = login_account_rate_limit_key("User@Example.test")
    b = login_account_rate_limit_key("user@example.test")
    assert a == b
    assert len(a) == 64
