"""Contratos de seguridad HTTP futuros (H2-B.6) — sin middleware activo."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SessionCookieKind(StrEnum):
    PLATFORM = "platform"
    GYM = "gym"


@dataclass(frozen=True, slots=True)
class SessionCookiePolicy:
    """Política de cookie de sesión (aplicar en H2-B.7+)."""

    name: str
    path: str
    http_only: bool = True
    secure: bool = True
    same_site: str = "lax"


PLATFORM_SESSION_COOKIE = SessionCookiePolicy(
    name="gym_platform_session",
    path="/api/v1/platform",
    same_site="strict",
)

GYM_SESSION_COOKIE = SessionCookiePolicy(
    name="gym_session",
    path="/api/v1",
    same_site="lax",
)

PLATFORM_AUTH_CONTINUATION_COOKIE = SessionCookiePolicy(
    name="gym_platform_auth_cont",
    path="/api/v1/platform/auth",
    same_site="strict",
)


@dataclass(frozen=True, slots=True)
class CsrfPolicy:
    """Doble envío cookie + header para mutaciones con cookie de sesión."""

    header_name: str = "X-CSRF-Token"
    cookie_name: str = "gym_csrf"
    safe_methods: frozenset[str] = frozenset({"GET", "HEAD", "OPTIONS"})


@dataclass(frozen=True, slots=True)
class OriginPolicy:
    """Validación Origin/Referer contra allowlist CORS en mutaciones."""

    require_for_methods: frozenset[str] = frozenset(
        {"POST", "PUT", "PATCH", "DELETE"},
    )


@dataclass(frozen=True, slots=True)
class RateLimitPolicy:
    """Límites lógicos (implementación en capa HTTP futura)."""

    login_per_ip_per_minute: int = 30
    login_per_email_per_minute: int = 10
    mfa_verify_per_continuation_per_minute: int = 15


@dataclass(frozen=True, slots=True)
class SecurityHeadersPolicy:
    """Cabeceras recomendadas vía middleware en despliegue."""

    content_type_options: str = "nosniff"
    frame_options: str = "DENY"
    referrer_policy: str = "strict-origin-when-cross-origin"
    permissions_policy: str = "geolocation=(), microphone=(), camera=()"


def platform_and_gym_cookies_are_separated() -> bool:
    return (
        PLATFORM_SESSION_COOKIE.name != GYM_SESSION_COOKIE.name
        and PLATFORM_SESSION_COOKIE.path != GYM_SESSION_COOKIE.path
    )
