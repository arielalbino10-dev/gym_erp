"""Fingerprint determinista para CreateOrganization (conflictos idempotencia).

Campos incluidos (valores ya normalizados en ``CreateOrganizationCommand``):

- ``legal_name``, ``display_name``
- ``commercial_email_normalized`` (None si no hay correo)
- ``tenant_timezone``, ``branch_name``, ``branch_timezone``
- ``branch_code`` (None si ausente)
- ``branch_address`` — objeto canónico con line1, city, line2, state, postal_code, country_code
- ``created_by_user_id`` (None si bootstrap sin actor)

Excluidos:

- ``idempotency_key`` (identifica la operación junto con ``operation`` en el store)
- ``correlation_id`` y demás metadatos de trazabilidad
- Identificadores generados (``tenant_id``, ``branch_id``)

El payload incluye ``v`` (esquema) y ``operation`` (``create_organization``).
Textos relevantes se normalizan a Unicode NFC antes del hash.

Serialización: JSON UTF-8 con claves ordenadas y separadores fijos; hash SHA-256 hex.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from typing import Any

from gym_erp_api.modules.organization.application.commands.create_organization import (
    CreateOrganizationCommand,
)
from gym_erp_api.modules.organization.application.idempotency_constants import (
    CREATE_ORGANIZATION_OPERATION,
)

_FINGERPRINT_SCHEMA_VERSION = 1


def create_organization_request_fingerprint(command: CreateOrganizationCommand) -> str:
    payload = _canonical_business_payload(command)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _canonical_business_payload(command: CreateOrganizationCommand) -> dict[str, Any]:
    address: dict[str, Any] | None = None
    if command.branch_address is not None:
        addr = command.branch_address
        address = {
            "line1": addr.line1,
            "city": addr.city,
            "line2": addr.line2,
            "state": addr.state,
            "postal_code": addr.postal_code,
            "country_code": addr.country_code,
        }
    return {
        "v": _FINGERPRINT_SCHEMA_VERSION,
        "operation": CREATE_ORGANIZATION_OPERATION,
        "legal_name": _nfc(command.legal_name),
        "display_name": _nfc(command.display_name),
        "commercial_email_normalized": (
            _nfc(command.commercial_email_normalized)
            if command.commercial_email_normalized is not None
            else None
        ),
        "tenant_timezone": command.tenant_timezone,
        "branch_name": _nfc(command.branch_name),
        "branch_timezone": command.branch_timezone,
        "branch_code": command.branch_code,
        "branch_address": address,
        "created_by_user_id": command.created_by_user_id,
    }


def _nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)
