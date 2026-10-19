"""Hash SHA-256 del token opaco de sesión (ADR-0003)."""

from __future__ import annotations

import hashlib
import secrets


def generate_opaque_session_token(*, nbytes: int = 32) -> str:
    """Token opaco CSPRNG (no persistir; usar solo para emitir cookie en H2-B.4)."""
    if nbytes < 32:
        raise ValueError("El token de sesión debe tener al menos 32 bytes de entropía.")
    return secrets.token_urlsafe(nbytes)


def hash_session_token(raw_token: str) -> str:
    if not isinstance(raw_token, str) or not raw_token.strip():
        raise ValueError("Token de sesión inválido.")
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
