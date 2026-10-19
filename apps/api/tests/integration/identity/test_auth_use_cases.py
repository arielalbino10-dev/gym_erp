"""Casos de uso auth internos contra gym_platform_test (H2-B.4)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from gym_erp_api.modules.identity.application.errors import (
    PlatformMfaRequiredError,
    PlatformSessionEmissionDisabledError,
)
from gym_erp_api.modules.identity.application.services.credential_verification_service import (
    CredentialVerificationService,
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
from gym_erp_api.modules.identity.domain.user_credential import UserCredential
from gym_erp_api.modules.identity.domain.user_identity import UserIdentity
from gym_erp_api.modules.identity.infrastructure.crypto.argon2_password_hasher import (
    Argon2PasswordHasher,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.identity_persistence,
    pytest.mark.asyncio(loop_scope="session"),
]

PASSWORD = "integration-test-password-12"


async def test_internal_auth_flow_gym_session(
    mongo_identity_repository,
    mongo_credential_repository,
    mongo_auth_session_repository,
):
    moment = datetime(2026, 8, 1, tzinfo=UTC)
    identity = UserIdentity.create(email="auth.flow@example.test", now=moment).mark_email_verified(
        now=moment
    )
    await mongo_identity_repository.save(identity)
    hasher = Argon2PasswordHasher()
    await mongo_credential_repository.insert(
        UserCredential.create(
            user_id=identity.user_id,
            password_hash=hasher.hash(PASSWORD),
            credential_version=0,
            now=moment,
        )
    )
    verify = CredentialVerificationService(
        identities=mongo_identity_repository,
        credentials=mongo_credential_repository,
        password_hasher=hasher,
    )
    principal = await verify.verify(email="auth.flow@example.test", password=PASSWORD)
    create = CreateGymSessionUseCase(
        identities=mongo_identity_repository,
        sessions=mongo_auth_session_repository,
        clock=lambda: moment,
    )
    created = await create.execute(principal=principal)
    resolve = ResolveSessionUseCase(
        identities=mongo_identity_repository,
        sessions=mongo_auth_session_repository,
        clock=lambda: moment,
    )
    resolved = await resolve.execute(opaque_token=created.opaque_token, touch_activity=False)
    assert resolved.user_id == identity.user_id

    revoke_all = RevokeAllUserSessionsUseCase(
        sessions=mongo_auth_session_repository,
        clock=lambda: moment,
    )
    await revoke_all.execute(user_id=identity.user_id, reason="test_cleanup")


async def test_platform_session_blocked_without_mfa(
    mongo_identity_repository,
    mongo_credential_repository,
    mongo_auth_session_repository,
    mongo_platform_mfa_session_authorization_repository,
):
    moment = datetime(2026, 8, 2, tzinfo=UTC)
    identity = UserIdentity.create(
        email="platform.block@example.test",
        now=moment,
    ).mark_email_verified(now=moment)
    await mongo_identity_repository.save(identity)
    hasher = Argon2PasswordHasher()
    await mongo_credential_repository.insert(
        UserCredential.create(
            user_id=identity.user_id,
            password_hash=hasher.hash(PASSWORD),
            credential_version=0,
            now=moment,
        )
    )
    verify = CredentialVerificationService(
        identities=mongo_identity_repository,
        credentials=mongo_credential_repository,
        password_hasher=hasher,
    )
    principal = await verify.verify(email="platform.block@example.test", password=PASSWORD)
    platform = CreatePlatformSessionUseCase(
        identities=mongo_identity_repository,
        sessions=mongo_auth_session_repository,
        clock=lambda: moment,
    )
    with pytest.raises(PlatformSessionEmissionDisabledError):
        await platform.execute(principal=principal, authorization_id=identity.user_id)
    platform_with_auth = CreatePlatformSessionUseCase(
        identities=mongo_identity_repository,
        sessions=mongo_auth_session_repository,
        authorizations=mongo_platform_mfa_session_authorization_repository,
        clock=lambda: moment,
    )
    with pytest.raises(PlatformMfaRequiredError):
        await platform_with_auth.execute(
            principal=principal,
            authorization_id=identity.user_id,
        )
