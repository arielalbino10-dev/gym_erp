from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pyotp
import pytest

from gym_erp_api.modules.identity.application.dto.auth_results import VerifiedPrincipal
from gym_erp_api.modules.identity.application.errors import PlatformAuthContinuationError
from gym_erp_api.modules.identity.application.use_cases.create_platform_session import (
    CreatePlatformSessionUseCase,
)
from gym_erp_api.modules.identity.application.use_cases.platform_auth_continuation import (
    CompletePlatformAuthContinuationMfaUseCase,
    CreatePlatformAuthContinuationUseCase,
    CreatePlatformSessionFromContinuationUseCase,
)
from gym_erp_api.modules.identity.application.use_cases.platform_mfa_totp import (
    StartPlatformMfaChallengeUseCase,
    VerifyPlatformMfaChallengeUseCase,
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
from tests.support.in_memory_platform_auth_continuation_repository import (
    InMemoryPlatformAuthContinuationRepository,
)
from tests.support.in_memory_platform_mfa_repositories import (
    InMemoryPlatformMfaChallengeRepository,
    InMemoryPlatformMfaSessionAuthorizationRepository,
    InMemoryPlatformMfaStepConsumptionRepository,
    InMemoryPlatformTotpEnrollmentRepository,
)
from tests.support.mfa_test_crypto import TEST_MFA_AES256_KEY

MOMENT = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


def _principal(user_id: str) -> VerifiedPrincipal:
    return VerifiedPrincipal(
        user_id=user_id,
        credential_version=0,
        email_normalized="cont@example.test",
        verified_at=MOMENT,
    )


@pytest.fixture
def continuation_stack():
    continuations = InMemoryPlatformAuthContinuationRepository()
    enrollments = InMemoryPlatformTotpEnrollmentRepository()
    challenges = InMemoryPlatformMfaChallengeRepository()
    steps = InMemoryPlatformMfaStepConsumptionRepository()
    authorizations = InMemoryPlatformMfaSessionAuthorizationRepository()
    encryptor = AesGcmMfaSecretEncryptor(key=TEST_MFA_AES256_KEY)
    totp = PyotpTotpService(valid_window=1)
    return continuations, enrollments, challenges, steps, authorizations, encryptor, totp


@pytest.mark.asyncio
async def test_continuation_end_to_end_platform_session(continuation_stack):
    continuations, enrollments, challenges, steps, authorizations, encryptor, totp = (
        continuation_stack
    )
    user_id = new_uuid()
    identity = UserIdentity.create(
        email="cont@example.test",
        user_id=user_id,
        now=MOMENT,
    ).mark_email_verified(now=MOMENT)
    secret_bytes = pyotp.random_base32().encode("ascii")
    await enrollments.save(
        PlatformTotpEnrollment.begin_pending(
            user_id=user_id,
            encrypted_secret=encryptor.encrypt(secret_bytes),
            now=MOMENT,
        ).activate(now=MOMENT)
    )
    create_cont = CreatePlatformAuthContinuationUseCase(
        continuations=continuations,
        clock=lambda: MOMENT,
    )
    bundle = await create_cont.execute(principal=_principal(user_id))
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
    complete = CompletePlatformAuthContinuationMfaUseCase(
        continuations=continuations,
        start_mfa=start,
        verify_mfa=verify,
        clock=lambda: MOMENT,
    )
    code = pyotp.TOTP(secret_bytes.decode("ascii")).at(MOMENT)
    ctx = await complete.execute(opaque_token=bundle.opaque_token, totp_code=code)
    assert ctx.authorization_id

    identity_repo = AsyncMock()
    identity_repo.get_by_id.return_value = identity
    session_repo = AsyncMock()
    create_session = CreatePlatformSessionUseCase(
        identities=identity_repo,
        sessions=session_repo,
        authorizations=authorizations,
        clock=lambda: MOMENT,
    )
    from_continuation = CreatePlatformSessionFromContinuationUseCase(
        continuations=continuations,
        create_session=create_session,
        clock=lambda: MOMENT,
    )
    created = await from_continuation.execute(opaque_token=bundle.opaque_token)
    assert created.session.session_kind is SessionKind.PLATFORM
    with pytest.raises(PlatformAuthContinuationError):
        await from_continuation.execute(opaque_token=bundle.opaque_token)


@pytest.mark.asyncio
async def test_second_open_continuation_rejected(continuation_stack):
    continuations, *_ = continuation_stack
    user_id = new_uuid()
    create_cont = CreatePlatformAuthContinuationUseCase(
        continuations=continuations,
        clock=lambda: MOMENT,
    )
    await create_cont.execute(principal=_principal(user_id))
    with pytest.raises(PlatformAuthContinuationError):
        await create_cont.execute(principal=_principal(user_id))


@pytest.mark.asyncio
async def test_continuation_token_not_in_repr(continuation_stack):
    continuations, *_ = continuation_stack
    create_cont = CreatePlatformAuthContinuationUseCase(
        continuations=continuations,
        clock=lambda: MOMENT,
    )
    bundle = await create_cont.execute(principal=_principal(new_uuid()))
    assert bundle.opaque_token not in repr(bundle)
