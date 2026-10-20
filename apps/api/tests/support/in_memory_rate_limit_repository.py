from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta

from gym_erp_api.infrastructure.mongo.mongo_rate_limit_repository import RateLimitDecision


@dataclass
class _Window:
    count: int
    window_start: datetime


class InMemoryRateLimitRepository:
    def __init__(self) -> None:
        self._data: dict[str, _Window] = {}
        self._lock = asyncio.Lock()
        self.fail_next = False

    async def check_and_increment(
        self,
        *,
        bucket: str,
        scope_key: str,
        limit: int,
        window: timedelta,
        now: datetime,
        session: object | None = None,
    ) -> RateLimitDecision:
        if self.fail_next:
            from gym_erp_api.presentation.http_security.errors import RateLimitBackendError

            raise RateLimitBackendError("simulated failure")
        doc_id = f"{bucket}:{scope_key}"
        cutoff = now - window
        async with self._lock:
            current = self._data.get(doc_id)
            if current is None or current.window_start < cutoff:
                self._data[doc_id] = _Window(count=1, window_start=now)
                return RateLimitDecision(allowed=True)
            current.count += 1
            if current.count > limit:
                retry = int((current.window_start + window - now).total_seconds())
                return RateLimitDecision(allowed=False, retry_after_seconds=max(1, retry))
            return RateLimitDecision(allowed=True)
