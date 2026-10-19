"""Flujo MFA TOTP platform contra gym_platform_test (H2-B.5)."""

from __future__ import annotations

from datetime import UTC, datetime

import pyotp
import pytest

from gym_erp_api.modules.identity.application.services.credential_verification_service import (
    CredentialVerificationService,
)
from gym_erp_api.modules.identity.application.use_cases.create_platform_session import (
    CreatePlatformSessionUseCase,
)
from gym_erp_api.modules.identity.application.use_cases.platform_mfa_totp import (
    BeginPlatformTotpEnrollmentUseCase,
    ConfirmPlatformTotpEnrollmentUseCase,
    StartPlatformMfaChallengeUseCase,
    VerifyPlatformMfaChallengeUseCase,
)
from gym_erp_api.modules.identity.domain.user_credential import UserCredential
from gym_erp_api.modules.identity.domain.user_identity import UserIdentity
from gym_erp_api.modules.identity.infrastructure.crypto.aes_gcm_mfa_encryptor import (
    AesGcmMfaSecretEncryptor,
)
from gym_erp_api.modules.identity.infrastructure.crypto.argon2_password_hasher import (
    Argon2PasswordHasher,
)
from gym_erp_api.modules.identity.infrastructure.crypto.pyotp_totp_service import PyotpTotpService
from tests.support.mfa_test_crypto import TEST_MFA_AES256_KEY

pytestmark = [
    pytest.mark.integration,
    pytest.mark.identity_mfa,
    pytest.mark.asyncio(loop_scope="session"),
]

PASSWORD = "integration-mfa-password-12"


async def test_platform_session_after_totp_mfa_flow(
    mongo_identity_repository,
    mongo_credential_repository,
    mongo_auth_session_repository,
    mongo_platform_totp_enrollment_repository,
    mongo_platform_mfa_challenge_repository,
    mongo_platform_mfa_step_repository,
    mongo_platform_mfa_session_authorization_repository,
):
    moment = datetime(2026, 8, 10, 15, 0, tzinfo=UTC)
    identity = UserIdentity.create(
        email="mfa.flow@example.test",
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
    encryptor = AesGcmMfaSecretEncryptor(key=TEST_MFA_AES256_KEY)
    totp = PyotpTotpService(valid_window=1)
    begin = BeginPlatformTotpEnrollmentUseCase(
        enrollments=mongo_platform_totp_enrollment_repository,
        encryptor=encryptor,
        totp=totp,
    )
    bundle = await begin.execute(
        user_id=identity.user_id,
        account_email=identity.email_normalized,
    )
    confirm_code = pyotp.TOTP(bundle.plaintext_secret.decode("ascii")).at(moment)
    confirm = ConfirmPlatformTotpEnrollmentUseCase(
        enrollments=mongo_platform_totp_enrollment_repository,
        encryptor=encryptor,
        totp=totp,
        clock=lambda: moment,
    )
    await confirm.execute(user_id=identity.user_id, totp_code=confirm_code)

    verify_creds = CredentialVerificationService(
        identities=mongo_identity_repository,
        credentials=mongo_credential_repository,
        password_hasher=hasher,
    )
    principal = await verify_creds.verify(email=identity.email_normalized, password=PASSWORD)

    start = StartPlatformMfaChallengeUseCase(
        enrollments=mongo_platform_totp_enrollment_repository,
        challenges=mongo_platform_mfa_challenge_repository,
        clock=lambda: moment,
    )
    challenge = await start.execute(principal=principal)
    login_code = pyotp.TOTP(bundle.plaintext_secret.decode("ascii")).at(moment)
    verify_mfa = VerifyPlatformMfaChallengeUseCase(
        enrollments=mongo_platform_totp_enrollment_repository,
        challenges=mongo_platform_mfa_challenge_repository,
        steps=mongo_platform_mfa_step_repository,
        authorizations=mongo_platform_mfa_session_authorization_repository,
        encryptor=encryptor,
        totp=totp,
        clock=lambda: moment,
    )
    grant = await verify_mfa.execute(
        principal=principal,
        challenge_id=challenge.challenge_id,
        totp_code=login_code,
    )

    platform = CreatePlatformSessionUseCase(
        identities=mongo_identity_repository,
        sessions=mongo_auth_session_repository,
        authorizations=mongo_platform_mfa_session_authorization_repository,
        clock=lambda: moment,
    )
    created = await platform.execute(
        principal=principal,
        authorization_id=grant.authorization_id,
    )
    assert created.session.user_id == identity.user_id
    assert created.opaque_token
