"""Continuidad server-side login platform (H2-B.6, sin HTTP)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from gym_erp_api.modules.identity.application.dto.auth_results import (
    CreatedSession,
    VerifiedPrincipal,
)
from gym_erp_api.modules.identity.application.errors import (
    PlatformAuthContinuationError,
    PlatformMfaVerificationFailedError,
)
from gym_erp_api.modules.identity.application.ports.platform_auth_continuation_repository import (
    PlatformAuthContinuationRepository,
)
from gym_erp_api.modules.identity.application.use_cases.create_platform_session import (
    CreatePlatformSessionUseCase,
)
from gym_erp_api.modules.identity.application.use_cases.platform_mfa_totp import (
    StartPlatformMfaChallengeUseCase,
    VerifyPlatformMfaChallengeUseCase,
)
from gym_erp_api.modules.identity.domain.platform_auth.platform_auth_continuation import (
    PlatformAuthContinuation,
)
from gym_erp_api.modules.identity.domain.time_utils import utc_now_ms
from gym_erp_api.modules.identity.infrastructure.crypto.session_token_hash import (
    generate_opaque_session_token,
    hash_session_token,
)

_GENERIC_CONTINUATION_FAILURE = "Autenticación platform inválida o expirada."


@dataclass(frozen=True, slots=True)
class PlatformAuthContinuationTokenBundle:
    """Token opaco — entregar una sola vez al cliente HTTP futuro; no loguear."""

    opaque_token: str = field(repr=False)
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class PlatformAuthContinuationContext:
    """Contexto interno reconstruido desde persistencia (no desde JSON del cliente)."""

    continuation_id: str
    user_id: str
    credential_version: int
    password_verified_at: datetime
    authorization_id: str | None

    def to_verified_principal(self) -> VerifiedPrincipal:
        return VerifiedPrincipal(
            user_id=self.user_id,
            credential_version=self.credential_version,
            email_normalized="",
            verified_at=self.password_verified_at,
        )


class CreatePlatformAuthContinuationUseCase:
    def __init__(
        self,
        *,
        continuations: PlatformAuthContinuationRepository,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._continuations = continuations
        self._clock = clock or utc_now_ms

    async def execute(self, *, principal: VerifiedPrincipal) -> PlatformAuthContinuationTokenBundle:
        now = self._clock()
        existing = await self._continuations.find_open_for_user(principal.user_id, now=now)
        if existing is not None:
            raise PlatformAuthContinuationError(_GENERIC_CONTINUATION_FAILURE)
        opaque = generate_opaque_session_token()
        token_hash = hash_session_token(opaque)
        cont = PlatformAuthContinuation.begin(
            token_hash=token_hash,
            user_id=principal.user_id,
            credential_version=principal.credential_version,
            password_verified_at=principal.verified_at,
            now=now,
        )
        await self._continuations.insert(cont)
        return PlatformAuthContinuationTokenBundle(
            opaque_token=opaque,
            expires_at=cont.expires_at,
        )


class ResolvePlatformAuthContinuationUseCase:
    def __init__(
        self,
        *,
        continuations: PlatformAuthContinuationRepository,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._continuations = continuations
        self._clock = clock or utc_now_ms

    async def execute(self, *, opaque_token: str) -> PlatformAuthContinuationContext:
        now = self._clock()
        token_hash = hash_session_token(opaque_token)
        cont = await self._continuations.get_by_token_hash(token_hash)
        if cont is None:
            raise PlatformAuthContinuationError(_GENERIC_CONTINUATION_FAILURE)
        try:
            cont.assert_active_at(now)
        except Exception as exc:
            raise PlatformAuthContinuationError(_GENERIC_CONTINUATION_FAILURE) from exc
        return PlatformAuthContinuationContext(
            continuation_id=cont.continuation_id,
            user_id=cont.user_id,
            credential_version=cont.credential_version,
            password_verified_at=cont.password_verified_at,
            authorization_id=cont.authorization_id,
        )


class CompletePlatformAuthContinuationMfaUseCase:
    """Desafío + TOTP + autorización, anclados a la continuación server-side."""

    def __init__(
        self,
        *,
        continuations: PlatformAuthContinuationRepository,
        start_mfa: StartPlatformMfaChallengeUseCase,
        verify_mfa: VerifyPlatformMfaChallengeUseCase,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._continuations = continuations
        self._start_mfa = start_mfa
        self._verify_mfa = verify_mfa
        self._clock = clock or utc_now_ms

    async def execute(
        self,
        *,
        opaque_token: str,
        totp_code: str,
    ) -> PlatformAuthContinuationContext:
        now = self._clock()
        token_hash = hash_session_token(opaque_token)
        cont = await self._continuations.get_by_token_hash(token_hash)
        if cont is None:
            raise PlatformAuthContinuationError(_GENERIC_CONTINUATION_FAILURE)
        try:
            cont.assert_active_at(now)
        except Exception as exc:
            raise PlatformAuthContinuationError(_GENERIC_CONTINUATION_FAILURE) from exc

        principal = VerifiedPrincipal(
            user_id=cont.user_id,
            credential_version=cont.credential_version,
            email_normalized="",
            verified_at=cont.password_verified_at,
        )

        if cont.authorization_id is not None:
            return PlatformAuthContinuationContext(
                continuation_id=cont.continuation_id,
                user_id=cont.user_id,
                credential_version=cont.credential_version,
                password_verified_at=cont.password_verified_at,
                authorization_id=cont.authorization_id,
            )

        challenge_id = cont.challenge_id
        if challenge_id is None:
            challenge = await self._start_mfa.execute(principal=principal)
            bound = await self._continuations.bind_challenge(
                cont.continuation_id,
                challenge_id=challenge.challenge_id,
                now=now,
            )
            if bound is None:
                raise PlatformMfaVerificationFailedError(_GENERIC_CONTINUATION_FAILURE)
            challenge_id = challenge.challenge_id

        grant = await self._verify_mfa.execute(
            principal=principal,
            challenge_id=challenge_id,
            totp_code=totp_code,
        )
        authorized = await self._continuations.bind_authorization(
            cont.continuation_id,
            authorization_id=grant.authorization_id,
            now=now,
        )
        if authorized is None:
            raise PlatformMfaVerificationFailedError(_GENERIC_CONTINUATION_FAILURE)
        return PlatformAuthContinuationContext(
            continuation_id=authorized.continuation_id,
            user_id=authorized.user_id,
            credential_version=authorized.credential_version,
            password_verified_at=authorized.password_verified_at,
            authorization_id=authorized.authorization_id,
        )


class CreatePlatformSessionFromContinuationUseCase:
    def __init__(
        self,
        *,
        continuations: PlatformAuthContinuationRepository,
        create_session: CreatePlatformSessionUseCase,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._continuations = continuations
        self._create_session = create_session
        self._clock = clock or utc_now_ms

    async def execute(self, *, opaque_token: str) -> CreatedSession:
        now = self._clock()
        token_hash = hash_session_token(opaque_token)
        cont = await self._continuations.get_by_token_hash(token_hash)
        if cont is None or cont.authorization_id is None:
            raise PlatformAuthContinuationError(_GENERIC_CONTINUATION_FAILURE)
        consumed = await self._continuations.consume_if_authorized(
            cont.continuation_id,
            user_id=cont.user_id,
            credential_version=cont.credential_version,
            now=now,
        )
        if consumed is None:
            raise PlatformAuthContinuationError(_GENERIC_CONTINUATION_FAILURE)
        principal = VerifiedPrincipal(
            user_id=consumed.user_id,
            credential_version=consumed.credential_version,
            email_normalized="",
            verified_at=consumed.password_verified_at,
        )
        return await self._create_session.execute(
            principal=principal,
            authorization_id=consumed.authorization_id,
        )
