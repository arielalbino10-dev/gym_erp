from enum import StrEnum


class PlatformAuthContinuationStatus(StrEnum):
    PASSWORD_VERIFIED = "password_verified"
    MFA_CHALLENGE_BOUND = "mfa_challenge_bound"
    MFA_AUTHORIZED = "mfa_authorized"
