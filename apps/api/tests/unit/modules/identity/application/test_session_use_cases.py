from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from gym_erp_api.modules.identity.application.dto.auth_results import VerifiedPrincipal
from gym_erp_api.modules.identity.application.dto.platform_mfa import PlatformMfaVerificationTicket
from gym_erp_api.modules.identity.application.errors import (
    PlatformMfaRequiredError,
    PlatformSessionEmissionDisabledError,
    SessionResolutionFailedError,
)
from gym_erp_api.modules.identity.application.policies.session_timing_policy import (
    SessionTimingPolicy,
)
from gym_erp_api.modules.identity.application.use_cases.create_gym_session import (
    CreateGymSessionUseCase,
)
from gym_erp_api.modules.identity.application.use_cases.create_platform_session import (
    CreatePlatformSessionUseCase,
)
from gym_erp_api.modules.identity.application.use_cases.resolve_session import ResolveSessionUseCase
from gym_erp_api.modules.identity.application.use_cases.revoke_all_user_sessions import (
    RevokeAllUserSessionsUseCase,
)
from gym_erp_api.modules.identity.application.use_cases.revoke_session import RevokeSessionUseCase
from gym_erp_api.modules.identity.domain.auth_session import AuthSession
from gym_erp_api.modules.identity.domain.session_kind import SessionKind
from gym_erp_api.modules.identity.domain.user_identity import UserIdentity
from gym_erp_api.modules.identity.infrastructure.crypto.session_token_hash import (
    generate_opaque_session_token,
    hash_session_token,
)
from gym_erp_api.shared_kernel.identifiers import new_uuid

MOMENT = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)


class _TestOnlyPlatformEmissionGate:
    def assert_emission_allowed(self) -> None:
        return None


def _principal(identity: UserIdentity) -> VerifiedPrincipal:
    return VerifiedPrincipal(
        user_id=identity.user_id,
        credential_version=identity.credential_version,
        email_normalized=identity.email_normalized,
    )


def _active_identity() -> UserIdentity:
    return UserIdentity.create(email="sess@example.test", now=MOMENT).mark_email_verified(
        now=MOMENT
    )


@pytest.fixture
def identity_repo():
    return AsyncMock()


@pytest.fixture
def session_repo():
    repo = AsyncMock()
    repo.insert = AsyncMock()
    repo.get_by_token_hash = AsyncMock(return_value=None)
    repo.get_by_id = AsyncMock(return_value=None)
    repo.save_revoked = AsyncMock()
    repo.revoke_all_for_user = AsyncMock(return_value=0)
    repo.touch_activity = AsyncMock()
    return repo


@pytest.mark.asyncio
async def test_create_gym_session_returns_opaque_token(identity_repo, session_repo):
    identity = _active_identity()
    identity_repo.get_by_id.return_value = identity
    use_case = CreateGymSessionUseCase(
        identities=identity_repo,
        sessions=session_repo,
        clock=lambda: MOMENT,
    )
    created = await use_case.execute(principal=_principal(identity))
    assert created.opaque_token
    assert created.session.token_hash == hash_session_token(created.opaque_token)
    assert created.session.session_kind is SessionKind.GYM
    session_repo.insert.assert_awaited_once()
    doc = session_repo.insert.await_args[0][0]
    assert doc.token_hash != created.opaque_token


@pytest.mark.asyncio
async def test_platform_session_requires_mfa_ticket(identity_repo, session_repo):
    identity = _active_identity()
    identity_repo.get_by_id.return_value = identity
    use_case = CreatePlatformSessionUseCase(
        identities=identity_repo,
        sessions=session_repo,
        clock=lambda: MOMENT,
    )
    with pytest.raises(PlatformSessionEmissionDisabledError):
        await use_case.execute(principal=_principal(identity), mfa_ticket=None)


@pytest.mark.asyncio
async def test_platform_session_requires_ticket_when_emission_gate_open(
    identity_repo, session_repo
):
    identity = _active_identity()
    identity_repo.get_by_id.return_value = identity
    use_case = CreatePlatformSessionUseCase(
        identities=identity_repo,
        sessions=session_repo,
        clock=lambda: MOMENT,
        emission_gate=_TestOnlyPlatformEmissionGate(),
    )
    with pytest.raises(PlatformMfaRequiredError):
        await use_case.execute(principal=_principal(identity), mfa_ticket=None)


@pytest.mark.asyncio
async def test_platform_session_with_valid_ticket(identity_repo, session_repo):
    identity = _active_identity()
    identity_repo.get_by_id.return_value = identity
    ticket = PlatformMfaVerificationTicket(user_id=identity.user_id, verified_at=MOMENT)
    use_case = CreatePlatformSessionUseCase(
        identities=identity_repo,
        sessions=session_repo,
        clock=lambda: MOMENT,
        emission_gate=_TestOnlyPlatformEmissionGate(),
    )
    created = await use_case.execute(principal=_principal(identity), mfa_ticket=ticket)
    assert created.session.session_kind is SessionKind.PLATFORM


@pytest.mark.asyncio
async def test_resolve_session_absolute_expiry(identity_repo, session_repo):
    identity = _active_identity()
    identity_repo.get_by_id.return_value = identity
    token = generate_opaque_session_token()
    expired = AuthSession.create(
        user_id=identity.user_id,
        session_kind=SessionKind.GYM,
        token_hash=hash_session_token(token),
        expires_at=MOMENT - timedelta(minutes=1),
        idle_expires_at=MOMENT - timedelta(minutes=2),
        credential_version=0,
        now=MOMENT - timedelta(hours=1),
    )
    session_repo.get_by_token_hash.return_value = expired
    use_case = ResolveSessionUseCase(
        identities=identity_repo,
        sessions=session_repo,
        clock=lambda: MOMENT,
    )
    with pytest.raises(SessionResolutionFailedError):
        await use_case.execute(opaque_token=token, touch_activity=False)


