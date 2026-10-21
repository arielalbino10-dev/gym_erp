#!/usr/bin/env -S uv run python
"""Bootstrap LOCAL opt-in: primer root_admin platform (H3-A.3 / incremento A).

Requisitos:
  APP_ENV=development|test
  GYM_ERP_BOOTSTRAP_PLATFORM_ROOT=1
  GYM_ERP_DEV_BOOTSTRAP_PLATFORM_EMAIL
  GYM_ERP_DEV_BOOTSTRAP_PASSWORD (mín. 12; solo si aún no hay credencial)

Promoción de identidad existente (no root):
  GYM_ERP_BOOTSTRAP_PLATFORM_CONFIRM_EXISTING=1

No ejecutar en production. No API pública. No imprime contraseñas ni tokens.
No sustituye enrolamiento MFA: el operador debe completar MFA en login platform.

Inspección: GYM_ERP_BOOTSTRAP_INSPECT=1 (mismo opt-in).
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import Mapping
from datetime import UTC, datetime

from gym_erp_api.core.config import Settings
from gym_erp_api.infrastructure.mongo.database import create_mongo_client
from gym_erp_api.infrastructure.mongo.mongo_databases import MongoDatabases
from gym_erp_api.modules.identity.domain.user_credential import UserCredential
from gym_erp_api.modules.identity.domain.user_identity import UserIdentity
from gym_erp_api.modules.identity.infrastructure.crypto.argon2_password_hasher import (
    Argon2PasswordHasher,
)
from gym_erp_api.modules.identity.infrastructure.mongo.mongo_credential_repository import (
    MongoCredentialRepository,
)
from gym_erp_api.modules.identity.infrastructure.mongo.mongo_identity_repository import (
    MongoIdentityRepository,
)
from gym_erp_api.modules.identity.infrastructure.mongo.mongo_platform_operator_eligibility_repository import (  # noqa: E501
    PLATFORM_OPERATOR_ELIGIBILITIES_COLLECTION,
    MongoPlatformOperatorEligibilityRepository,
)
from gym_erp_api.modules.platform_admin.domain.platform_role import PlatformRole
from gym_erp_api.modules.platform_admin.domain.platform_role_assignment import (
    PlatformRoleAssignment,
)
from gym_erp_api.modules.platform_admin.infrastructure.mongo.mongo_platform_role_assignment_repository import (  # noqa: E501
    MongoPlatformRoleAssignmentRepository,
)
from gym_erp_api.modules.platform_admin.infrastructure.mongo.platform_role_assignment_mapper import (  # noqa: E501
    PLATFORM_ROLE_ASSIGNMENTS_COLLECTION,
)


class BootstrapError(RuntimeError):
    pass


def require_bootstrap_opt_in(env: Mapping[str, str] | None = None) -> None:
    source = env if env is not None else os.environ
    if source.get("GYM_ERP_BOOTSTRAP_PLATFORM_ROOT", "").strip() != "1":
        raise BootstrapError("Defina GYM_ERP_BOOTSTRAP_PLATFORM_ROOT=1 para continuar.")


def validate_app_env_for_bootstrap(app_env: str) -> None:
    env = app_env.strip().lower()
    if env not in {"development", "test"}:
        raise BootstrapError(f"APP_ENV={env!r} no permitido para bootstrap platform.")


def collect_bootstrap_inputs(
    env: Mapping[str, str],
    *,
    inspect_only: bool,
) -> tuple[str, str]:
    email = env.get("GYM_ERP_DEV_BOOTSTRAP_PLATFORM_EMAIL", "").strip().lower()
    if not email:
        raise BootstrapError("Defina GYM_ERP_DEV_BOOTSTRAP_PLATFORM_EMAIL.")
    password = env.get("GYM_ERP_DEV_BOOTSTRAP_PASSWORD", "").strip()
    if not inspect_only and len(password) < 12:
        raise BootstrapError("Defina GYM_ERP_DEV_BOOTSTRAP_PASSWORD (mín. 12 caracteres).")
    return email, password


def require_promotion_consent_for_existing_identity(
    *,
    identity_preexisted: bool,
    already_root: bool,
    env: Mapping[str, str] | None = None,
) -> None:
    if not identity_preexisted or already_root:
        return
    source = env if env is not None else os.environ
    if source.get("GYM_ERP_BOOTSTRAP_PLATFORM_CONFIRM_EXISTING", "").strip() != "1":
        raise BootstrapError(
            "Identidad existente sin root_admin: defina "
            "GYM_ERP_BOOTSTRAP_PLATFORM_CONFIRM_EXISTING=1 para promover "
            "(evita promoción silenciosa).",
        )


async def _run() -> int:
    require_bootstrap_opt_in()
    settings = Settings(_env_file=None)
    validate_app_env_for_bootstrap(settings.app_env)
    inspect_only = os.environ.get("GYM_ERP_BOOTSTRAP_INSPECT", "").strip() == "1"
    email, password = collect_bootstrap_inputs(os.environ, inspect_only=inspect_only)

    client = create_mongo_client(settings)
    if client is None:
        raise BootstrapError("MongoDB no configurado.")
    databases = MongoDatabases(client, settings)
    platform = databases.platform
    identities = MongoIdentityRepository(platform["user_identities"])
    credentials = MongoCredentialRepository(platform["user_credentials"])
    eligibility = MongoPlatformOperatorEligibilityRepository(
        platform[PLATFORM_OPERATOR_ELIGIBILITIES_COLLECTION],
    )
    assignments = MongoPlatformRoleAssignmentRepository(
        platform[PLATFORM_ROLE_ASSIGNMENTS_COLLECTION],
    )
    hasher = Argon2PasswordHasher()
    now = datetime.now(UTC)

    existing = await identities.get_by_email_normalized(email_normalized=email)
    identity_preexisted = existing is not None
    if existing is not None:
        user_id = existing.user_id
        print(f"Identidad existente para operador platform: user_id={user_id}")
    else:
        if inspect_only:
            print("Modo inspect: identidad platform no existe; no se creará.")
            await client.close()
            return 0
        identity = UserIdentity.create(email=email, now=now).mark_email_verified(now=now)
        user_id = identity.user_id
        await identities.save(identity)
        await credentials.insert(
            UserCredential.create(
                user_id=user_id,
                password_hash=hasher.hash(password),
                credential_version=0,
                now=now,
            ),
        )
        print(f"Identidad platform creada: user_id={user_id}")

    if inspect_only:
        print("Modo inspect: sin escrituras de elegibilidad/RBAC.")
        await client.close()
        return 0

    prior = await assignments.get_by_user_id(user_id=user_id)
    already_root = prior is not None and PlatformRole.ROOT_ADMIN in prior.roles
    require_promotion_consent_for_existing_identity(
        identity_preexisted=identity_preexisted,
        already_root=already_root,
    )

    await eligibility.grant_eligibility(user_id=user_id, granted_at=now)
    await assignments.upsert(
        assignment=PlatformRoleAssignment(
            user_id=user_id,
            roles=frozenset({PlatformRole.ROOT_ADMIN}),
            updated_at=now,
        ),
    )
    print("Elegibilidad platform y rol root_admin asignados.")
    print("Complete enrolamiento MFA mediante login en /api/v1/platform/auth.")
    await client.close()
    return 0


def main() -> None:
    try:
        raise SystemExit(asyncio.run(_run()))
    except BootstrapError as exc:
        print(f"Bootstrap platform: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
