"""Mappers MFA platform ↔ MongoDB."""

from __future__ import annotations

from typing import Any

from bson.binary import Binary

from gym_erp_api.modules.identity.domain.persistence_utils import parse_utc_datetime
from gym_erp_api.modules.identity.domain.platform_mfa.encrypted_secret import EncryptedMfaSecret
from gym_erp_api.modules.identity.domain.platform_mfa.enums import TotpEnrollmentStatus
from gym_erp_api.modules.identity.domain.platform_mfa.platform_mfa_challenge import (
    PlatformMfaChallenge,
)
from gym_erp_api.modules.identity.domain.platform_mfa.platform_mfa_session_authorization import (
    PlatformMfaSessionAuthorization,
)
from gym_erp_api.modules.identity.domain.platform_mfa.platform_totp_enrollment import (
    PlatformTotpEnrollment,
)

PLATFORM_MFA_TOTP_COLLECTION = "platform_mfa_totp_enrollments"
PLATFORM_MFA_CHALLENGES_COLLECTION = "platform_mfa_challenges"
PLATFORM_MFA_STEPS_COLLECTION = "platform_mfa_totp_steps"
PLATFORM_MFA_AUTHORIZATIONS_COLLECTION = "platform_mfa_session_authorizations"


def enrollment_to_document(enrollment: PlatformTotpEnrollment) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "_id": enrollment.user_id,
        "user_id": enrollment.user_id,
        "status": enrollment.status.value,
        "key_version": enrollment.encrypted_secret.key_version,
        "encrypted_secret": Binary(enrollment.encrypted_secret.ciphertext),
        "created_at": enrollment.created_at,
        "updated_at": enrollment.updated_at,
    }
    if enrollment.enabled_at is not None:
        doc["enabled_at"] = enrollment.enabled_at
    return doc


def enrollment_from_document(raw: dict[str, Any]) -> PlatformTotpEnrollment:
    enc_raw = raw["encrypted_secret"]
    ciphertext = bytes(enc_raw) if isinstance(enc_raw, Binary) else enc_raw
    enabled = raw.get("enabled_at")
    return PlatformTotpEnrollment(
        user_id=str(raw["user_id"]),
        status=TotpEnrollmentStatus(str(raw["status"])),
        encrypted_secret=EncryptedMfaSecret(
            key_version=int(raw["key_version"]),
            ciphertext=ciphertext,
        ),
        created_at=parse_utc_datetime(raw["created_at"], "created_at"),
        updated_at=parse_utc_datetime(raw["updated_at"], "updated_at"),
        enabled_at=parse_utc_datetime(enabled, "enabled_at") if enabled else None,
    )


def challenge_to_document(challenge: PlatformMfaChallenge) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "_id": challenge.challenge_id,
        "challenge_id": challenge.challenge_id,
        "user_id": challenge.user_id,
        "created_at": challenge.created_at,
        "expires_at": challenge.expires_at,
        "failed_attempts": challenge.failed_attempts,
        "max_attempts": challenge.max_attempts,
        "updated_at": challenge.created_at,
    }
    if challenge.consumed_at is not None:
        doc["consumed_at"] = challenge.consumed_at
    return doc


def challenge_from_document(raw: dict[str, Any]) -> PlatformMfaChallenge:
    consumed = raw.get("consumed_at")
    return PlatformMfaChallenge(
        challenge_id=str(raw["challenge_id"]),
        user_id=str(raw["user_id"]),
        created_at=parse_utc_datetime(raw["created_at"], "created_at"),
        expires_at=parse_utc_datetime(raw["expires_at"], "expires_at"),
        failed_attempts=int(raw["failed_attempts"]),
        max_attempts=int(raw["max_attempts"]),
        consumed_at=parse_utc_datetime(consumed, "consumed_at") if consumed else None,
    )


def authorization_to_document(auth: PlatformMfaSessionAuthorization) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "_id": auth.authorization_id,
        "authorization_id": auth.authorization_id,
        "user_id": auth.user_id,
        "challenge_id": auth.challenge_id,
        "credential_version": auth.credential_version,
        "issued_at": auth.issued_at,
        "expires_at": auth.expires_at,
    }
    if auth.consumed_at is not None:
        doc["consumed_at"] = auth.consumed_at
    return doc


def authorization_from_document(raw: dict[str, Any]) -> PlatformMfaSessionAuthorization:
    consumed = raw.get("consumed_at")
    return PlatformMfaSessionAuthorization(
        authorization_id=str(raw["authorization_id"]),
        user_id=str(raw["user_id"]),
        challenge_id=str(raw["challenge_id"]),
        credential_version=int(raw["credential_version"]),
        issued_at=parse_utc_datetime(raw["issued_at"], "issued_at"),
        expires_at=parse_utc_datetime(raw["expires_at"], "expires_at"),
        consumed_at=parse_utc_datetime(consumed, "consumed_at") if consumed else None,
    )
