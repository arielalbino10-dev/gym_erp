"""Errores de dominio del módulo identity."""


class IdentityDomainError(Exception):
    """Violación de regla de negocio en identity."""


class InvalidIdentityIdentifierError(IdentityDomainError):
    """UUID de user_id inválido o no canónico."""


class InvalidIdentityFieldError(IdentityDomainError):
    """Email u otro campo inválido."""


class InvalidIdentityStateTransitionError(IdentityDomainError):
    """Transición de status no permitida."""


class InvalidIdentityInvariantError(IdentityDomainError):
    """Invariante de identidad incumplida (p. ej. credential_version)."""
