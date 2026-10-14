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
    """Validación completa de URI (usuario, query, allowlist)."""
    from tests.support.integration_environment import validate_integration_mongodb_uri as _full

    _full(uri)
