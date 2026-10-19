"""H2-B.4.1 / H2-B.5 — emisión platform y límites de active_tenant_id."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from gym_erp_api.modules.identity.application.dto.auth_results import VerifiedPrincipal
from gym_erp_api.modules.identity.application.dto.platform_mfa import PlatformMfaVerificationTicket
from gym_erp_api.modules.identity.application.errors import (
    PlatformMfaNotConfiguredError,
    PlatformMfaRequiredError,
    PlatformSessionEmissionDisabledError,
)
from gym_erp_api.modules.identity.application.use_cases.create_gym_session import (
    CreateGymSessionUseCase,
)
from gym_erp_api.modules.identity.application.use_cases.create_platform_session import (
    CreatePlatformSessionUseCase,
)
from gym_erp_api.modules.identity.domain.platform_mfa.platform_mfa_session_authorization import (
    PlatformMfaSessionAuthorization,
)
from gym_erp_api.modules.identity.domain.user_identity import UserIdentity
from gym_erp_api.modules.identity.infrastructure.platform_mfa_unconfigured import (
    UnconfiguredPlatformMfaVerification,
)
from gym_erp_api.shared_kernel.identifiers import new_uuid
from tests.support.in_memory_platform_mfa_repositories import (
    InMemoryPlatformMfaSessionAuthorizationRepository,
)

MOMENT = datetime(2026, 9, 1, tzinfo=UTC)


def _principal(identity: UserIdentity) -> VerifiedPrincipal:
    return VerifiedPrincipal(
        user_id=identity.user_id,
        credential_version=identity.credential_version,
        email_normalized=identity.email_normalized,
        verified_at=MOMENT,
    )


@pytest.mark.asyncio
async def test_platform_session_blocked_by_default_even_with_forged_ticket():
    identity = UserIdentity.create(email="forge@example.test", now=MOMENT).mark_email_verified(
        now=MOMENT
    )
    identity_repo = AsyncMock()
    identity_repo.get_by_id.return_value = identity
    session_repo = AsyncMock()
    use_case = CreatePlatformSessionUseCase(
        identities=identity_repo,
        sessions=session_repo,
        clock=lambda: MOMENT,
    )
    forged_auth = new_uuid()
    with pytest.raises(PlatformSessionEmissionDisabledError):
        await use_case.execute(principal=_principal(identity), authorization_id=forged_auth)
    session_repo.insert.assert_not_awaited()


@pytest.mark.asyncio
async def test_fabricated_mfa_ticket_does_not_authorize_platform_session():
    identity = UserIdentity.create(email="ticket@example.test", now=MOMENT).mark_email_verified(
        now=MOMENT
    )
    identity_repo = AsyncMock()
    identity_repo.get_by_id.return_value = identity
    session_repo = AsyncMock()
    authorizations = InMemoryPlatformMfaSessionAuthorizationRepository()
    _ = PlatformMfaVerificationTicket(user_id=identity.user_id, verified_at=MOMENT)
    use_case = CreatePlatformSessionUseCase(
        identities=identity_repo,
        sessions=session_repo,
        authorizations=authorizations,
        clock=lambda: MOMENT,
    )
    with pytest.raises(PlatformMfaRequiredError):
        await use_case.execute(principal=_principal(identity), authorization_id=new_uuid())
    session_repo.insert.assert_not_awaited()


@pytest.mark.asyncio
async def test_platform_session_only_after_real_authorization():
    identity = UserIdentity.create(email="authz@example.test", now=MOMENT).mark_email_verified(
        now=MOMENT
    )
    identity_repo = AsyncMock()
    identity_repo.get_by_id.return_value = identity
    session_repo = AsyncMock()
    authorizations = InMemoryPlatformMfaSessionAuthorizationRepository()
    auth = PlatformMfaSessionAuthorization.issue(
        user_id=identity.user_id,
        challenge_id=new_uuid(),
        credential_version=identity.credential_version,
        now=MOMENT,
    )
    await authorizations.insert(auth)
    use_case = CreatePlatformSessionUseCase(
        identities=identity_repo,
        sessions=session_repo,
        authorizations=authorizations,
        clock=lambda: MOMENT,
    )
    await use_case.execute(principal=_principal(identity), authorization_id=auth.authorization_id)
    session_repo.insert.assert_awaited_once()


@pytest.mark.asyncio
async def test_unconfigured_mfa_port_never_issues_ticket():
    port = UnconfiguredPlatformMfaVerification()
    with pytest.raises(PlatformMfaNotConfiguredError):
        await port.issue_verification_ticket(new_uuid())


@pytest.mark.asyncio
async def test_gym_session_stores_tenant_hint_without_authorization_logic():
    identity = UserIdentity.create(email="gym@example.test", now=MOMENT).mark_email_verified(
        now=MOMENT
    )
    identity_repo = AsyncMock()
    identity_repo.get_by_id.return_value = identity
    session_repo = AsyncMock()
    tenant_id = new_uuid()
    use_case = CreateGymSessionUseCase(
        identities=identity_repo,
        sessions=session_repo,
        clock=lambda: MOMENT,
    )
    created = await use_case.execute(
        principal=_principal(identity),
        active_tenant_id=tenant_id,
    )
    assert created.session.active_tenant_id == tenant_id


@pytest.mark.asyncio
async def test_resolve_rejects_session_revoked_during_touch_race():
    from gym_erp_api.modules.identity.application.use_cases.resolve_session import (
        ResolveSessionUseCase,
    )
    from gym_erp_api.modules.identity.domain.auth_session import AuthSession
    from gym_erp_api.modules.identity.domain.errors import SessionUpdateConflictError
    from gym_erp_api.modules.identity.domain.session_kind import SessionKind
    from gym_erp_api.modules.identity.infrastructure.crypto.session_token_hash import (
        generate_opaque_session_token,
        hash_session_token,
    )

    identity = UserIdentity.create(email="race@example.test", now=MOMENT).mark_email_verified(
        now=MOMENT
    )
    identity_repo = AsyncMock()
    identity_repo.get_by_id.return_value = identity
    token = generate_opaque_session_token()
    session = AuthSession.create(
        user_id=identity.user_id,
        session_kind=SessionKind.GYM,
        token_hash=hash_session_token(token),
        expires_at=MOMENT + timedelta(hours=1),
        idle_expires_at=MOMENT + timedelta(minutes=30),
        credential_version=0,
        now=MOMENT,
    )
    revoked = session.revoke(reason="logout", now=MOMENT)
    session_repo = AsyncMock()
    session_repo.get_by_token_hash.return_value = session
    session_repo.touch_activity = AsyncMock(side_effect=SessionUpdateConflictError("conflict"))
    session_repo.get_by_id.return_value = revoked
    use_case = ResolveSessionUseCase(
        identities=identity_repo,
        sessions=session_repo,
        clock=lambda: MOMENT + timedelta(minutes=2),
    )
    from gym_erp_api.modules.identity.application.errors import SessionResolutionFailedError

    with pytest.raises(SessionResolutionFailedError):
        await use_case.execute(opaque_token=token)


def test_identity_module_does_not_import_tenant_context():
    import gym_erp_api.modules.identity.application.use_cases.create_gym_session as gym_uc
    import gym_erp_api.modules.identity.application.use_cases.resolve_session as resolve_uc

    source_gym = open(gym_uc.__file__, encoding="utf-8").read()
    source_resolve = open(resolve_uc.__file__, encoding="utf-8").read()
    assert "TenantContext" not in source_gym
    assert "TenantContext" not in source_resolve
