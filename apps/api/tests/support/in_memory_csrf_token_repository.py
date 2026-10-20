from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class _CsrfRecord:
    binding_key: str
    expires_at: datetime


class InMemoryCsrfTokenRepository:
    def __init__(self) -> None:
        self._records: dict[str, _CsrfRecord] = {}

    async def store(
        self,
        *,
        token_hash: str,
        binding_key: str,
        expires_at: datetime,
        session: object | None = None,
    ) -> None:
        self._records[token_hash] = _CsrfRecord(binding_key=binding_key, expires_at=expires_at)

    async def consume_if_valid(
        self,
        *,
        token_hash: str,
        binding_key: str,
        now: datetime,
        session: object | None = None,
    ) -> bool:
        record = self._records.get(token_hash)
        if record is None:
            return False
        if record.binding_key != binding_key or record.expires_at <= now:
            return False
        del self._records[token_hash]
        return True
