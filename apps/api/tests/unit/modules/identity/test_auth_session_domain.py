from datetime import UTC, datetime, timedelta

import pytest

from gym_erp_api.modules.identity.domain.auth_session import AuthSession
from gym_erp_api.modules.identity.domain.errors import (
    SessionExpiredError,
    SessionRevokedError,
)
from gym_erp_api.modules.identity.domain.session_kind import SessionKind
from gym_erp_api.shared_kernel.identifiers import new_uuid


def _token_hash(seed: str = "a") -> str:
    return "a" * 64 if seed == "a" else ("b" * 64)


def test_session_rejects_revoked_or_expired():
    moment = datetime(2026, 6, 1, tzinfo=UTC)
    session = AuthSession.create(
        user_id=new_uuid(),
        session_kind=SessionKind.PLATFORM,
        token_hash=_token_hash(),
        expires_at=moment + timedelta(hours=1),
        idle_expires_at=moment + timedelta(minutes=10),
        credential_version=0,
        now=moment,
    )
    revoked = session.revoke(reason="logout", now=moment)
    with pytest.raises(SessionRevokedError):
        revoked.assert_usable_at(moment + timedelta(minutes=1))

    fresh = AuthSession.create(
        user_id=new_uuid(),
        session_kind=SessionKind.GYM,
        token_hash=_token_hash("b"),
        expires_at=moment + timedelta(minutes=1),
        idle_expires_at=moment + timedelta(seconds=30),
        credential_version=0,
        now=moment,
    )
    with pytest.raises(SessionExpiredError):
        fresh.assert_usable_at(moment + timedelta(minutes=5))
