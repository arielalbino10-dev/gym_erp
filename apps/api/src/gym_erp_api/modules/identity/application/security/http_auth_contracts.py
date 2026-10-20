"""Contratos de seguridad HTTP (H2-B.6 / H2-B.7.1) — ADR-0003."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MutationSecurityProfile(StrEnum):
    """Política explícita para mutaciones HTTP (H2-B.7.1.1)."""

    PUBLIC = "public"
    """Estado mutable sin cookies de sesión (p. ej. health no aplica). Origin en POST/…"""

    PRE_AUTHENTICATION = "pre_authentication"
    """Login/MFA antes de sesión: Origin; CSRF solo si hay cookies de sesión en la petición."""

    COOKIE_SESSION = "cookie_session"
    """Mutación con sesión por cookie: Origin + CSRF obligatorio (binding server-side)."""


class SessionCookieKind(StrEnum):
    PLATFORM = "platform"
    GYM = "gym"


@dataclass(frozen=True, slots=True)
class SessionCookiePolicy:
    name: str
    path: str
    http_only: bool = True
    secure: bool = True
    same_site: str = "lax"


PLATFORM_SESSION_COOKIE = SessionCookiePolicy(
    name="gym_erp_platform_session",
    path="/api/v1/platform",
    same_site="strict",
)

GYM_SESSION_COOKIE = SessionCookiePolicy(
    name="gym_erp_gym_session",
    path="/api/v1/gym",
    same_site="lax",
)

PLATFORM_AUTH_CONTINUATION_COOKIE = SessionCookiePolicy(
    name="gym_erp_platform_auth_cont",
    path="/api/v1/platform/auth",
    same_site="strict",
)


@dataclass(frozen=True, slots=True)
class CsrfPolicy:
    header_name: str = "X-CSRF-Token"
    cookie_name: str = "gym_erp_csrf"
    safe_methods: frozenset[str] = frozenset({"GET", "HEAD", "OPTIONS"})


@dataclass(frozen=True, slots=True)
class OriginPolicy:
    require_for_methods: frozenset[str] = frozenset(
        {"POST", "PUT", "PATCH", "DELETE"},
    )


@dataclass(frozen=True, slots=True)
class RateLimitPolicy:
    login_per_ip_per_minute: int = 30
    login_per_account_per_minute: int = 10
    mfa_verify_per_ip_per_minute: int = 30
    mfa_verify_per_continuation_per_minute: int = 15
    session_sensitive_per_ip_per_minute: int = 60


@dataclass(frozen=True, slots=True)
class SecurityHeadersPolicy:
    content_type_options: str = "nosniff"
    frame_options: str = "DENY"
    referrer_policy: str = "strict-origin-when-cross-origin"
    permissions_policy: str = "geolocation=(), microphone=(), camera=()"
    auth_cache_control: str = "no-store"


def platform_and_gym_cookies_are_separated() -> bool:
    return (
        PLATFORM_SESSION_COOKIE.name != GYM_SESSION_COOKIE.name
        and PLATFORM_SESSION_COOKIE.path != GYM_SESSION_COOKIE.path
    )


SESSION_COOKIE_NAMES: frozenset[str] = frozenset(
    {
        PLATFORM_SESSION_COOKIE.name,
        GYM_SESSION_COOKIE.name,
        PLATFORM_AUTH_CONTINUATION_COOKIE.name,
    }
)
