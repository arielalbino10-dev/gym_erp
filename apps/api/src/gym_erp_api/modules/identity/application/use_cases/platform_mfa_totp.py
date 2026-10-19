"""Casos de uso MFA TOTP platform (sin HTTP)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from gym_erp_api.modules.identity.application.dto.auth_results import VerifiedPrincipal
from gym_erp_api.modules.identity.application.errors import (
    PlatformMfaNotConfiguredError,
    PlatformMfaVerificationFailedError,
)
from gym_erp_api.modules.identity.application.ports import (
    PlatformMfaChallengeRepository,
    PlatformMfaSessionAuthorizationRepository,
    PlatformMfaStepConsumptionRepository,
    PlatformTotpEnrollmentRepository,
)
from gym_erp_api.modules.identity.application.ports.mfa_secret_encryptor import MfaSecretEncryptor
from gym_erp_api.modules.identity.application.ports.totp_service import TotpService
from gym_erp_api.modules.identity.domain.platform_mfa.enums import TotpEnrollmentStatus
from gym_erp_api.modules.identity.domain.platform_mfa.platform_mfa_challenge import (
    PlatformMfaChallenge,
)
from gym_erp_api.modules.identity.domain.platform_mfa.platform_mfa_session_authorization import (
    PlatformMfaSessionAuthorization,
)
from gym_erp_api.modules.identity.domain.platform_mfa.platform_totp_enrollment import (
    PlatformTotpEnrollment,
)
from gym_erp_api.modules.identity.domain.time_utils import utc_now_ms
from gym_erp_api.modules.identity.domain.validators import require_user_uuid_v4

_GENERIC_MFA_FAILURE = "Verificación MFA inválida o expirada."
_STEP_TTL = timedelta(hours=24)
_PASSWORD_PROOF_TTL = timedelta(minutes=5)


def _assert_fresh_password_proof(principal: VerifiedPrincipal, now: datetime) -> None:
    if principal.verified_at.tzinfo is None:
        raise PlatformMfaVerificationFailedError(_GENERIC_MFA_FAILURE)
    if now - principal.verified_at > _PASSWORD_PROOF_TTL:
        raise PlatformMfaVerificationFailedError(_GENERIC_MFA_FAILURE)


@dataclass(frozen=True, slots=True)
class BeginTotpEnrollmentSecretBundle:
    """Secreto en claro — entregar una sola vez; no loguear."""

    provisioning_uri: str
    plaintext_secret: bytes = field(repr=False)


@dataclass(frozen=True, slots=True)
class PlatformMfaAuthorizationGrant:
    authorization_id: str
    user_id: str


class BeginPlatformTotpEnrollmentUseCase:
    def __init__(
        self,
        *,
        enrollments: PlatformTotpEnrollmentRepository,
        encryptor: MfaSecretEncryptor,
        totp: TotpService,
        issuer: str = "Gym ERP Platform",
    ) -> None:
        self._enrollments = enrollments
        self._encryptor = encryptor
        self._totp = totp
        self._issuer = issuer

    async def execute(self, *, user_id: str, account_email: str) -> BeginTotpEnrollmentSecretBundle:
        uid = require_user_uuid_v4(user_id)
        existing = await self._enrollments.get_by_user_id(uid)
        if existing and existing.status is TotpEnrollmentStatus.ENABLED:
            raise PlatformMfaVerificationFailedError(_GENERIC_MFA_FAILURE)
        secret = self._totp.generate_secret()
        encrypted = self._encryptor.encrypt(secret)
        enrollment = PlatformTotpEnrollment.begin_pending(user_id=uid, encrypted_secret=encrypted)
        await self._enrollments.save(enrollment)
        uri = self._totp.provisioning_uri(
            secret=secret,
            account_name=account_email,
            issuer=self._issuer,
        )
        return BeginTotpEnrollmentSecretBundle(provisioning_uri=uri, plaintext_secret=secret)


class ConfirmPlatformTotpEnrollmentUseCase:
    def __init__(
        self,
        *,
        enrollments: PlatformTotpEnrollmentRepository,
        encryptor: MfaSecretEncryptor,
        totp: TotpService,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._enrollments = enrollments
        self._encryptor = encryptor
        self._totp = totp
        self._clock = clock or utc_now_ms

    async def execute(self, *, user_id: str, totp_code: str) -> None:
        uid = require_user_uuid_v4(user_id)
        enrollment = await self._enrollments.get_by_user_id(uid)
        if enrollment is None or enrollment.status is not TotpEnrollmentStatus.PENDING:
            raise PlatformMfaVerificationFailedError(_GENERIC_MFA_FAILURE)
        secret = self._encryptor.decrypt(enrollment.encrypted_secret)
        now = self._clock()
        for_time = int(now.astimezone(UTC).timestamp())
        ok, _counter = self._totp.verify(secret=secret, code=totp_code, for_time=for_time)
        if not ok:
            raise PlatformMfaVerificationFailedError(_GENERIC_MFA_FAILURE)
        await self._enrollments.save(enrollment.activate(now=now))


class StartPlatformMfaChallengeUseCase:
    def __init__(
        self,
        *,
        enrollments: PlatformTotpEnrollmentRepository,
        challenges: PlatformMfaChallengeRepository,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._enrollments = enrollments
        self._challenges = challenges
        self._clock = clock or utc_now_ms

    async def execute(self, *, principal: VerifiedPrincipal) -> PlatformMfaChallenge:
        now = self._clock()
        _assert_fresh_password_proof(principal, now)
        uid = require_user_uuid_v4(principal.user_id)
        enrollment = await self._enrollments.get_by_user_id(uid)
        if enrollment is None or enrollment.status is not TotpEnrollmentStatus.ENABLED:
            raise PlatformMfaNotConfiguredError("MFA TOTP no configurado para la identidad.")
        existing = await self._challenges.find_open_for_user(uid, now=now)
        if existing is not None:
            return existing
        challenge = PlatformMfaChallenge.create(user_id=uid, now=now)
        await self._challenges.insert(challenge)
        return challenge


class VerifyPlatformMfaChallengeUseCase:
    def __init__(
        self,
        *,
        enrollments: PlatformTotpEnrollmentRepository,
        challenges: PlatformMfaChallengeRepository,
        steps: PlatformMfaStepConsumptionRepository,
        authorizations: PlatformMfaSessionAuthorizationRepository,
        encryptor: MfaSecretEncryptor,
        totp: TotpService,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._enrollments = enrollments
        self._challenges = challenges
        self._steps = steps
        self._authorizations = authorizations
        self._encryptor = encryptor
        self._totp = totp
        self._clock = clock or utc_now_ms

    async def execute(
        self,
        *,
        principal: VerifiedPrincipal,
        challenge_id: str,
        totp_code: str,
    ) -> PlatformMfaAuthorizationGrant:
        cid = require_user_uuid_v4(challenge_id, "challenge_id")
        now = self._clock()
        _assert_fresh_password_proof(principal, now)
        uid = require_user_uuid_v4(principal.user_id)
        credential_version = principal.credential_version
        challenge = await self._challenges.get_by_id(cid)
        if challenge is None or challenge.user_id != uid:
            raise PlatformMfaVerificationFailedError(_GENERIC_MFA_FAILURE)

        if not await self._challenges.reserve_verification_attempt(cid, user_id=uid, now=now):
            raise PlatformMfaVerificationFailedError(_GENERIC_MFA_FAILURE)

        enrollment = await self._enrollments.get_by_user_id(uid)
        if enrollment is None or enrollment.status is not TotpEnrollmentStatus.ENABLED:
            raise PlatformMfaNotConfiguredError("MFA TOTP no configurado.")

        secret = self._encryptor.decrypt(enrollment.encrypted_secret)
        for_time = int(now.astimezone(UTC).timestamp())
        ok, counter = self._totp.verify(secret=secret, code=totp_code, for_time=for_time)
        if not ok:
            raise PlatformMfaVerificationFailedError(_GENERIC_MFA_FAILURE)

        if not await self._steps.try_register_step(
            user_id=uid,
            time_counter=counter,
            expires_at=now + _STEP_TTL,
        ):
            raise PlatformMfaVerificationFailedError(_GENERIC_MFA_FAILURE)

        if await self._challenges.consume_if_valid(cid, user_id=uid, now=now) is None:
            raise PlatformMfaVerificationFailedError(_GENERIC_MFA_FAILURE)

        authorization = PlatformMfaSessionAuthorization.issue(
            user_id=uid,
            challenge_id=cid,
            credential_version=credential_version,
            now=now,
        )
        await self._authorizations.insert(authorization)
        return PlatformMfaAuthorizationGrant(
            authorization_id=authorization.authorization_id,
            user_id=uid,
        )
