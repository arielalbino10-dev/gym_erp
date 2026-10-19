from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from gym_erp_api.modules.identity.application.policies.session_timing_policy import (
    SessionTimingPolicy,
)
from gym_erp_api.modules.identity.application.use_cases.resolve_session import ResolveSessionUseCase
from gym_erp_api.modules.identity.domain.auth_session import AuthSession
from gym_erp_api.modules.identity.domain.session_kind import SessionKind
from gym_erp_api.modules.identity.domain.user_identity import UserIdentity
from gym_erp_api.modules.identity.infrastructure.crypto.session_token_hash import (
    generate_opaque_session_token,
    hash_session_token,
)

MOMENT = datetime(2026, 6, 10, 12, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_touch_caps_idle_at_absolute_expiry():
    identity = UserIdentity.create(email="touch@example.test", now=MOMENT).mark_email_verified(
        now=MOMENT
    )
    identity_repo = AsyncMock()
    identity_repo.get_by_id.return_value = identity
    session_repo = AsyncMock()
    token = generate_opaque_session_token()
    expires = MOMENT + timedelta(minutes=10)
    session = AuthSession.create(
        user_id=identity.user_id,
        session_kind=SessionKind.GYM,
        token_hash=hash_session_token(token),
        expires_at=expires,
        idle_expires_at=MOMENT + timedelta(minutes=8),
        credential_version=0,
        now=MOMENT,
    )
    session_repo.get_by_token_hash.return_value = session
    now = MOMENT + timedelta(minutes=7)
    touched = session.touch_activity(idle_expires_at=expires, now=now)
    session_repo.touch_activity.return_value = touched
    use_case = ResolveSessionUseCase(
        identities=identity_repo,
        sessions=session_repo,
        timing=SessionTimingPolicy(touch_throttle=timedelta(seconds=0)),
        clock=lambda: now,
    )
    await use_case.execute(opaque_token=token)
    call_args = session_repo.touch_activity.await_args[0][0]
    assert call_args.idle_expires_at == expires
