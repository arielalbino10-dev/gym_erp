"""IP del cliente con proxies de confianza explícitos."""

from __future__ import annotations

import ipaddress

from starlette.requests import Request

from gym_erp_api.core.config import Settings


def trusted_proxy_set(settings: Settings) -> frozenset[str]:
    raw = settings.trusted_proxy_ips.strip()
    if not raw:
        return frozenset()
    return frozenset(part.strip() for part in raw.split(",") if part.strip())


def _parse_ip(value: str) -> str | None:
    candidate = value.strip()
    if not candidate:
        return None
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None


def client_ip_from_forwarded(forwarded: str, *, trusted: frozenset[str]) -> str | None:
    hops = [part.strip() for part in forwarded.split(",") if part.strip()]
    for hop in reversed(hops):
        parsed = _parse_ip(hop)
        if parsed is None:
            continue
        if parsed not in trusted:
            return parsed
    for hop in hops:
        parsed = _parse_ip(hop)
        if parsed is not None:
            return parsed
    return None


def client_ip(request: Request, settings: Settings) -> str:
    peer = request.client.host if request.client else ""
    trusted = trusted_proxy_set(settings)
    if peer not in trusted:
        return peer or "unknown"
    forwarded = request.headers.get("X-Forwarded-For", "").strip()
    if not forwarded:
        return peer or "unknown"
    resolved = client_ip_from_forwarded(forwarded, trusted=trusted)
    return resolved or peer or "unknown"
