"""Mapper UserCredential ↔ documento MongoDB (``user_credentials``)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from gym_erp_api.modules.identity.domain.errors import InvalidIdentityPersistenceError
from gym_erp_api.modules.identity.domain.persistence_utils import parse_utc_datetime
from gym_erp_api.modules.identity.domain.user_credential import UserCredential

USER_CREDENTIALS_COLLECTION = "user_credentials"


def credential_to_document(credential: UserCredential) -> dict[str, Any]:
    return {
        "_id": credential.user_id,
        "user_id": credential.user_id,
        "password_hash": credential.password_hash,
        "credential_version": credential.credential_version,
        "updated_at": credential.updated_at,
    }


def credential_from_document(raw: Mapping[str, Any]) -> UserCredential:
    try:
        return UserCredential(
            user_id=str(raw["user_id"]),
            password_hash=str(raw["password_hash"]),
            credential_version=int(raw["credential_version"]),
            updated_at=parse_utc_datetime(raw["updated_at"], "updated_at"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidIdentityPersistenceError("Documento de credencial incompleto.") from exc
