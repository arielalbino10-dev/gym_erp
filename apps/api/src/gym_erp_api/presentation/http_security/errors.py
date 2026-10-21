"""Errores HTTP de seguridad (mensajes genéricos al cliente)."""

from __future__ import annotations


class HttpSecurityError(Exception):
    """Base; el handler devuelve mensaje genérico."""

    public_message: str = "Solicitud no permitida."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.public_message)


class InvalidOriginError(HttpSecurityError):
    public_message = "Solicitud no permitida."


class CsrfValidationError(HttpSecurityError):
    public_message = "Solicitud no permitida."


class CsrfContextRequiredError(HttpSecurityError):
    public_message = "Solicitud no permitida."


class RateLimitExceededError(HttpSecurityError):
    public_message = "Demasiadas solicitudes."

    def __init__(self, *, retry_after_seconds: int) -> None:
        self.retry_after_seconds = max(1, retry_after_seconds)
        super().__init__(self.public_message)


class RateLimitBackendError(HttpSecurityError):
    public_message = "Servicio temporalmente no disponible."


class AccessInfrastructureUnavailableError(HttpSecurityError):
    public_message = "Servicio temporalmente no disponible."


class GymNotAuthenticatedError(HttpSecurityError):
    public_message = "No autenticado."


class GymAccessDeniedError(HttpSecurityError):
    public_message = "Acceso no permitido."


class GymTenantNotSelectedError(HttpSecurityError):
    public_message = "No hay gimnasio seleccionado."


class IdentityInfrastructureUnavailableError(HttpSecurityError):
    public_message = "Servicio temporalmente no disponible."


class HttpsRequiredError(HttpSecurityError):
    public_message = "Solicitud no permitida."
