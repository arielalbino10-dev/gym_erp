"""Errores de aplicación — administración platform."""


class PlatformAdminError(Exception):
    """Base administración platform."""


class PlatformPermissionDeniedError(PlatformAdminError):
    """Operador autenticado sin permiso para la operación."""


class PlatformRoleAssignmentNotFoundError(PlatformAdminError):
    """Sin asignación RBAC para el operador."""


class PlatformRoleManagementForbiddenError(PlatformAdminError):
    """Cambio RBAC no permitido (escalamiento o actor no autorizado)."""


class LastRootAdminProtectionError(PlatformAdminError):
    """Revocación bloqueada: debe permanecer al menos un root_admin."""
