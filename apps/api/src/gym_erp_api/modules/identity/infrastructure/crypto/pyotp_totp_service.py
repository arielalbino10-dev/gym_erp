"""TOTP estándar (RFC 6238) vía pyotp."""

from __future__ import annotations

from datetime import UTC, datetime

import pyotp
from pyotp import utils as pyotp_utils


class PyotpTotpService:
    def __init__(self, *, valid_window: int = 1) -> None:
        self._valid_window = valid_window

    def generate_secret(self) -> bytes:
        return pyotp.random_base32().encode("ascii")

    def provisioning_uri(self, *, secret: bytes, account_name: str, issuer: str) -> str:
        totp = pyotp.TOTP(secret.decode("ascii"))
        return totp.provisioning_uri(name=account_name, issuer_name=issuer)

    def verify(
        self,
        *,
        secret: bytes,
        code: str,
        for_time: int | None = None,
    ) -> tuple[bool, int]:
        if not isinstance(code, str) or not code.isdigit() or len(code) != 6:
            return False, 0
        totp = pyotp.TOTP(secret.decode("ascii"))
        if for_time is not None:
            moment = datetime.fromtimestamp(for_time, tz=UTC)
        else:
            moment = datetime.now(tz=UTC)
        base_counter = totp.timecode(moment)
        for offset in range(-self._valid_window, self._valid_window + 1):
            candidate = totp.at(moment, counter_offset=offset)
            if pyotp_utils.strings_equal(code, candidate):
                return True, base_counter + offset
        return False, base_counter
