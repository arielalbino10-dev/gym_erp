"""Errores de dominio del módulo access."""


class AccessDomainError(Exception):
    """Violación de invariante de membresía o rol gym."""


class InvalidMembershipFieldError(AccessDomainError):
    """Campo de membresía inválido."""


class InvalidMembershipStateTransitionError(AccessDomainError):
    """Transición de estado no permitida."""


class InvalidGymRoleAssignmentError(AccessDomainError):
    """Combinación rol / alcance de sucursal inválida."""
