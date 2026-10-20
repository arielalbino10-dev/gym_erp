"""Composición de servicios identity/MFA en gym_platform (H2-B.6)."""

from __future__ import annotations

from dataclasses import dataclass

from pymongo.asynchronous.database import AsyncDatabase

from gym_erp_api.core.config import Settings
from gym_erp_api.core.platform_mfa_crypto import resolve_platform_mfa_aes256_key
from gym_erp_api.infrastructure.mongo.mongo_databases import MongoDatabases
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
    PLATFORM_OPERATOR_ELIGIBILITIES_COLLECTION,
    MongoPlatformOperatorEligibilityRepository,
)
from gym_erp_api.modules.identity.infrastructure.mongo.platform_auth_continuation_mappers import (
    PLATFORM_AUTH_CONTINUATIONS_COLLECTION,
)
from gym_erp_api.modules.identity.infrastructure.mongo.platform_mfa_mappers import (
    PLATFORM_MFA_AUTHORIZATIONS_COLLECTION,
    PLATFORM_MFA_CHALLENGES_COLLECTION,
    PLATFORM_MFA_STEPS_COLLECTION,
    PLATFORM_MFA_TOTP_COLLECTION,
)


@dataclass(frozen=True, slots=True)
class IdentityInfrastructure:
    """Dependencias identity platform (solo gym_platform para auth/MFA)."""

    identity_repository: MongoIdentityRepository
    credential_repository: MongoCredentialRepository
    auth_session_repository: MongoAuthSessionRepository
    totp_enrollment_repository: MongoPlatformTotpEnrollmentRepository
    mfa_challenge_repository: MongoPlatformMfaChallengeRepository
    mfa_step_repository: MongoPlatformMfaStepConsumptionRepository
    mfa_authorization_repository: MongoPlatformMfaSessionAuthorizationRepository
    auth_continuation_repository: MongoPlatformAuthContinuationRepository
    password_hasher: Argon2PasswordHasher
    mfa_encryptor: AesGcmMfaSecretEncryptor
    totp_service: PyotpTotpService
    credential_verification: CredentialVerificationService
    create_gym_session: CreateGymSessionUseCase
    create_platform_session: CreatePlatformSessionUseCase
    resolve_session: ResolveSessionUseCase
    revoke_session: RevokeSessionUseCase
    revoke_all_user_sessions: RevokeAllUserSessionsUseCase
    begin_totp_enrollment: BeginPlatformTotpEnrollmentUseCase
    confirm_totp_enrollment: ConfirmPlatformTotpEnrollmentUseCase
    start_platform_mfa_challenge: StartPlatformMfaChallengeUseCase
    verify_platform_mfa_challenge: VerifyPlatformMfaChallengeUseCase
    create_auth_continuation: CreatePlatformAuthContinuationUseCase
    resolve_auth_continuation: ResolvePlatformAuthContinuationUseCase
    complete_auth_continuation_mfa: CompletePlatformAuthContinuationMfaUseCase
    create_platform_session_from_continuation: CreatePlatformSessionFromContinuationUseCase
    platform_session_eligibility: PlatformSessionEligibilityService


def _platform_db(databases: MongoDatabases) -> AsyncDatabase:
    return databases.platform


def build_identity_infrastructure(
    databases: MongoDatabases,
    settings: Settings,
) -> IdentityInfrastructure:
    platform = _platform_db(databases)
    key = resolve_platform_mfa_aes256_key(settings)
    encryptor = AesGcmMfaSecretEncryptor(
        key=key,
        key_version=settings.platform_mfa_encryption_key_version,
    )
    totp = PyotpTotpService(valid_window=1)
    hasher = Argon2PasswordHasher()

    identities = MongoIdentityRepository(platform["user_identities"])
    credentials = MongoCredentialRepository(platform["user_credentials"])
    sessions = MongoAuthSessionRepository(platform["auth_sessions"])
    enrollments = MongoPlatformTotpEnrollmentRepository(platform[PLATFORM_MFA_TOTP_COLLECTION])
    challenges = MongoPlatformMfaChallengeRepository(platform[PLATFORM_MFA_CHALLENGES_COLLECTION])
    steps = MongoPlatformMfaStepConsumptionRepository(platform[PLATFORM_MFA_STEPS_COLLECTION])
    authorizations = MongoPlatformMfaSessionAuthorizationRepository(
        platform[PLATFORM_MFA_AUTHORIZATIONS_COLLECTION]
    )
    continuations = MongoPlatformAuthContinuationRepository(
        platform[PLATFORM_AUTH_CONTINUATIONS_COLLECTION]
    )
    operator_eligibility = MongoPlatformOperatorEligibilityRepository(
        platform[PLATFORM_OPERATOR_ELIGIBILITIES_COLLECTION]
    )

    credential_verification = CredentialVerificationService(
        identities=identities,
        credentials=credentials,
        password_hasher=hasher,
    )
    create_platform = CreatePlatformSessionUseCase(
        identities=identities,
        sessions=sessions,
        authorizations=authorizations,
    )
    start_mfa = StartPlatformMfaChallengeUseCase(
        enrollments=enrollments,
        challenges=challenges,
    )
    verify_mfa = VerifyPlatformMfaChallengeUseCase(
        enrollments=enrollments,
        challenges=challenges,
        steps=steps,
        authorizations=authorizations,
        encryptor=encryptor,
        totp=totp,
    )

    return IdentityInfrastructure(
        identity_repository=identities,
        credential_repository=credentials,
        auth_session_repository=sessions,
        totp_enrollment_repository=enrollments,
        mfa_challenge_repository=challenges,
        mfa_step_repository=steps,
        mfa_authorization_repository=authorizations,
        auth_continuation_repository=continuations,
        password_hasher=hasher,
        mfa_encryptor=encryptor,
        totp_service=totp,
        credential_verification=credential_verification,
        create_gym_session=CreateGymSessionUseCase(
            identities=identities,
            sessions=sessions,
        ),
        create_platform_session=create_platform,
        resolve_session=ResolveSessionUseCase(
            identities=identities,
            sessions=sessions,
        ),
        revoke_session=RevokeSessionUseCase(sessions=sessions),
        revoke_all_user_sessions=RevokeAllUserSessionsUseCase(sessions=sessions),
        begin_totp_enrollment=BeginPlatformTotpEnrollmentUseCase(
            enrollments=enrollments,
            encryptor=encryptor,
            totp=totp,
        ),
        confirm_totp_enrollment=ConfirmPlatformTotpEnrollmentUseCase(
            enrollments=enrollments,
            encryptor=encryptor,
            totp=totp,
        ),
        start_platform_mfa_challenge=start_mfa,
        verify_platform_mfa_challenge=verify_mfa,
        create_auth_continuation=CreatePlatformAuthContinuationUseCase(
            continuations=continuations,
        ),
        resolve_auth_continuation=ResolvePlatformAuthContinuationUseCase(
            continuations=continuations,
        ),
        complete_auth_continuation_mfa=CompletePlatformAuthContinuationMfaUseCase(
            continuations=continuations,
            start_mfa=start_mfa,
            verify_mfa=verify_mfa,
        ),
        create_platform_session_from_continuation=CreatePlatformSessionFromContinuationUseCase(
            continuations=continuations,
            create_session=create_platform,
        ),
        platform_session_eligibility=PlatformSessionEligibilityService(
            eligibility=operator_eligibility,
        ),
    )
