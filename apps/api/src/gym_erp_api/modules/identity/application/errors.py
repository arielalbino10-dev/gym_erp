"""Errores de aplicación identity (mensajes genéricos hacia capa HTTP futura)."""


class IdentityApplicationError(Exception):
    """Base de errores de casos de uso identity."""


class AuthenticationFailedError(IdentityApplicationError):
    """Correo/contraseña inválidos o cuenta no utilizable (respuesta uniforme)."""


class PlatformMfaRequiredError(IdentityApplicationError):
    """MFA platform no satisfecho; no se emite sesión platform."""


class PlatformMfaNotConfiguredError(IdentityApplicationError):
    """MFA platform aún no implementado (H2-B.5+)."""


class PlatformSessionEmissionDisabledError(IdentityApplicationError):
    """Emisión platform bloqueada hasta MFA real y composición H2-B.5."""


class SessionResolutionFailedError(IdentityApplicationError):
    """Token de sesión inválido, expirado, revocado o identidad no usable."""


class SessionRevocationFailedError(IdentityApplicationError):
    """No se pudo revocar la sesión solicitada."""
