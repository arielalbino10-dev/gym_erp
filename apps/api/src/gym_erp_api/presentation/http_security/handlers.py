"""Mapeo de excepciones a respuestas HTTP genéricas."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from gym_erp_api.modules.access.application.errors import AccessApplicationError
from gym_erp_api.modules.identity.application.errors import (
    AuthenticationFailedError,
    IdentityApplicationError,
    PlatformAuthContinuationError,
    PlatformMfaRequiredError,
    PlatformMfaVerificationFailedError,
    SessionResolutionFailedError,
    SessionRevocationFailedError,
)
from gym_erp_api.presentation.http_security.errors import (
    AccessInfrastructureUnavailableError,
    CsrfContextRequiredError,
    CsrfValidationError,
    GymAccessDeniedError,
    GymNotAuthenticatedError,
    GymTenantNotSelectedError,
    HttpSecurityError,
    HttpsRequiredError,
    IdentityInfrastructureUnavailableError,
    InvalidOriginError,
    RateLimitBackendError,
    RateLimitExceededError,
)

_logger = logging.getLogger(__name__)

_GENERIC_AUTH = {"detail": "Credenciales inválidas o solicitud no autorizada."}
_GENERIC_FORBIDDEN = {"detail": "Solicitud no permitida."}
_GENERIC_UNAVAILABLE = {"detail": "Servicio temporalmente no disponible."}


def register_http_security_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RateLimitExceededError)
    async def _rate_limit(_: Request, exc: RateLimitExceededError) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={"detail": exc.public_message},
            headers={"Retry-After": str(exc.retry_after_seconds)},
        )

    @app.exception_handler(InvalidOriginError)
    @app.exception_handler(CsrfValidationError)
    @app.exception_handler(CsrfContextRequiredError)
    @app.exception_handler(HttpsRequiredError)
    async def _forbidden(_: Request, exc: HttpSecurityError) -> JSONResponse:
        _logger.info("http_security_forbidden", extra={"reason": type(exc).__name__})
        return JSONResponse(status_code=403, content={"detail": exc.public_message})

    @app.exception_handler(GymNotAuthenticatedError)
    async def _gym_unauth(_: Request, exc: HttpSecurityError) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": exc.public_message})

    @app.exception_handler(GymTenantNotSelectedError)
    async def _gym_no_tenant(_: Request, exc: HttpSecurityError) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content={"detail": exc.public_message, "code": "tenant_not_selected"},
        )

    @app.exception_handler(GymAccessDeniedError)
    @app.exception_handler(AccessApplicationError)
    async def _gym_access(_: Request, exc: Exception) -> JSONResponse:
        _logger.info("gym_access_denied", extra={"reason": type(exc).__name__})
        message = getattr(exc, "args", ("Acceso no permitido.",))[0]
        if isinstance(message, str) and message:
            detail = message
        else:
            detail = "Acceso no permitido."
        return JSONResponse(status_code=403, content={"detail": detail})

    @app.exception_handler(RateLimitBackendError)
    @app.exception_handler(IdentityInfrastructureUnavailableError)
    @app.exception_handler(AccessInfrastructureUnavailableError)
    async def _unavailable(_: Request, exc: HttpSecurityError) -> JSONResponse:
        _logger.warning("http_security_unavailable", extra={"reason": type(exc).__name__})
        return JSONResponse(status_code=503, content={"detail": exc.public_message})

    @app.exception_handler(AuthenticationFailedError)
    @app.exception_handler(PlatformMfaRequiredError)
    @app.exception_handler(PlatformMfaVerificationFailedError)
    @app.exception_handler(PlatformAuthContinuationError)
    @app.exception_handler(SessionResolutionFailedError)
    async def _auth_failed(_: Request, exc: IdentityApplicationError) -> JSONResponse:
        _logger.info("identity_auth_failed", extra={"reason": type(exc).__name__})
        return JSONResponse(status_code=401, content=_GENERIC_AUTH)

    @app.exception_handler(SessionRevocationFailedError)
    async def _revocation(_: Request, exc: IdentityApplicationError) -> JSONResponse:
        _logger.info("identity_revocation_failed", extra={"reason": type(exc).__name__})
        return JSONResponse(status_code=400, content=_GENERIC_FORBIDDEN)
