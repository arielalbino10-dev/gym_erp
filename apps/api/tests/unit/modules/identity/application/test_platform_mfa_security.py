"""H2-B.5.1 — pruebas negativas de seguridad MFA."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pyotp
import pytest

from gym_erp_api.modules.identity.application.dto.auth_results import VerifiedPrincipal
from gym_erp_api.modules.identity.application.errors import (
    PlatformMfaRequiredError,
    PlatformMfaVerificationFailedError,
)
from gym_erp_api.modules.identity.application.use_cases.create_platform_session import (
    CreatePlatformSessionUseCase,
)
from gym_erp_api.modules.identity.application.use_cases.platform_mfa_totp import (
    StartPlatformMfaChallengeUseCase,
    VerifyPlatformMfaChallengeUseCase,
)
from gym_erp_api.modules.identity.domain.platform_mfa.platform_mfa_session_authorization import (
    PlatformMfaSessionAuthorization,
)
from gym_erp_api.modules.identity.domain.platform_mfa.platform_totp_enrollment import (
    PlatformTotpEnrollment,
)
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


def _principal(user_id: str, *, verified_at: datetime | None = None) -> VerifiedPrincipal:
    return VerifiedPrincipal(
        user_id=user_id,
        credential_version=0,
        email_normalized="sec@example.test",
        verified_at=verified_at or MOMENT,
    )


@pytest.mark.asyncio
async def test_start_challenge_rejects_stale_password_proof():
    user_id = new_uuid()
    enrollments = InMemoryPlatformTotpEnrollmentRepository()
    encryptor = AesGcmMfaSecretEncryptor(key=TEST_MFA_AES256_KEY)
    secret = pyotp.random_base32().encode("ascii")
    await enrollments.save(
        PlatformTotpEnrollment.begin_pending(
            user_id=user_id,
            encrypted_secret=encryptor.encrypt(secret),
            now=MOMENT,
        ).activate(now=MOMENT)
    )
    stale = MOMENT + timedelta(minutes=6)
    start = StartPlatformMfaChallengeUseCase(
        enrollments=enrollments,
        challenges=InMemoryPlatformMfaChallengeRepository(),
        clock=lambda: stale,
    )
    with pytest.raises(PlatformMfaVerificationFailedError):
        await start.execute(principal=_principal(user_id, verified_at=MOMENT))


@pytest.mark.asyncio
async def test_verify_rejects_challenge_for_other_user():
    owner = new_uuid()
    attacker = new_uuid()
    enrollments = InMemoryPlatformTotpEnrollmentRepository()
    challenges = InMemoryPlatformMfaChallengeRepository()
    encryptor = AesGcmMfaSecretEncryptor(key=TEST_MFA_AES256_KEY)
    secret = pyotp.random_base32().encode("ascii")
    await enrollments.save(
        PlatformTotpEnrollment.begin_pending(
            user_id=owner,
            encrypted_secret=encryptor.encrypt(secret),
            now=MOMENT,
        ).activate(now=MOMENT)
    )
    start = StartPlatformMfaChallengeUseCase(
        enrollments=enrollments,
        challenges=challenges,
        clock=lambda: MOMENT,
    )
    challenge = await start.execute(principal=_principal(owner))
    verify = VerifyPlatformMfaChallengeUseCase(
        enrollments=enrollments,
        challenges=challenges,
        steps=InMemoryPlatformMfaStepConsumptionRepository(),
        authorizations=InMemoryPlatformMfaSessionAuthorizationRepository(),
        encryptor=encryptor,
        totp=PyotpTotpService(valid_window=1),
        clock=lambda: MOMENT,
    )
    code = pyotp.TOTP(secret.decode("ascii")).at(MOMENT)
    with pytest.raises(PlatformMfaVerificationFailedError):
        await verify.execute(
            principal=_principal(attacker),
            challenge_id=challenge.challenge_id,
            totp_code=code,
        )


@pytest.mark.asyncio
async def test_fifth_attempt_can_complete_with_valid_totp():
    user_id = new_uuid()
    enrollments = InMemoryPlatformTotpEnrollmentRepository()
    challenges = InMemoryPlatformMfaChallengeRepository()
    steps = InMemoryPlatformMfaStepConsumptionRepository()
    authorizations = InMemoryPlatformMfaSessionAuthorizationRepository()
    encryptor = AesGcmMfaSecretEncryptor(key=TEST_MFA_AES256_KEY)
    totp = PyotpTotpService(valid_window=1)
    secret = pyotp.random_base32().encode("ascii")
    await enrollments.save(
        PlatformTotpEnrollment.begin_pending(
            user_id=user_id,
            encrypted_secret=encryptor.encrypt(secret),
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
    principal = _principal(user_id)
    challenge = await start.execute(principal=principal)
    for _ in range(4):
        with pytest.raises(PlatformMfaVerificationFailedError):
            await verify.execute(
                principal=principal,
                challenge_id=challenge.challenge_id,
                totp_code="000000",
            )
    code = pyotp.TOTP(secret.decode("ascii")).at(MOMENT)
    grant = await verify.execute(
        principal=principal,
        challenge_id=challenge.challenge_id,
        totp_code=code,
    )
    assert grant.authorization_id


@pytest.mark.asyncio
async def test_session_rejects_authorization_for_other_user():
    identity = UserIdentity.create(email="victim@example.test", now=MOMENT).mark_email_verified(
        now=MOMENT
    )
    other_id = new_uuid()
    authorizations = InMemoryPlatformMfaSessionAuthorizationRepository()
    auth = PlatformMfaSessionAuthorization.issue(
        user_id=identity.user_id,
        challenge_id=new_uuid(),
        credential_version=0,
        now=MOMENT,
    )
    await authorizations.insert(auth)
    identity_repo = AsyncMock()
    identity_repo.get_by_id.return_value = identity
    use_case = CreatePlatformSessionUseCase(
        identities=identity_repo,
        sessions=AsyncMock(),
        authorizations=authorizations,
        clock=lambda: MOMENT,
    )
    attacker = VerifiedPrincipal(
        user_id=other_id,
        credential_version=0,
        email_normalized="attacker@example.test",
        verified_at=MOMENT,
    )
    with pytest.raises(PlatformMfaRequiredError):
        await use_case.execute(principal=attacker, authorization_id=auth.authorization_id)


@pytest.mark.asyncio
async def test_session_rejects_obsolete_credential_version_on_authorization():
    identity = (
        UserIdentity.create(email="ver@example.test", now=MOMENT)
        .mark_email_verified(now=MOMENT)
        .increment_credential_version(now=MOMENT)
    )
    authorizations = InMemoryPlatformMfaSessionAuthorizationRepository()
    auth = PlatformMfaSessionAuthorization.issue(
        user_id=identity.user_id,
        challenge_id=new_uuid(),
        credential_version=0,
        now=MOMENT,
    )
    await authorizations.insert(auth)
    identity_repo = AsyncMock()
    identity_repo.get_by_id.return_value = identity
    use_case = CreatePlatformSessionUseCase(
        identities=identity_repo,
        sessions=AsyncMock(),
        authorizations=authorizations,
        clock=lambda: MOMENT,
    )
    principal = VerifiedPrincipal(
        user_id=identity.user_id,
        credential_version=identity.credential_version,
        email_normalized=identity.email_normalized,
        verified_at=MOMENT,
    )
    with pytest.raises(PlatformMfaRequiredError):
        await use_case.execute(principal=principal, authorization_id=auth.authorization_id)


@pytest.mark.asyncio
async def test_start_reuses_single_open_challenge_per_user():
    user_id = new_uuid()
    enrollments = InMemoryPlatformTotpEnrollmentRepository()
    challenges = InMemoryPlatformMfaChallengeRepository()
    encryptor = AesGcmMfaSecretEncryptor(key=TEST_MFA_AES256_KEY)
    secret = pyotp.random_base32().encode("ascii")
    await enrollments.save(
        PlatformTotpEnrollment.begin_pending(
            user_id=user_id,
            encrypted_secret=encryptor.encrypt(secret),
            now=MOMENT,
        ).activate(now=MOMENT)
    )
    start = StartPlatformMfaChallengeUseCase(
        enrollments=enrollments,
        challenges=challenges,
        clock=lambda: MOMENT,
    )
    principal = _principal(user_id)
    first = await start.execute(principal=principal)
    second = await start.execute(principal=principal)
    assert first.challenge_id == second.challenge_id


def test_aes_rejects_unknown_key_version_and_tampered_ciphertext():
    encryptor = AesGcmMfaSecretEncryptor(key=TEST_MFA_AES256_KEY, key_version=1)
    enc = encryptor.encrypt(b"SECRETBASE32PADDING!!")
    other_version = AesGcmMfaSecretEncryptor(key=TEST_MFA_AES256_KEY, key_version=2)
    with pytest.raises(ValueError, match="Versión de clave"):
        other_version.decrypt(enc)
    tampered = bytearray(enc.ciphertext)
    tampered[-1] ^= 0xFF
    from gym_erp_api.modules.identity.domain.platform_mfa.encrypted_secret import EncryptedMfaSecret

    bad = EncryptedMfaSecret(key_version=enc.key_version, ciphertext=bytes(tampered))
    with pytest.raises(Exception):
        encryptor.decrypt(bad)
