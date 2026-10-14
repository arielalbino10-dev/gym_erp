"""Validación conjunta del entorno de integración MongoDB (sin revelar credenciales)."""

from __future__ import annotations

import secrets
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from tests.support.mongodb_uri_guard import (
    ALLOWED_HOSTS,
    FORBIDDEN_DB_NAMES,
    database_name_from_mongodb_uri,
)

ALLOWED_INTEGRATION_DATABASES = frozenset({"gym_platform_test", "gym_operational_test"})
EXPECTED_OPERATIONAL_DB_IN_URI = "gym_operational_test"
EXPECTED_INTEGRATION_USER = "gym_erp_integration"
FORBIDDEN_INTEGRATION_USERS = frozenset({"gym_erp_admin", "gym_erp_app"})
EXPECTED_AUTH_SOURCE = "admin"
EXPECTED_REPLICA_SET = "rs0"
ALLOWED_MONGODB_PORT = 27017

INTEGRATION_COLLECTION_PREFIX = "gym_erp_iso_"

FORBIDDEN_PRIVILEGED_ROLES = frozenset(
    {
        "root",
        "dbAdminAnyDatabase",
        "userAdminAnyDatabase",
        "readWriteAnyDatabase",
        "readAnyDatabase",
        "clusterAdmin",
        "clusterManager",
        "hostManager",
        "backup",
        "restore",
        "dbOwner",
    }
)

ALLOWED_ROLES_ON_TEST_DATABASES = frozenset({"read", "readWrite"})


def username_from_mongodb_uri(uri: str) -> str:
    parsed = urlparse(uri)
    if not parsed.username:
        raise ValueError(
            "La URI de integración debe incluir usuario (use el usuario de integración dedicado)."
        )
    return unquote(parsed.username)


def mongodb_uri_query_params(uri: str) -> dict[str, list[str]]:
    parsed = urlparse(uri)
    return parse_qs(parsed.query, keep_blank_values=False)


def validate_mongodb_uri_host_and_port(uri: str) -> None:
    parsed = urlparse(uri)
    if parsed.scheme != "mongodb":
        raise ValueError(
            "La URI de integración debe usar el esquema 'mongodb' (no mongodb+srv ni otros)."
        )
    if parsed.port is not None and parsed.port != ALLOWED_MONGODB_PORT:
        raise ValueError(
            f"Puerto MongoDB no permitido para integración (use {ALLOWED_MONGODB_PORT})."
        )
    host = (parsed.hostname or "").lower()
    if not host or host not in ALLOWED_HOSTS:
        raise ValueError(
            "La URI de integración debe apuntar a localhost o 127.0.0.1 (no host remoto)."
        )
    netloc = parsed.netloc or ""
    if "," in netloc or "@" in netloc and netloc.count("@") > 1:
        raise ValueError("La URI de integración no debe listar múltiples hosts.")


def validate_mongodb_uri_user(uri: str) -> None:
    user = username_from_mongodb_uri(uri).lower()
    if user in FORBIDDEN_INTEGRATION_USERS:
        raise ValueError(
            f"Usuario prohibido para integración: {user!r}. "
            f"Use únicamente {EXPECTED_INTEGRATION_USER!r}."
        )
    if user != EXPECTED_INTEGRATION_USER:
        raise ValueError(
            f"Usuario de integración inesperado: {user!r}. "
            f"Se requiere {EXPECTED_INTEGRATION_USER!r}."
        )


def validate_mongodb_uri_query(uri: str) -> None:
    params = mongodb_uri_query_params(uri)
    replica_values = params.get("replicaSet") or params.get("replicaset")
    if not replica_values or replica_values[0] != EXPECTED_REPLICA_SET:
        raise ValueError(
            f"La URI debe incluir replicaSet={EXPECTED_REPLICA_SET!r} en query string."
        )
    auth_values = params.get("authSource")
    if not auth_values or auth_values[0].lower() != EXPECTED_AUTH_SOURCE:
        raise ValueError(
            f"La URI debe incluir authSource={EXPECTED_AUTH_SOURCE!r} en query string."
        )


def assert_allowed_integration_database_name(name: str) -> str:
    normalized = name.strip().lower()
    if normalized in FORBIDDEN_DB_NAMES:
        raise ValueError(f"Base de datos prohibida para pruebas: {normalized!r}.")
    if normalized not in ALLOWED_INTEGRATION_DATABASES:
        raise ValueError(
            "Nombre de base de datos fuera de la allowlist de integración "
            f"(permitidas: {sorted(ALLOWED_INTEGRATION_DATABASES)!r})."
        )
    return normalized


