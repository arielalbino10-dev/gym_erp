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


class InvalidIdentityPersistenceError(IdentityDomainError):
    """Documento MongoDB inválido al rehidratar identidad."""


class IdentityDuplicateEmailError(IdentityDomainError):
    """email_normalized ya registrado."""


class IdentityDuplicateUserError(IdentityDomainError):
    """user_id ya registrado."""


class IdentityNotFoundError(IdentityDomainError):
    """Identidad inexistente."""


class IdentityUpdateConflictError(IdentityDomainError):
    """Conflicto de concurrencia optimista en identidad."""


class IdentityStorageError(IdentityDomainError):
    """Fallo de persistencia sin detalles sensibles."""


class InvalidCredentialFieldError(IdentityDomainError):
    """Hash o campo de credencial inválido."""


class CredentialNotFoundError(IdentityDomainError):
    """Credencial inexistente para user_id."""


class CredentialUpdateConflictError(IdentityDomainError):
    """Conflicto de concurrencia en credencial."""


class CredentialDuplicateUserError(IdentityDomainError):
    """Ya existe credencial para user_id."""


class InvalidSessionFieldError(IdentityDomainError):
    """Campo de sesión inválido."""


class SessionNotFoundError(IdentityDomainError):
    """Sesión inexistente."""


class SessionRevokedError(IdentityDomainError):
    """Sesión revocada."""


class SessionExpiredError(IdentityDomainError):
    """Sesión expirada (absoluta o inactividad)."""


class SessionUpdateConflictError(IdentityDomainError):
    """Conflicto de concurrencia al actualizar actividad de sesión."""
