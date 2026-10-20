"""Errores application del módulo access (sin HTTP)."""


class AccessApplicationError(Exception):
    """Violación de regla de autorización multi-tenant."""


class TenantNotSelectedError(AccessApplicationError):
    """Sesión autenticada sin tenant gym seleccionado (H2-C.3)."""


class MembershipNotFoundError(AccessApplicationError):
    """No existe membresía para el par usuario–tenant."""


class MembershipAccessDeniedError(AccessApplicationError):
    """Membresía no operativa o no coincide con identidad confiable."""


class MembershipStorageError(AccessApplicationError):
    """Fallo de persistencia de membresía."""


class MembershipDuplicateError(AccessApplicationError):
    """Ya existe membresía canónica para usuario–tenant."""


class MembershipUpdateConflictError(AccessApplicationError):
    """Conflicto de concurrencia optimista al actualizar membresía."""


class BranchScopeValidationError(AccessApplicationError):
    """Sucursal fuera del tenant o inexistente para el alcance de membresía."""