def validate_integration_database_settings(platform_db: str, operational_db: str) -> None:
    platform = assert_allowed_integration_database_name(platform_db)
    operational = assert_allowed_integration_database_name(operational_db)
    if platform == operational:
        raise ValueError("Las bases platform y operational de integración deben ser distintas.")
    if platform != "gym_platform_test":
        raise ValueError("MONGODB_PLATFORM_DB debe ser exactamente 'gym_platform_test'.")
    if operational != "gym_operational_test":
        raise ValueError("MONGODB_OPERATIONAL_DB debe ser exactamente 'gym_operational_test'.")


def validate_integration_mongodb_uri(uri: str) -> None:
    """Valida URI local de integración (path = gym_operational_test, usuario y query)."""
    validate_mongodb_uri_host_and_port(uri)
    validate_mongodb_uri_user(uri)
    validate_mongodb_uri_query(uri)
    db_name = database_name_from_mongodb_uri(uri)
    assert_allowed_integration_database_name(db_name)
    if db_name != EXPECTED_OPERATIONAL_DB_IN_URI:
        raise ValueError(
            "El path de la URI debe apuntar a la base operational de prueba "
            f"({EXPECTED_OPERATIONAL_DB_IN_URI!r})."
        )


def validate_integration_environment(
    *,
    uri: str,
    platform_db: str,
    operational_db: str,
) -> None:
    """Validación conjunta antes de abrir conexión."""
    validate_integration_mongodb_uri(uri)
    validate_integration_database_settings(platform_db, operational_db)


def generate_ephemeral_collection_name() -> str:
    return f"{INTEGRATION_COLLECTION_PREFIX}{secrets.token_hex(8)}"


def assert_ephemeral_collection_safe_for_teardown(
    collection_name: str,
    *,
    expected_name: str,
    operational_db: str,
) -> None:
    assert_allowed_integration_database_name(operational_db)
    if operational_db != EXPECTED_OPERATIONAL_DB_IN_URI:
        raise ValueError("La limpieza solo está permitida en gym_operational_test.")
    if collection_name != expected_name:
        raise ValueError("El nombre de colección no coincide con el registrado para la ejecución.")
    if not collection_name.startswith(INTEGRATION_COLLECTION_PREFIX):
        raise ValueError("La colección no tiene el prefijo reservado a pruebas de integración.")


def _normalize_role_db(role_db: str) -> str:
    return role_db.strip().lower()


def validate_integration_authenticated_roles(auth_info: dict[str, Any]) -> None:
    """Valida roles de connectionStatus (sin conectar por sí mismo)."""
    users = auth_info.get("authenticatedUsers") or []
    if not users:
        raise ValueError("connectionStatus no reporta usuario autenticado.")
    primary = users[0]
    auth_user = str(primary.get("user", "")).lower()
    if auth_user in FORBIDDEN_INTEGRATION_USERS:
        raise ValueError(f"Usuario autenticado prohibido: {auth_user!r}.")
    if auth_user != EXPECTED_INTEGRATION_USER:
        raise ValueError(f"Usuario autenticado inesperado: {auth_user!r}.")

    roles: list[dict[str, Any]] = list(auth_info.get("authenticatedUserRoles") or [])
    if not roles:
        raise ValueError("El usuario de integración no tiene roles asignados.")

    seen: set[tuple[str, str]] = set()
    allowed_dbs = ALLOWED_INTEGRATION_DATABASES
    for entry in roles:
        role_name = str(entry.get("role", ""))
        role_db = _normalize_role_db(str(entry.get("db", "")))
        if role_name in FORBIDDEN_PRIVILEGED_ROLES:
            raise ValueError(f"Rol privilegiado no permitido en integración: {role_name!r}.")
        if role_db not in allowed_dbs:
            raise ValueError(f"Rol {role_name!r} sobre base no autorizada: {role_db!r}.")
        if role_name not in ALLOWED_ROLES_ON_TEST_DATABASES:
            raise ValueError(
                f"Rol {role_name!r} no permitido; use read o readWrite en bases *_test."
            )
        seen.add((role_name, role_db))

    dbs_with_access = {db for _, db in seen}
    if dbs_with_access != allowed_dbs:
        raise ValueError(
            "Los roles deben cubrir exactamente gym_platform_test y gym_operational_test."
        )


async def verify_integration_mongodb_identity(client: Any) -> None:
    """Comprueba connectionStatus antes de cualquier escritura en integración."""
    status = await client.admin.command("connectionStatus")
    auth_info = status.get("authInfo") or {}
    validate_integration_authenticated_roles(auth_info)
