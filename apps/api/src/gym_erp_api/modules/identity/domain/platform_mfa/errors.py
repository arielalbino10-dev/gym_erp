"""Errores de dominio MFA platform."""


class PlatformMfaDomainError(Exception):
    pass


class InvalidTotpEnrollmentError(PlatformMfaDomainError):
    pass


class InvalidMfaChallengeError(PlatformMfaDomainError):
    pass


class InvalidMfaAuthorizationError(PlatformMfaDomainError):
    pass
