from unittest.mock import MagicMock

from gym_erp_api.core.config import Settings
from gym_erp_api.presentation.http_security.client_ip import (
    client_ip,
    client_ip_from_forwarded,
    trusted_proxy_set,
)


class _Headers:
    def __init__(self, data: dict[str, str]) -> None:
        self._data = data

    def get(self, key: str, default: str = "") -> str:
        return self._data.get(key, default)


def _request(*, peer: str, headers: dict[str, str] | None = None):
    request = MagicMock()
    request.client.host = peer
    request.headers = _Headers(headers or {})
    return request


def test_forwarded_uses_rightmost_untrusted_hop():
    trusted = frozenset({"127.0.0.1"})
    forwarded = "203.0.113.50, 198.51.100.10, 127.0.0.1"
    assert client_ip_from_forwarded(forwarded, trusted=trusted) == "198.51.100.10"


def test_spoofed_leftmost_hop_ignored_behind_trusted_proxy():
    settings = Settings(app_env="test", mongodb_uri=None, trusted_proxy_ips="127.0.0.1")
    request = _request(
        peer="127.0.0.1",
        headers={"X-Forwarded-For": "1.2.3.4, 203.0.113.9"},
    )
    assert client_ip(request, settings) == "203.0.113.9"


def test_invalid_forwarded_hop_skipped():
    settings = Settings(app_env="test", mongodb_uri=None, trusted_proxy_ips="127.0.0.1")
    request = _request(
        peer="127.0.0.1",
        headers={"X-Forwarded-For": "not-an-ip, 203.0.113.9"},
    )
    assert client_ip(request, settings) == "203.0.113.9"


def test_direct_client_without_trusted_proxy():
    settings = Settings(app_env="test", mongodb_uri=None, trusted_proxy_ips="127.0.0.1")
    request = _request(peer="203.0.113.55", headers={"X-Forwarded-For": "1.2.3.4"})
    assert client_ip(request, settings) == "203.0.113.55"


def test_trusted_proxy_set_parses_csv():
    settings = Settings(app_env="test", mongodb_uri=None, trusted_proxy_ips="127.0.0.1, 10.0.0.1")
    assert trusted_proxy_set(settings) == frozenset({"127.0.0.1", "10.0.0.1"})
