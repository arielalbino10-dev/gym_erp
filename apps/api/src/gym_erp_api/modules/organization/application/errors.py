"""Errores de la capa application (organization). No sustituyen excepciones HTTP."""


class OrganizationApplicationError(Exception):
    """Violación de regla de aplicación en organization."""


class TenantNotFoundApplicationError(OrganizationApplicationError):
    """No existe tenant platform para la operación solicitada."""


class TenantSuspendedApplicationError(OrganizationApplicationError):
    """El tenant está suspendido; operaciones operational bloqueadas."""


class TenantNotActiveApplicationError(OrganizationApplicationError):
    """El tenant aún no está activo (p. ej. provisioning)."""


class TenantAccessDeniedApplicationError(OrganizationApplicationError):
    """El tenant solicitado no coincide con el contexto autorizado."""


class BranchAccessDeniedApplicationError(OrganizationApplicationError):
    """La sucursal está fuera del alcance permitido por el contexto."""


class BranchNotFoundApplicationError(OrganizationApplicationError):
    """Sucursal inexistente o no visible en el tenant/alcance autorizado."""


class BranchDuplicateApplicationError(OrganizationApplicationError):
    """Conflicto de unicidad al crear sucursal."""


class IdempotencyKeyRequiredError(OrganizationApplicationError):
    """Falta idempotency_key o no cumple el formato permitido."""


class IdempotencyPayloadConflictError(OrganizationApplicationError):
    """La misma clave de idempotencia se reutilizó con datos de negocio distintos."""


class IdempotencyInProgressError(OrganizationApplicationError):
    """Otra ejecución reservó la clave y aún no completó (estado pending)."""


class OrganizationCommitUncertainError(OrganizationApplicationError):
    """Commit MongoDB con resultado desconocido; no reintentar con nuevos identificadores."""


class IdempotencyDocumentInvalidError(OrganizationApplicationError):
    """Documento de idempotencia en platform ilegible o inconsistente."""


class IdempotencyReservationMissingError(OrganizationApplicationError):
    """mark_completed sin reserva pending previa en la misma transacción lógica."""


class IdempotencyAlreadyCompletedError(OrganizationApplicationError):
    """La operación idempotente ya estaba en estado completed."""
