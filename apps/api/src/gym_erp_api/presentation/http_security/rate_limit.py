"""Rate limiting HTTP (MongoDB, fail-closed configurable)."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum

from gym_erp_api.core.config import Settings
from gym_erp_api.infrastructure.mongo.mongo_rate_limit_repository import (
    MongoRateLimitRepository,
    RateLimitDecision,
)
from gym_erp_api.modules.identity.application.security.http_auth_contracts import RateLimitPolicy
from gym_erp_api.presentation.http_security.errors import (
    RateLimitBackendError,
    RateLimitExceededError,
)

_policy = RateLimitPolicy()


class RateLimitBucket(StrEnum):
    LOGIN_IP = "login_ip"
    LOGIN_ACCOUNT = "login_account"
    MFA_VERIFY_IP = "mfa_verify_ip"
    MFA_CONTINUATION = "mfa_continuation"
    SESSION_SENSITIVE_IP = "session_sensitive_ip"


class HttpRateLimiter:
    def __init__(
        self,
        *,
        repository: MongoRateLimitRepository,
        settings: Settings,
    ) -> None:
        self._repository = repository
        self._settings = settings

    async def enforce(
        self,
        *,
        bucket: RateLimitBucket,
        scope_key: str,
        limit: int,
        window: timedelta,
        now: datetime,
    ) -> None:
        try:
            decision = await self._repository.check_and_increment(
                bucket=bucket.value,
                scope_key=scope_key,
                limit=limit,
                window=window,
                now=now,
            )
        except RateLimitBackendError:
            if self._settings.rate_limit_fail_closed:
                raise
            return
        _raise_if_denied(decision)

    async def enforce_login_ip(self, *, ip: str, now: datetime) -> None:
        await self.enforce(
            bucket=RateLimitBucket.LOGIN_IP,
            scope_key=ip,
            limit=_policy.login_per_ip_per_minute,
            window=timedelta(minutes=1),
            now=now,
        )

    async def enforce_login_account(self, *, account_key: str, now: datetime) -> None:
        await self.enforce(
            bucket=RateLimitBucket.LOGIN_ACCOUNT,
            scope_key=account_key,
            limit=_policy.login_per_account_per_minute,
            window=timedelta(minutes=1),
            now=now,
        )

    async def enforce_mfa_verify_ip(self, *, ip: str, now: datetime) -> None:
        await self.enforce(
            bucket=RateLimitBucket.MFA_VERIFY_IP,
            scope_key=ip,
            limit=_policy.mfa_verify_per_ip_per_minute,
            window=timedelta(minutes=1),
            now=now,
        )

    async def enforce_mfa_continuation(self, *, continuation_key: str, now: datetime) -> None:
        await self.enforce(
            bucket=RateLimitBucket.MFA_CONTINUATION,
            scope_key=continuation_key,
            limit=_policy.mfa_verify_per_continuation_per_minute,
            window=timedelta(minutes=1),
            now=now,
        )


def _raise_if_denied(decision: RateLimitDecision) -> None:
    if not decision.allowed:
        raise RateLimitExceededError(retry_after_seconds=decision.retry_after_seconds)
