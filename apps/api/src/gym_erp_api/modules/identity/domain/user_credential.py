"""Credencial de contraseña (hash Argon2id) vinculada 1:1 a user_id."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from gym_erp_api.modules.identity.domain.errors import InvalidCredentialFieldError
from gym_erp_api.modules.identity.domain.time_utils import truncate_utc_to_milliseconds, utc_now_ms
from gym_erp_api.modules.identity.domain.validators import require_user_uuid_v4

_ARGON2ID_PREFIX = "$argon2id$"


@dataclass(frozen=True, slots=True)
class UserCredential:
    user_id: str
    password_hash: str = field(repr=False)
    credential_version: int
    updated_at: datetime

    def __post_init__(self) -> None:
        require_user_uuid_v4(self.user_id)
        if not isinstance(self.password_hash, str) or not self.password_hash.startswith(
            _ARGON2ID_PREFIX
        ):
            raise InvalidCredentialFieldError("password_hash debe ser Argon2id (PHC).")
        if not isinstance(self.credential_version, int) or self.credential_version < 0:
            raise InvalidCredentialFieldError("credential_version inválido.")

    @classmethod
    def create(
        cls,
        *,
        user_id: str,
        password_hash: str,
        credential_version: int,
        now: datetime | None = None,
    ) -> UserCredential:
        moment = truncate_utc_to_milliseconds(now) if now is not None else utc_now_ms()
        return cls(
            user_id=require_user_uuid_v4(user_id),
            password_hash=password_hash,
            credential_version=credential_version,
            updated_at=moment,
        )
