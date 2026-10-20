"""Validación Origin / Referer (coincidencia exacta normalizada)."""

from __future__ import annotations

from urllib.parse import urlparse

from gym_erp_api.core.config import Settings
from gym_erp_api.presentation.http_security.errors import InvalidOriginError


def normalize_origin(origin: str) -> str:
    parsed = urlparse(origin.strip())
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise InvalidOriginError("Origin malformado.")
    host = parsed.hostname.lower()
    try:
        port = parsed.port
    except ValueError as exc:
        raise InvalidOriginError("Origin malformado.") from exc
    if port is None:
        port = 443 if parsed.scheme == "https" else 80
    default_port = 443 if parsed.scheme == "https" else 80
    if port == default_port:
        return f"{parsed.scheme}://{host}"
    return f"{parsed.scheme}://{host}:{port}"


def allowed_origins(settings: Settings) -> frozenset[str]:
    return frozenset(normalize_origin(o) for o in settings.cors_origin_list)


def origin_from_referer(referer: str) -> str:
    parsed = urlparse(referer.strip())
    if not parsed.scheme or not parsed.hostname:
        raise InvalidOriginError("Referer malformado.")
    return normalize_origin(f"{parsed.scheme}://{parsed.netloc}")


def resolve_request_origin(
    *,
    origin_header: str | None,
    referer_header: str | None,
) -> str:
    if origin_header and origin_header.strip():
        return normalize_origin(origin_header)
    if referer_header and referer_header.strip():
        return origin_from_referer(referer_header)
    raise InvalidOriginError("Origin ausente.")


def validate_origin_for_mutation(
    settings: Settings,
    *,
    origin_header: str | None,
    referer_header: str | None,
) -> None:
    resolved = resolve_request_origin(
        origin_header=origin_header,
        referer_header=referer_header,
    )
    if resolved not in allowed_origins(settings):
        raise InvalidOriginError("Origin no autorizado.")
