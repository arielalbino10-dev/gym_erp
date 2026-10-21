#!/usr/bin/env -S uv run python
"""Bootstrap LOCAL opt-in: identidad gym + tenant + membresía owner (H3-C.1 / H3-C.1.1).

Requisitos:
  APP_ENV=development|test (manual dev: development)
  GYM_ERP_BOOTSTRAP_GYM=1
  GYM_ERP_DEV_BOOTSTRAP_PASSWORD (mín. 12; solo si aún no hay credencial)
  MONGODB_PLATFORM_DB=gym_platform y MONGODB_OPERATIONAL_DB=gym_operational (development)

Inspección sin escrituras: GYM_ERP_BOOTSTRAP_INSPECT=1 (mismo opt-in).

No ejecutar en production. No imprime secretos ni URI con credenciales.
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from gym_erp_api.core.config import Settings, get_settings
from gym_erp_api.infrastructure.mongo.database import create_mongo_client
from gym_erp_api.infrastructure.mongo.mongo_databases import MongoDatabases
from gym_erp_api.infrastructure.mongo.mongo_unit_of_work import MongoUnitOfWork
from gym_erp_api.infrastructure.mongo.scoped_repository import TenantScopedRepository
from gym_erp_api.modules.access.domain.enums import BranchScopeMode, GymRole
from gym_erp_api.modules.access.domain.tenant_membership import TenantMembership
from gym_erp_api.modules.access.infrastructure.mongo.membership_document_mapper import (
    TENANT_MEMBERSHIPS_COLLECTION,
)
from gym_erp_api.modules.access.infrastructure.mongo.mongo_tenant_membership_repository import (
    MongoTenantMembershipRepository,
)
from gym_erp_api.modules.identity.domain.user_credential import UserCredential
from gym_erp_api.modules.identity.domain.user_identity import UserIdentity
from gym_erp_api.modules.identity.infrastructure.crypto.argon2_password_hasher import (
    Argon2PasswordHasher,
)
from gym_erp_api.modules.identity.infrastructure.mongo.credential_document_mapper import (
    USER_CREDENTIALS_COLLECTION,
)
from gym_erp_api.modules.identity.infrastructure.mongo.identity_document_mapper import (
    USER_IDENTITIES_COLLECTION,
)
from gym_erp_api.modules.identity.infrastructure.mongo.mongo_credential_repository import (
    MongoCredentialRepository,
)
from gym_erp_api.modules.identity.infrastructure.mongo.mongo_identity_repository import (
    MongoIdentityRepository,
)
from gym_erp_api.modules.organization.application.bootstrap_context import (
    CREATE_ORGANIZATION_BOOTSTRAP_MEMBERSHIP_ID,
    CREATE_ORGANIZATION_BOOTSTRAP_USER_ID,
)
from gym_erp_api.modules.organization.domain.branch import Branch
from gym_erp_api.modules.organization.domain.enums import TenantStatus
from gym_erp_api.modules.organization.domain.tenant import Tenant
from gym_erp_api.modules.organization.infrastructure.mongo.branch_document_mapper import (
    BRANCHES_COLLECTION,
)
from gym_erp_api.modules.organization.infrastructure.mongo.operational_branch_repository import (
    OperationalBranchRepository,
)
from gym_erp_api.modules.organization.infrastructure.mongo.platform_tenant_repository import (
    PlatformTenantRepository,
)
from gym_erp_api.modules.organization.infrastructure.mongo.tenant_document_mapper import (
    TENANTS_COLLECTION,
)
from gym_erp_api.shared_kernel.identifiers import is_valid_uuid_v4, new_uuid
from gym_erp_api.shared_kernel.tenant_context import TenantContext

if TYPE_CHECKING:
    from pymongo.asynchronous.client_session import AsyncClientSession

_BOOTSTRAP_DISPLAY_NAME = "Dev Gym Local"
_BOOTSTRAP_LEGAL_NAME = "Gimnasio desarrollo local"
_BOOTSTRAP_BRANCH_NAME = "Sucursal inicial local"
_DEV_PLATFORM_DB = "gym_platform"
_DEV_OPERATIONAL_DB = "gym_operational"
_FORBIDDEN_APP_ENVS = frozenset({"production", "staging", "prod", "stage"})
_ALLOWED_APP_ENVS = frozenset({"development", "test"})


class BootstrapError(Exception):
    """Validación o precondición de bootstrap fallida."""


@dataclass(frozen=True, slots=True)
class BootstrapInputs:
    email: str
    password: str
    tenant_id_override: str | None


@dataclass(frozen=True, slots=True)
class BootstrapInspectReport:
    email: str
    identity_present: bool
    credential_present: bool
    bootstrap_membership_tenant_ids: tuple[str, ...]
    notes: tuple[str, ...]


def is_bootstrap_dev_tenant(tenant: Tenant) -> bool:
    return (
        tenant.display_name == _BOOTSTRAP_DISPLAY_NAME
        and tenant.legal_name == _BOOTSTRAP_LEGAL_NAME
    )


def parse_tenant_id_override(raw: str | None) -> str | None:
    if raw is None or not str(raw).strip():
        return None
    candidate = str(uuid.UUID(str(raw).strip()))
    if not is_valid_uuid_v4(candidate):
        raise BootstrapError("GYM_ERP_DEV_TENANT_ID debe ser un UUID v4 válido.")
    return candidate


def validate_opt_in(*, bootstrap_flag: str | None) -> None:
    if bootstrap_flag != "1":
        raise BootstrapError("Defina GYM_ERP_BOOTSTRAP_GYM=1 para ejecutar.")


def validate_password(password: str) -> None:
    if len(password.strip()) < 12:
        raise BootstrapError("Defina GYM_ERP_DEV_BOOTSTRAP_PASSWORD (mín. 12 caracteres).")


def validate_email(email: str) -> None:
    normalized = email.strip().lower()
    if not normalized.endswith("@local.test"):
        raise BootstrapError("Use un email @local.test para bootstrap local.")


def validate_app_env(app_env: str) -> None:
    normalized = app_env.strip().lower()
    if normalized in _FORBIDDEN_APP_ENVS:
        raise BootstrapError("Bootstrap no permitido en production/staging.")
    if normalized not in _ALLOWED_APP_ENVS:
        raise BootstrapError("Bootstrap permitido solo en development/test.")


def validate_database_names(
    *,
    platform_db: str,
    operational_db: str,
    app_env: str,
    allow_test_db_flag: str | None,
) -> None:
    platform = platform_db.strip()
    operational = operational_db.strip()
    if platform == operational:
        raise BootstrapError("Las bases platform y operational deben ser distintas.")
    uses_test_suffix = platform.endswith("_test") or operational.endswith("_test")
    if uses_test_suffix and allow_test_db_flag != "1":
        raise BootstrapError(
            "Bases *_test rechazadas para bootstrap manual. "
            "Use gym_platform/gym_operational o GYM_ERP_BOOTSTRAP_ALLOW_TEST_DB=1 "
            "solo en flujos de prueba aislados.",
        )
    if app_env.strip().lower() == "development":
        if platform != _DEV_PLATFORM_DB or operational != _DEV_OPERATIONAL_DB:
            raise BootstrapError(
                "En APP_ENV=development use "
                f"MONGODB_PLATFORM_DB={_DEV_PLATFORM_DB} y "
                f"MONGODB_OPERATIONAL_DB={_DEV_OPERATIONAL_DB}.",
            )


def validate_mongodb_uri(mongodb_uri: str | None) -> None:
    if mongodb_uri is None:
        raise BootstrapError("MONGODB_URI no configurada.")
    uri = str(mongodb_uri)
    if uri.strip().lower().startswith("mongodb+srv://"):
        raise BootstrapError("Bootstrap no permitido con mongodb+srv.")
    parsed = urlparse(uri)
    host_part = (parsed.netloc.split("@")[-1] if parsed.netloc else "").split("/")[0]
    if "," in host_part:
        raise BootstrapError("Bootstrap no permitido con URI multi-host.")
    mongo_hosts = {h.rsplit(":", 1)[0].lower() for h in host_part.split(",") if h}
    if not mongo_hosts or not mongo_hosts <= {"127.0.0.1", "localhost"}:
        raise BootstrapError("Bootstrap solo permitido con MongoDB en localhost.")


def collect_bootstrap_inputs(
    environ: dict[str, str] | None = None,
    *,
    require_password: bool = True,
) -> BootstrapInputs:
    env = environ if environ is not None else os.environ
    validate_opt_in(bootstrap_flag=env.get("GYM_ERP_BOOTSTRAP_GYM"))
    default_email = "dev.gym.owner@local.test"
    email = env.get("GYM_ERP_DEV_BOOTSTRAP_EMAIL", default_email).strip().lower()
    password = env.get("GYM_ERP_DEV_BOOTSTRAP_PASSWORD", "").strip()
    if require_password:
        validate_password(password)
    validate_email(email)
    tenant_override = parse_tenant_id_override(env.get("GYM_ERP_DEV_TENANT_ID"))
    return BootstrapInputs(email=email, password=password, tenant_id_override=tenant_override)


def validate_settings_for_bootstrap(
    settings: Settings,
    environ: dict[str, str] | None = None,
) -> None:
    env = environ if environ is not None else os.environ
    validate_app_env(settings.app_env)
    validate_mongodb_uri(
        settings.mongodb_uri.get_secret_value() if settings.mongodb_uri else None,
    )
    validate_database_names(
        platform_db=settings.mongodb_platform_db,
        operational_db=settings.mongodb_operational_db,
        app_env=settings.app_env,
        allow_test_db_flag=env.get("GYM_ERP_BOOTSTRAP_ALLOW_TEST_DB"),
    )


async def list_bootstrap_tenant_ids_for_user(
    *,
    user_id: str,
    memberships: MongoTenantMembershipRepository,
    tenants: PlatformTenantRepository,
    session: AsyncClientSession | None,
) -> list[str]:
    """Tenants bootstrap vinculados por membresía activa del usuario (no por display_name solo)."""
    active = await memberships.list_active_by_user_id(user_id, session=session)
    found: list[str] = []
    for membership in active:
        if GymRole.GYM_OWNER not in membership.gym_roles:
            continue
        tenant = await tenants.get_by_id(membership.tenant_id, session=session)
        if tenant is not None and is_bootstrap_dev_tenant(tenant):
            found.append(membership.tenant_id)
    return found


async def resolve_dev_tenant_id(
    *,
    email: str,
    tenant_id_override: str | None,
    user_id: str | None,
    memberships: MongoTenantMembershipRepository,
    tenants: PlatformTenantRepository,
    session: AsyncClientSession | None,
) -> str:
    if tenant_id_override is not None:
        return tenant_id_override

    if user_id is not None:
        bootstrap_ids = await list_bootstrap_tenant_ids_for_user(
            user_id=user_id,
            memberships=memberships,
            tenants=tenants,
            session=session,
        )
        if len(bootstrap_ids) > 1:
            raise BootstrapError(
                "Varios gimnasios bootstrap para este usuario; "
                "defina GYM_ERP_DEV_TENANT_ID con uno UUID v4 existente.",
            )
        if len(bootstrap_ids) == 1:
            return bootstrap_ids[0]

    return new_uuid()


async def assert_bootstrap_tenant_allowed(
    *,
    tenant_id: str,
    tenants: PlatformTenantRepository,
    session: AsyncClientSession | None,
) -> None:
    tenant = await tenants.get_by_id(tenant_id, session=session)
    if tenant is None:
        return
    if not is_bootstrap_dev_tenant(tenant):
        raise BootstrapError(
            "El tenant indicado no pertenece al bootstrap local de desarrollo; abortando.",
        )


async def assert_tenant_override_authorized(
    *,
    tenant_id: str,
    tenant_id_override: str | None,
    user_id: str | None,
    memberships: MongoTenantMembershipRepository,
    tenants: PlatformTenantRepository,
    session: AsyncClientSession | None,
) -> None:
    if tenant_id_override is None or tenant_id_override != tenant_id:
        return
    if user_id is not None:
        existing = await memberships.get_by_user_and_tenant(
            user_id=user_id,
            tenant_id=tenant_id,
            session=session,
        )
        if existing is not None:
            return
    tenant = await tenants.get_by_id(tenant_id, session=session)
    if tenant is not None:
        raise BootstrapError(
            "GYM_ERP_DEV_TENANT_ID apunta a un gimnasio existente sin membresía "
            "para este usuario; omita la variable o use su tenant bootstrap.",
        )


def credential_exists_message(*, email: str) -> str:
    return (
        f"El usuario {email} ya tiene credencial registrada. "
        "GYM_ERP_DEV_BOOTSTRAP_PASSWORD no se aplicará. "
        "Inicie sesión con la contraseña que configuró antes o, solo en desarrollo, "
        "elimine manualmente el documento en user_credentials si desea recrearla."
    )


def format_inspect_report(report: BootstrapInspectReport) -> str:
    lines = [
        f"email={report.email}",
        f"identity_present={report.identity_present}",
        f"credential_present={report.credential_present}",
        "bootstrap_membership_tenant_ids="
        f"{','.join(report.bootstrap_membership_tenant_ids) or '(ninguno)'}",
    ]
    for note in report.notes:
        lines.append(f"note: {note}")
    return "\n".join(lines)


async def inspect_bootstrap_state(
    databases: MongoDatabases,
    *,
    email: str,
) -> BootstrapInspectReport:
    identities = MongoIdentityRepository(databases.platform[USER_IDENTITIES_COLLECTION])
    credentials = MongoCredentialRepository(databases.platform[USER_CREDENTIALS_COLLECTION])
    memberships = MongoTenantMembershipRepository(
        databases.platform[TENANT_MEMBERSHIPS_COLLECTION],
    )
    tenants = PlatformTenantRepository(databases.platform[TENANTS_COLLECTION])

    notes: list[str] = []
    identity = await identities.get_by_email_normalized(email)
    identity_present = identity is not None
    credential_present = False
    bootstrap_ids: tuple[str, ...] = ()

    if identity is not None:
        cred = await credentials.get_by_user_id(identity.user_id)
        credential_present = cred is not None
        ids = await list_bootstrap_tenant_ids_for_user(
            user_id=identity.user_id,
            memberships=memberships,
            tenants=tenants,
            session=None,
        )
        bootstrap_ids = tuple(ids)
        if identity_present and credential_present and not bootstrap_ids:
            notes.append(
                "Estado parcial probable: identidad y credencial sin membresía bootstrap.",
            )
        if identity_present and bootstrap_ids and not credential_present:
            notes.append("Identidad con membresía bootstrap pero sin credencial.")
    else:
        notes.append("Sin identidad; primera ejecución creará UUID v4 nuevo para el tenant.")

    return BootstrapInspectReport(
        email=email,
        identity_present=identity_present,
        credential_present=credential_present,
        bootstrap_membership_tenant_ids=bootstrap_ids,
        notes=tuple(notes),
    )


def _is_transaction_not_supported(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "replica set" in text or "transaction numbers" in text


async def apply_bootstrap_writes(
    *,
    databases: MongoDatabases,
    inputs: BootstrapInputs,
    moment: datetime,
    session: AsyncClientSession | None,
    credential_already_exists: bool,
) -> str:
    identities = MongoIdentityRepository(databases.platform[USER_IDENTITIES_COLLECTION])
    credentials = MongoCredentialRepository(databases.platform[USER_CREDENTIALS_COLLECTION])
    memberships = MongoTenantMembershipRepository(
        databases.platform[TENANT_MEMBERSHIPS_COLLECTION],
    )
    tenants = PlatformTenantRepository(databases.platform[TENANTS_COLLECTION])

    existing = await identities.get_by_email_normalized(inputs.email)
    user_id = existing.user_id if existing is not None else None

    tenant_id = await resolve_dev_tenant_id(
        email=inputs.email,
        tenant_id_override=inputs.tenant_id_override,
        user_id=user_id,
        memberships=memberships,
        tenants=tenants,
        session=session,
    )

    await assert_bootstrap_tenant_allowed(tenant_id=tenant_id, tenants=tenants, session=session)
    await assert_tenant_override_authorized(
        tenant_id=tenant_id,
        tenant_id_override=inputs.tenant_id_override,
        user_id=user_id,
        memberships=memberships,
        tenants=tenants,
        session=session,
    )

    if existing is None:
        identity = UserIdentity.create(email=inputs.email, now=moment).mark_email_verified(
            now=moment,
        )
        await identities.save(identity, session=session)
    else:
        identity = existing

    # Concurrencia: re-resolver tras crear/leer identidad por si otra ejecución completó membresía.
    tenant_id = await resolve_dev_tenant_id(
        email=inputs.email,
        tenant_id_override=inputs.tenant_id_override,
        user_id=identity.user_id,
        memberships=memberships,
        tenants=tenants,
        session=session,
    )
    await assert_bootstrap_tenant_allowed(tenant_id=tenant_id, tenants=tenants, session=session)

    if not credential_already_exists:
        hasher = Argon2PasswordHasher()
        await credentials.insert(
            UserCredential.create(
                user_id=identity.user_id,
                password_hash=hasher.hash(inputs.password),
                credential_version=0,
                now=moment,
            ),
            session=session,
        )

    tenant = await tenants.get_by_id(tenant_id, session=session)
    if tenant is None:
        created = Tenant.create(
            legal_name=_BOOTSTRAP_LEGAL_NAME,
            display_name=_BOOTSTRAP_DISPLAY_NAME,
            tenant_id=tenant_id,
            now=moment,
        )
        created = created.transition_status(TenantStatus.ACTIVE, now=moment)
        await tenants.insert(created, session=session)

    membership = await memberships.get_by_user_and_tenant(
        user_id=identity.user_id,
        tenant_id=tenant_id,
        session=session,
    )
    if membership is None:
        await memberships.insert(
            TenantMembership.create_active(
                user_id=identity.user_id,
                tenant_id=tenant_id,
                gym_roles=frozenset({GymRole.GYM_OWNER}),
                branch_scope_mode=BranchScopeMode.ALL_BRANCHES,
                now=moment,
            ),
            session=session,
        )

    bootstrap_ctx = TenantContext(
        tenant_id=tenant_id,
        user_id=CREATE_ORGANIZATION_BOOTSTRAP_USER_ID,
        membership_id=CREATE_ORGANIZATION_BOOTSTRAP_MEMBERSHIP_ID,
        allowed_branch_ids=None,
    )
    branch_repo = OperationalBranchRepository(
        TenantScopedRepository(
            databases.operational[BRANCHES_COLLECTION],
            bootstrap_ctx,
            branch_scoped=False,
        ),
    )
    listed = await branch_repo.list_branches(session=session)
    if not listed:
        await branch_repo.insert(
            Branch.create(
                tenant_id=tenant_id,
                name=_BOOTSTRAP_BRANCH_NAME,
                now=moment,
            ),
            session=session,
        )

    return tenant_id


async def run_bootstrap(settings: Settings, inputs: BootstrapInputs) -> tuple[str, bool]:
    """Ejecuta bootstrap idempotente. Devuelve (tenant_id, credencial_ya_existía)."""
    client = create_mongo_client(settings)
    if client is None:
        raise BootstrapError("No se pudo conectar a MongoDB.")

    databases = MongoDatabases(client, settings)
    moment = datetime.now(tz=UTC)
    cred_exists = False

    try:
        identities = MongoIdentityRepository(databases.platform[USER_IDENTITIES_COLLECTION])
        credentials = MongoCredentialRepository(databases.platform[USER_CREDENTIALS_COLLECTION])

        existing_identity = await identities.get_by_email_normalized(inputs.email)
        if existing_identity is not None:
            cred = await credentials.get_by_user_id(existing_identity.user_id)
            cred_exists = cred is not None

        tenant_id: str

        async def _writes(session: AsyncClientSession | None) -> None:
            nonlocal tenant_id
            tenant_id = await apply_bootstrap_writes(
                databases=databases,
                inputs=inputs,
                moment=moment,
                session=session,
                credential_already_exists=cred_exists,
            )

        try:
            async with MongoUnitOfWork(databases) as uow:
                await _writes(uow.session)
        except Exception as exc:
            if not _is_transaction_not_supported(exc):
                raise
            await _writes(None)

        return tenant_id, cred_exists
    finally:
        await client.close()


async def run_inspect(settings: Settings, email: str) -> BootstrapInspectReport:
    client = create_mongo_client(settings)
    if client is None:
        raise BootstrapError("No se pudo conectar a MongoDB.")
    try:
        databases = MongoDatabases(client, settings)
        return await inspect_bootstrap_state(databases, email=email)
    finally:
        await client.close()


async def main() -> int:
    try:
        inspect_only = os.environ.get("GYM_ERP_BOOTSTRAP_INSPECT") == "1"
        inputs = collect_bootstrap_inputs(require_password=not inspect_only)
        settings = get_settings()
        validate_settings_for_bootstrap(settings)
        if inspect_only:
            report = await run_inspect(settings, inputs.email)
            print(format_inspect_report(report))
            return 0
        tenant_id, cred_exists = await run_bootstrap(settings, inputs)
        if cred_exists:
            print(credential_exists_message(email=inputs.email), file=sys.stderr)
        print(f"Bootstrap OK. email={inputs.email} tenant_id={tenant_id}")
        return 0
    except BootstrapError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
