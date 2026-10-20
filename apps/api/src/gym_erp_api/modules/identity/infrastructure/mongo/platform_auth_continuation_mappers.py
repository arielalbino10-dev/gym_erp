from __future__ import annotations

from typing import Any

from gym_erp_api.modules.identity.domain.persistence_utils import parse_utc_datetime
from gym_erp_api.modules.identity.domain.platform_auth.enums import PlatformAuthContinuationStatus
from gym_erp_api.modules.identity.domain.platform_auth.platform_auth_continuation import (
    PlatformAuthContinuation,
)

PLATFORM_AUTH_CONTINUATIONS_COLLECTION = "platform_auth_continuations"


def continuation_to_document(cont: PlatformAuthContinuation) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "_id": cont.continuation_id,
        "continuation_id": cont.continuation_id,
        "token_hash": cont.token_hash,
        "user_id": cont.user_id,
        "credential_version": cont.credential_version,
        "password_verified_at": cont.password_verified_at,
        "status": cont.status.value,
        "expires_at": cont.expires_at,
        "created_at": cont.created_at,
    }
    if cont.challenge_id is not None:
        doc["challenge_id"] = cont.challenge_id
    if cont.authorization_id is not None:
        doc["authorization_id"] = cont.authorization_id
    if cont.consumed_at is not None:
        doc["consumed_at"] = cont.consumed_at
    return doc


def continuation_from_document(raw: dict[str, Any]) -> PlatformAuthContinuation:
    consumed = raw.get("consumed_at")
    return PlatformAuthContinuation(
        continuation_id=str(raw["continuation_id"]),
        token_hash=str(raw["token_hash"]),
        user_id=str(raw["user_id"]),
        credential_version=int(raw["credential_version"]),
        password_verified_at=parse_utc_datetime(
            raw["password_verified_at"],
            "password_verified_at",
        ),
        status=PlatformAuthContinuationStatus(str(raw["status"])),
        expires_at=parse_utc_datetime(raw["expires_at"], "expires_at"),
        created_at=parse_utc_datetime(raw["created_at"], "created_at"),
        challenge_id=str(raw["challenge_id"]) if raw.get("challenge_id") else None,
        authorization_id=str(raw["authorization_id"]) if raw.get("authorization_id") else None,
        consumed_at=parse_utc_datetime(consumed, "consumed_at") if consumed else None,
    )
