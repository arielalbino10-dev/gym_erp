"""TTL de sesión (valores iniciales ADR-0003 §9)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from gym_erp_api.modules.identity.domain.session_kind import SessionKind
from gym_erp_api.modules.identity.domain.time_utils import truncate_utc_to_milliseconds


@dataclass(frozen=True, slots=True)
class SessionTimingPolicy:
    platform_absolute_ttl: timedelta = timedelta(hours=12)
    platform_idle_ttl: timedelta = timedelta(minutes=15)
    gym_absolute_ttl: timedelta = timedelta(hours=8)
    gym_idle_ttl: timedelta = timedelta(minutes=30)
    touch_throttle: timedelta = timedelta(seconds=60)

    def absolute_expires_at(self, session_kind: SessionKind, created_at: datetime) -> datetime:
        created = truncate_utc_to_milliseconds(created_at)
        ttl = (
            self.platform_absolute_ttl
            if session_kind is SessionKind.PLATFORM
            else self.gym_absolute_ttl
        )
        return created + ttl

    def idle_expires_at(
        self,
        session_kind: SessionKind,
        moment: datetime,
        *,
        absolute_cap: datetime | None = None,
    ) -> datetime:
        base = truncate_utc_to_milliseconds(moment)
        ttl = self.platform_idle_ttl if session_kind is SessionKind.PLATFORM else self.gym_idle_ttl
        idle = base + ttl
        if absolute_cap is not None:
            cap = truncate_utc_to_milliseconds(absolute_cap)
            if idle > cap:
                return cap
        return idle

    def should_touch(self, last_seen_at: datetime, now: datetime) -> bool:
        return now - last_seen_at >= self.touch_throttle
