from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pyotp
import pytest

from gym_erp_api.modules.identity.application.errors import (
    PlatformMfaRequiredError,
    PlatformMfaVerificationFailedError,
    PlatformSessionEmissionDisabledError,
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
from gym_erp_api.modules.identity.domain.platform_mfa.platform_mfa_session_authorization import (
    PlatformMfaSessionAuthorization,
)
from gym_erp_api.modules.identity.domain.platform_mfa.platform_totp_enrollment import (
    PlatformTotpEnrollment,
)
from gym_erp_api.modules.identity.domain.session_kind import SessionKind
from gym_erp_api.modules.identity.domain.user_identity import UserIdentity
from gym_erp_api.modules.identity.infrastructure.crypto.aes_gcm_mfa_encryptor import (
    AesGcmMfaSecretEncryptor,
)
from gym_erp_api.modules.identity.infrastructure.crypto.pyotp_totp_service import PyotpTotpService
from gym_erp_api.shared_kernel.identifiers import new_uuid
from tests.support.in_memory_platform_mfa_repositories import (
    InMemoryPlatformMfaChallengeRepository,
    InMemoryPlatformMfaSessionAuthorizationRepository,
    InMemoryPlatformMfaStepConsumptionRepository,
    InMemoryPlatformTotpEnrollmentRepository,
)
from tests.support.mfa_test_crypto import TEST_MFA_AES256_KEY

MOMENT = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def _principal(*, user_id: str, credential_version: int = 0, email: str = "mfa@example.test"):
    from gym_erp_api.modules.identity.application.dto.auth_results import VerifiedPrincipal

    return VerifiedPrincipal(
        user_id=user_id,
        credential_version=credential_version,
        email_normalized=email,
        verified_at=MOMENT,
    )


@pytest.fixture
def totp_stack():
    encryptor = AesGcmMfaSecretEncryptor(key=TEST_MFA_AES256_KEY)
    totp = PyotpTotpService(valid_window=1)
    enrollments = InMemoryPlatformTotpEnrollmentRepository()
    challenges = InMemoryPlatformMfaChallengeRepository()
    steps = InMemoryPlatformMfaStepConsumptionRepository()
    authorizations = InMemoryPlatformMfaSessionAuthorizationRepository()
    return encryptor, totp, enrollments, challenges, steps, authorizations


@pytest.mark.asyncio
async def test_enrollment_pending_confirm_activate(totp_stack):
    encryptor, totp, enrollments, *_ = totp_stack
    user_id = new_uuid()
    begin = BeginPlatformTotpEnrollmentUseCase(
        enrollments=enrollments,
        encryptor=encryptor,
        totp=totp,
    )
    bundle = await begin.execute(user_id=user_id, account_email="admin@example.test")
    code = pyotp.TOTP(bundle.plaintext_secret.decode("ascii")).at(MOMENT)
    confirm = ConfirmPlatformTotpEnrollmentUseCase(
        enrollments=enrollments,
        encryptor=encryptor,
        totp=totp,
        clock=lambda: MOMENT,
    )
    await confirm.execute(user_id=user_id, totp_code=code)
    stored = await enrollments.get_by_user_id(user_id)
    assert stored is not None
    assert stored.status.value == "enabled"


@pytest.mark.asyncio
async def test_totp_replay_rejected(totp_stack):
    encryptor, totp, enrollments, challenges, steps, authorizations = totp_stack
    user_id = new_uuid()
    secret_bytes = pyotp.random_base32().encode("ascii")
    encrypted = encryptor.encrypt(secret_bytes)
    await enrollments.save(
        PlatformTotpEnrollment.begin_pending(
            user_id=user_id,
            encrypted_secret=encrypted,
            now=MOMENT,
        ).activate(now=MOMENT)
    )
    start = StartPlatformMfaChallengeUseCase(
        enrollments=enrollments,
        challenges=challenges,
        clock=lambda: MOMENT,
    )
    verify = VerifyPlatformMfaChallengeUseCase(
        enrollments=enrollments,
        challenges=challenges,
        steps=steps,
        authorizations=authorizations,
        encryptor=encryptor,
        totp=totp,
        clock=lambda: MOMENT,
    )
    principal = _principal(user_id=user_id)
    challenge = await start.execute(principal=principal)
    code = pyotp.TOTP(secret_bytes.decode("ascii")).at(MOMENT)
    await verify.execute(
        principal=principal,
        challenge_id=challenge.challenge_id,
        totp_code=code,
    )
    challenge2 = await start.execute(principal=principal)
    with pytest.raises(PlatformMfaVerificationFailedError):
        await verify.execute(
            principal=principal,
            challenge_id=challenge2.challenge_id,
            totp_code=code,
        )


@pytest.mark.asyncio
async def test_platform_session_requires_consumed_authorization(totp_stack):

    _, _, _, _, _, authorizations = totp_stack
    user_id = new_uuid()
    identity = UserIdentity.create(email="plat@example.test", now=MOMENT).mark_email_verified(
        now=MOMENT
    )
    identity_repo = AsyncMock()
    identity_repo.get_by_id.return_value = identity
    session_repo = AsyncMock()
    principal = _principal(user_id=user_id, email="plat@example.test")
    use_case = CreatePlatformSessionUseCase(
        identities=identity_repo,
        sessions=session_repo,
        authorizations=None,
    )
    with pytest.raises(PlatformSessionEmissionDisabledError):
        await use_case.execute(principal=principal, authorization_id=new_uuid())

    auth = PlatformMfaSessionAuthorization.issue(
        user_id=identity.user_id,
        challenge_id=new_uuid(),
        credential_version=identity.credential_version,
        now=MOMENT,
    )
    await authorizations.insert(auth)
    use_case2 = CreatePlatformSessionUseCase(
        identities=identity_repo,
        sessions=session_repo,
        authorizations=authorizations,
        clock=lambda: MOMENT,
    )
    principal_ok = _principal(
        user_id=identity.user_id,
        credential_version=identity.credential_version,
        email=identity.email_normalized,
    )
    created = await use_case2.execute(
        principal=principal_ok,
        authorization_id=auth.authorization_id,
    )
    assert created.session.session_kind is SessionKind.PLATFORM
    with pytest.raises(PlatformMfaRequiredError):
        await use_case2.execute(
            principal=principal_ok,
            authorization_id=auth.authorization_id,
        )


@pytest.mark.asyncio
async def test_invalid_totp_increments_failed_attempts(totp_stack):
    encryptor, totp, enrollments, challenges, steps, authorizations = totp_stack
    user_id = new_uuid()
    secret_bytes = pyotp.random_base32().encode("ascii")
    encrypted = encryptor.encrypt(secret_bytes)
    await enrollments.save(
        PlatformTotpEnrollment.begin_pending(
            user_id=user_id,
            encrypted_secret=encrypted,
            now=MOMENT,
        ).activate(now=MOMENT)
    )
    start = StartPlatformMfaChallengeUseCase(
        enrollments=enrollments,
        challenges=challenges,
        clock=lambda: MOMENT,
    )
    verify = VerifyPlatformMfaChallengeUseCase(
        enrollments=enrollments,
        challenges=challenges,
        steps=steps,
        authorizations=authorizations,
        encryptor=encryptor,
        totp=totp,
        clock=lambda: MOMENT,
    )
    principal = _principal(user_id=user_id)
    challenge = await start.execute(principal=principal)
    with pytest.raises(PlatformMfaVerificationFailedError):
        await verify.execute(
            principal=principal,
            challenge_id=challenge.challenge_id,
            totp_code="000000",
        )
    updated = await challenges.get_by_id(challenge.challenge_id)
    assert updated is not None
    assert updated.failed_attempts == 1


@pytest.mark.asyncio
async def test_expired_challenge_rejected(totp_stack):
    encryptor, totp, enrollments, challenges, steps, authorizations = totp_stack
    user_id = new_uuid()
    secret_bytes = pyotp.random_base32().encode("ascii")
    encrypted = encryptor.encrypt(secret_bytes)
    await enrollments.save(
        PlatformTotpEnrollment.begin_pending(
            user_id=user_id,
            encrypted_secret=encrypted,
            now=MOMENT,
        ).activate(now=MOMENT)
    )
    start = StartPlatformMfaChallengeUseCase(
        enrollments=enrollments,
        challenges=challenges,
        clock=lambda: MOMENT,
    )
    principal = _principal(user_id=user_id)
    challenge = await start.execute(principal=principal)
    late = MOMENT + timedelta(minutes=10)
    verify = VerifyPlatformMfaChallengeUseCase(
        enrollments=enrollments,
        challenges=challenges,
        steps=steps,
        authorizations=authorizations,
        encryptor=encryptor,
        totp=totp,
        clock=lambda: late,
    )
    code = pyotp.TOTP(secret_bytes.decode("ascii")).at(late)
    with pytest.raises(PlatformMfaVerificationFailedError):
        await verify.execute(
            principal=_principal(user_id=user_id, email="late@example.test"),
            challenge_id=challenge.challenge_id,
            totp_code=code,
        )


def test_encrypted_secret_not_in_repr():
    encryptor = AesGcmMfaSecretEncryptor(key=TEST_MFA_AES256_KEY)
    enc = encryptor.encrypt(b"ABCDEFGHIJKLMNOPQRST")
    assert "ABCDEF" not in repr(enc)
