"""IdentityInfrastructure sobre colecciones efímeras de integración."""

from __future__ import annotations

from typing import Any

from gym_erp_api.core.config import Settings
from gym_erp_api.core.platform_mfa_crypto import resolve_platform_mfa_aes256_key
from gym_erp_api.infrastructure.identity.identity_container import IdentityInfrastructure
from gym_erp_api.modules.identity.application.services.credential_verification_service import (
    CredentialVerificationService,
)
from gym_erp_api.modules.identity.application.services.platform_session_eligibility import (
    PlatformSessionEligibilityService,
)
from gym_erp_api.modules.identity.application.use_cases.create_gym_session import (
    CreateGymSessionUseCase,
)
from gym_erp_api.modules.identity.application.use_cases.create_platform_session import (
    CreatePlatformSessionUseCase,
)
from gym_erp_api.modules.identity.application.use_cases.platform_auth_continuation import (
    CompletePlatformAuthContinuationMfaUseCase,
    CreatePlatformAuthContinuationUseCase,
    CreatePlatformSessionFromContinuationUseCase,
    ResolvePlatformAuthContinuationUseCase,
)
from gym_erp_api.modules.identity.application.use_cases.platform_mfa_totp import (
    BeginPlatformTotpEnrollmentUseCase,
    ConfirmPlatformTotpEnrollmentUseCase,
    StartPlatformMfaChallengeUseCase,
    VerifyPlatformMfaChallengeUseCase,
)
from gym_erp_api.modules.identity.application.use_cases.resolve_session import ResolveSessionUseCase
from gym_erp_api.modules.identity.application.use_cases.revoke_all_user_sessions import (
    RevokeAllUserSessionsUseCase,
)
from gym_erp_api.modules.identity.application.use_cases.revoke_session import RevokeSessionUseCase
from gym_erp_api.modules.identity.infrastructure.crypto.aes_gcm_mfa_encryptor import (
    AesGcmMfaSecretEncryptor,
)
from gym_erp_api.modules.identity.infrastructure.crypto.argon2_password_hasher import (
    Argon2PasswordHasher,
)
from gym_erp_api.modules.identity.infrastructure.crypto.pyotp_totp_service import PyotpTotpService
from gym_erp_api.modules.identity.infrastructure.mongo.mongo_auth_session_repository import (
    MongoAuthSessionRepository,
)
from gym_erp_api.modules.identity.infrastructure.mongo.mongo_credential_repository import (
    MongoCredentialRepository,
)
from gym_erp_api.modules.identity.infrastructure.mongo.mongo_identity_repository import (
    MongoIdentityRepository,
)
from gym_erp_api.modules.identity.infrastructure.mongo.mongo_platform_auth_continuation_repository import (  # noqa: E501
    MongoPlatformAuthContinuationRepository,
)
from gym_erp_api.modules.identity.infrastructure.mongo.mongo_platform_mfa_repositories import (
    MongoPlatformMfaChallengeRepository,
    MongoPlatformMfaSessionAuthorizationRepository,
    MongoPlatformMfaStepConsumptionRepository,
    MongoPlatformTotpEnrollmentRepository,
)
from gym_erp_api.modules.identity.infrastructure.mongo.mongo_platform_operator_eligibility_repository import (  # noqa: E501
    MongoPlatformOperatorEligibilityRepository,
)


def build_ephemeral_identity_infrastructure(
    *,
    settings: Settings,
    identities: Any,
    credentials: Any,
    sessions: Any,
    continuations: Any,
    mfa_totp: Any,
    mfa_challenges: Any,
    mfa_steps: Any,
    mfa_authz: Any,
    operator_eligibility: Any,
) -> IdentityInfrastructure:
    key = resolve_platform_mfa_aes256_key(settings)
    encryptor = AesGcmMfaSecretEncryptor(
        key=key,
        key_version=settings.platform_mfa_encryption_key_version,
    )
    totp = PyotpTotpService(valid_window=1)
    hasher = Argon2PasswordHasher()

    identity_repo = MongoIdentityRepository(identities)
    credential_repo = MongoCredentialRepository(credentials)
    session_repo = MongoAuthSessionRepository(sessions)
    enrollment_repo = MongoPlatformTotpEnrollmentRepository(mfa_totp)
    challenge_repo = MongoPlatformMfaChallengeRepository(mfa_challenges)
    step_repo = MongoPlatformMfaStepConsumptionRepository(mfa_steps)
    authz_repo = MongoPlatformMfaSessionAuthorizationRepository(mfa_authz)
    continuation_repo = MongoPlatformAuthContinuationRepository(continuations)
    eligibility_repo = MongoPlatformOperatorEligibilityRepository(operator_eligibility)

    credential_verification = CredentialVerificationService(
        identities=identity_repo,
        credentials=credential_repo,
        password_hasher=hasher,
    )
    create_platform = CreatePlatformSessionUseCase(
        identities=identity_repo,
        sessions=session_repo,
        authorizations=authz_repo,
    )
    start_mfa = StartPlatformMfaChallengeUseCase(
        enrollments=enrollment_repo,
        challenges=challenge_repo,
    )
    verify_mfa = VerifyPlatformMfaChallengeUseCase(
        enrollments=enrollment_repo,
        challenges=challenge_repo,
        steps=step_repo,
        authorizations=authz_repo,
        encryptor=encryptor,
        totp=totp,
    )

    return IdentityInfrastructure(
        identity_repository=identity_repo,
        credential_repository=credential_repo,
        auth_session_repository=session_repo,
        totp_enrollment_repository=enrollment_repo,
        mfa_challenge_repository=challenge_repo,
        mfa_step_repository=step_repo,
        mfa_authorization_repository=authz_repo,
        auth_continuation_repository=continuation_repo,
        password_hasher=hasher,
        mfa_encryptor=encryptor,
        totp_service=totp,
        credential_verification=credential_verification,
        create_gym_session=CreateGymSessionUseCase(
            identities=identity_repo,
            sessions=session_repo,
        ),
        create_platform_session=create_platform,
        resolve_session=ResolveSessionUseCase(
            identities=identity_repo,
            sessions=session_repo,
        ),
        revoke_session=RevokeSessionUseCase(sessions=session_repo),
        revoke_all_user_sessions=RevokeAllUserSessionsUseCase(sessions=session_repo),
        begin_totp_enrollment=BeginPlatformTotpEnrollmentUseCase(
            enrollments=enrollment_repo,
            encryptor=encryptor,
            totp=totp,
        ),
        confirm_totp_enrollment=ConfirmPlatformTotpEnrollmentUseCase(
            enrollments=enrollment_repo,
            encryptor=encryptor,
            totp=totp,
        ),
        start_platform_mfa_challenge=start_mfa,
        verify_platform_mfa_challenge=verify_mfa,
        create_auth_continuation=CreatePlatformAuthContinuationUseCase(
            continuations=continuation_repo,
        ),
        resolve_auth_continuation=ResolvePlatformAuthContinuationUseCase(
            continuations=continuation_repo,
        ),
        complete_auth_continuation_mfa=CompletePlatformAuthContinuationMfaUseCase(
            continuations=continuation_repo,
            start_mfa=start_mfa,
            verify_mfa=verify_mfa,
        ),
        create_platform_session_from_continuation=CreatePlatformSessionFromContinuationUseCase(
            continuations=continuation_repo,
            create_session=create_platform,
        ),
        platform_session_eligibility=PlatformSessionEligibilityService(
            eligibility=eligibility_repo,
        ),
    )
