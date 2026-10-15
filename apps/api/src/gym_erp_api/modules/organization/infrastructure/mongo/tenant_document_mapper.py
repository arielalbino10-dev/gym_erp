"""Mapper Tenant ↔ documento MongoDB (colección platform ``tenants``)."""

from __future__ import annotations

from typing import Any

from gym_erp_api.modules.organization.domain.tenant import Tenant

TENANTS_COLLECTION = "tenants"


def tenant_to_document(tenant: Tenant) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "_id": tenant.tenant_id,
        "tenant_id": tenant.tenant_id,
        "legal_name": tenant.legal_name,
        "display_name": tenant.display_name,
        "status": tenant.status.value,
        "timezone": tenant.timezone,
        "created_at": tenant.created_at,
        "updated_at": tenant.updated_at,
    }
    if tenant.commercial_email is not None:
        doc["commercial_email"] = tenant.commercial_email
        doc["commercial_email_normalized"] = tenant.commercial_email_normalized
    if tenant.created_by_user_id is not None:
        doc["created_by_user_id"] = tenant.created_by_user_id
    if tenant.updated_by_user_id is not None:
        doc["updated_by_user_id"] = tenant.updated_by_user_id
    return doc


def tenant_from_document(raw: dict[str, Any]) -> Tenant:
    return Tenant.from_persistence(raw)
