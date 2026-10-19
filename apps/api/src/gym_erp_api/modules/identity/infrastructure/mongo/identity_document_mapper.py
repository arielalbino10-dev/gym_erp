"""Mapper UserIdentity ↔ documento MongoDB (``user_identities``)."""

from __future__ import annotations

from typing import Any

from gym_erp_api.modules.identity.domain.user_identity import UserIdentity

USER_IDENTITIES_COLLECTION = "user_identities"


def identity_to_document(identity: UserIdentity) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "_id": identity.user_id,
        "user_id": identity.user_id,
        "email": identity.email,
        "email_normalized": identity.email_normalized,
        "status": identity.status.value,
        "credential_version": identity.credential_version,
        "created_at": identity.created_at,
        "updated_at": identity.updated_at,
    }
    if identity.email_verified_at is not None:
        doc["email_verified_at"] = identity.email_verified_at
    return doc


def identity_from_document(raw: dict[str, Any]) -> UserIdentity:
    return UserIdentity.from_persistence(raw)
