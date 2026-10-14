"""Validación de URI para pruebas de integración (sin conectar a MongoDB)."""

from urllib.parse import unquote, urlparse

FORBIDDEN_DB_NAMES = frozenset({"gym_platform", "gym_operational"})
ALLOWED_HOSTS = frozenset({"127.0.0.1", "localhost"})


def database_name_from_mongodb_uri(uri: str) -> str:
    parsed = urlparse(uri)
    path = (parsed.path or "").lstrip("/")
    if not path:
        raise ValueError("La URI de prueba debe incluir un nombre de base de datos en el path.")
    raw_name = path.split("/")[0]
    return unquote(raw_name).lower()


def validate_integration_mongodb_uri(uri: str) -> None:
    parsed = urlparse(uri)
    if parsed.scheme != "mongodb":
        raise ValueError(
            "La URI de integración debe usar el esquema 'mongodb' (no mongodb+srv ni otros)."
        )
    host = (parsed.hostname or "").lower()
    if not host or host not in ALLOWED_HOSTS:
        raise ValueError(
            "La URI de integración debe apuntar a localhost o 127.0.0.1 (no host remoto)."
        )
    db_name = database_name_from_mongodb_uri(uri)
    if db_name in FORBIDDEN_DB_NAMES:
        raise ValueError(
            f"Base de datos prohibida para pruebas: {db_name!r}. "
            "Use una BD dedicada terminada en _test."
        )
    if not db_name.endswith("_test"):
        raise ValueError(
            f"El nombre de base de datos debe terminar en '_test' (recibido: {db_name!r})."
        )
