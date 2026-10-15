"""Mapper Branch ↔ documento MongoDB (colección operational ``branches``)."""

from __future__ import annotations

from typing import Any

from gym_erp_api.modules.organization.domain.branch import Branch
from gym_erp_api.modules.organization.domain.value_objects import BranchAddress

BRANCHES_COLLECTION = "branches"


def branch_to_document(branch: Branch) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "_id": branch.branch_id,
        "branch_id": branch.branch_id,
        "tenant_id": branch.tenant_id,
        "name": branch.name,
        "status": branch.status.value,
        "timezone": branch.timezone,
        "created_at": branch.created_at,
        "updated_at": branch.updated_at,
    }
    if branch.code is not None:
        doc["code"] = branch.code
    if branch.address is not None:
        doc["address"] = _address_to_document(branch.address)
    if branch.created_by_user_id is not None:
        doc["created_by_user_id"] = branch.created_by_user_id
    if branch.updated_by_user_id is not None:
        doc["updated_by_user_id"] = branch.updated_by_user_id
    return doc


def branch_from_document(raw: dict[str, Any]) -> Branch:
    return Branch.from_persistence(raw)


def _address_to_document(address: BranchAddress) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "line1": address.line1,
        "city": address.city,
        "country_code": address.country_code,
    }
    if address.line2 is not None:
        payload["line2"] = address.line2
    if address.state is not None:
        payload["state"] = address.state
    if address.postal_code is not None:
        payload["postal_code"] = address.postal_code
    return payload
