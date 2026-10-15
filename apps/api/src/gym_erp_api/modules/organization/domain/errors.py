"""Errores de dominio del módulo organization."""


class OrganizationDomainError(Exception):
    """Violación de regla de negocio en organization."""


class InvalidOrganizationIdentifierError(OrganizationDomainError):
    """UUID de dominio inválido o no canónico."""


class InvalidOrganizationFieldError(OrganizationDomainError):
    """Campo de texto, zona horaria u otro valor inválido."""


class InvalidOrganizationStateTransitionError(OrganizationDomainError):
    """Transición de status no permitida."""


class OrganizationImmutabilityError(OrganizationDomainError):
    """Intento de alterar identificadores o relaciones inmutables."""


class InvalidOrganizationPersistenceError(OrganizationDomainError):
    """Documento persistido incompleto, corrupto o inconsistente."""


class OrganizationEntityNotFoundError(OrganizationDomainError):
    """Entidad no encontrada en persistencia."""
