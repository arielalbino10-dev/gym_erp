"""Normalización determinista de correo (D4); sin reglas por proveedor."""

import unicodedata


def normalize_email(value: str) -> str:
    """Devuelve email_normalized o lanza ValueError si queda vacío."""
    if not isinstance(value, str):
        raise ValueError("El correo debe ser una cadena.")
    trimmed = value.strip()
    step1 = unicodedata.normalize("NFKC", trimmed)
    step2 = step1.casefold()
    normalized = unicodedata.normalize("NFKC", step2)
    if not normalized:
        raise ValueError("El correo normalizado no puede estar vacío.")
    return normalized
