"""Excepciones del núcleo multi-tenant (errores de programación o violación de scope)."""


class MultiTenantCoreError(Exception):
    """Base para errores del núcleo multi-tenant."""


class InvalidTenantContextError(MultiTenantCoreError):
    """TenantContext o identificadores inválidos."""


class TenantScopeError(MultiTenantCoreError):
    """Intento de eludir o sobrescribir el alcance del tenant o campos protegidos."""


class ForbiddenMongoOperatorError(TenantScopeError):
    """Operador o etapa MongoDB no permitida en esta capa."""
