from gym_erp_api.modules.identity.application.security.http_auth_contracts import (
    GYM_SESSION_COOKIE,
    PLATFORM_SESSION_COOKIE,
    RateLimitPolicy,
    platform_and_gym_cookies_are_separated,
)


def test_platform_and_gym_cookies_separated():
    assert platform_and_gym_cookies_are_separated()
    assert PLATFORM_SESSION_COOKIE.http_only
    assert GYM_SESSION_COOKIE.http_only
    assert PLATFORM_SESSION_COOKIE.secure


def test_rate_limit_policy_defaults():
    policy = RateLimitPolicy()
    assert policy.login_per_ip_per_minute >= 10
    assert policy.mfa_verify_per_continuation_per_minute >= 5