@pytest.mark.asyncio
async def test_resolve_session_idle_expiry(identity_repo, session_repo):
    identity = _active_identity()
    identity_repo.get_by_id.return_value = identity
    token = generate_opaque_session_token()
    expired_idle = AuthSession.create(
        user_id=identity.user_id,
        session_kind=SessionKind.GYM,
        token_hash=hash_session_token(token),
        expires_at=MOMENT + timedelta(hours=1),
        idle_expires_at=MOMENT - timedelta(seconds=1),
        credential_version=0,
        now=MOMENT - timedelta(minutes=30),
    )
    session_repo.get_by_token_hash.return_value = expired_idle
    use_case = ResolveSessionUseCase(
        identities=identity_repo,
        sessions=session_repo,
        clock=lambda: MOMENT,
    )
    with pytest.raises(SessionResolutionFailedError):
        await use_case.execute(opaque_token=token, touch_activity=False)


@pytest.mark.asyncio
async def test_resolve_session_revoked(identity_repo, session_repo):
    identity = _active_identity()
    identity_repo.get_by_id.return_value = identity
    token = generate_opaque_session_token()
    session = AuthSession.create(
        user_id=identity.user_id,
        session_kind=SessionKind.GYM,
        token_hash=hash_session_token(token),
        expires_at=MOMENT + timedelta(hours=1),
        idle_expires_at=MOMENT + timedelta(minutes=10),
        credential_version=0,
        now=MOMENT,
    ).revoke(reason="logout", now=MOMENT)
    session_repo.get_by_token_hash.return_value = session
    use_case = ResolveSessionUseCase(
        identities=identity_repo,
        sessions=session_repo,
        clock=lambda: MOMENT,
    )
    with pytest.raises(SessionResolutionFailedError):
        await use_case.execute(opaque_token=token)


@pytest.mark.asyncio
async def test_resolve_session_credential_version_mismatch(identity_repo, session_repo):
    identity = _active_identity().increment_credential_version(now=MOMENT)
    identity_repo.get_by_id.return_value = identity
    token = generate_opaque_session_token()
    session = AuthSession.create(
        user_id=identity.user_id,
        session_kind=SessionKind.GYM,
        token_hash=hash_session_token(token),
        expires_at=MOMENT + timedelta(hours=1),
        idle_expires_at=MOMENT + timedelta(minutes=10),
        credential_version=0,
        now=MOMENT,
    )
    session_repo.get_by_token_hash.return_value = session
    use_case = ResolveSessionUseCase(
        identities=identity_repo,
        sessions=session_repo,
        clock=lambda: MOMENT,
    )
    with pytest.raises(SessionResolutionFailedError):
        await use_case.execute(opaque_token=token, touch_activity=False)


@pytest.mark.asyncio
async def test_revoke_session_idempotent(identity_repo, session_repo):
    identity = _active_identity()
    session = AuthSession.create(
        user_id=identity.user_id,
        session_kind=SessionKind.GYM,
        token_hash="a" * 64,
        expires_at=MOMENT + timedelta(hours=1),
        idle_expires_at=MOMENT + timedelta(minutes=10),
        credential_version=0,
        now=MOMENT,
    )
    session_repo.get_by_id.return_value = session.revoke(reason="logout", now=MOMENT)
    use_case = RevokeSessionUseCase(sessions=session_repo, clock=lambda: MOMENT)
    await use_case.execute(session_id=session.session_id, reason="logout")
    session_repo.save_revoked.assert_not_awaited()


@pytest.mark.asyncio
async def test_revoke_all_user_sessions(identity_repo, session_repo):
    uid = new_uuid()
    session_repo.revoke_all_for_user.return_value = 2
    use_case = RevokeAllUserSessionsUseCase(sessions=session_repo, clock=lambda: MOMENT)
    count = await use_case.execute(user_id=uid, reason="password_change")
    assert count == 2


@pytest.mark.asyncio
async def test_resolve_success_with_touch(identity_repo, session_repo):
    identity = _active_identity()
    identity_repo.get_by_id.return_value = identity
    token = generate_opaque_session_token()
    session = AuthSession.create(
        user_id=identity.user_id,
        session_kind=SessionKind.GYM,
        token_hash=hash_session_token(token),
        expires_at=MOMENT + timedelta(hours=8),
        idle_expires_at=MOMENT + timedelta(minutes=30),
        credential_version=identity.credential_version,
        now=MOMENT,
    )
    session_repo.get_by_token_hash.return_value = session
    touched = session.touch_activity(
        idle_expires_at=MOMENT + timedelta(minutes=30),
        now=MOMENT + timedelta(minutes=2),
    )
    session_repo.touch_activity.return_value = touched
    policy = SessionTimingPolicy(touch_throttle=timedelta(seconds=0))
    use_case = ResolveSessionUseCase(
        identities=identity_repo,
        sessions=session_repo,
        timing=policy,
        clock=lambda: MOMENT + timedelta(minutes=2),
    )
    resolved = await use_case.execute(opaque_token=token)
    assert resolved.user_id == identity.user_id
