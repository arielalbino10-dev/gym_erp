"""Mapper MongoDB — platform_role_assignments."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from gym_erp_api.modules.platform_admin.domain.platform_permission import PlatformPermission
from gym_erp_api.modules.platform_admin.domain.platform_role import PlatformRole
from gym_erp_api.modules.platform_admin.domain.platform_role_assignment import (
    PlatformRoleAssignment,
)

PLATFORM_ROLE_ASSIGNMENTS_COLLECTION = "platform_role_assignments"


def assignment_to_document(assignment: PlatformRoleAssignment) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "_id": assignment.user_id,
        "roles": sorted(role.value for role in assignment.roles),
        "granted_permissions": sorted(p.value for p in assignment.granted_permissions),
        "revoked_permissions": sorted(p.value for p in assignment.revoked_permissions),
    }
    if assignment.updated_at is not None:
        doc["updated_at"] = assignment.updated_at
    if assignment.updated_by_user_id is not None:
        doc["updated_by_user_id"] = assignment.updated_by_user_id
    return doc


def assignment_from_document(doc: dict[str, Any]) -> PlatformRoleAssignment:
    roles_raw = doc.get("roles") or []
    granted_raw = doc.get("granted_permissions") or []
    revoked_raw = doc.get("revoked_permissions") or []
    updated_at = doc.get("updated_at")
    if updated_at is not None and not isinstance(updated_at, datetime):
        updated_at = None
    return PlatformRoleAssignment(
        user_id=str(doc["_id"]),
        roles=frozenset(PlatformRole(value) for value in roles_raw),
        granted_permissions=frozenset(PlatformPermission(value) for value in granted_raw),
        revoked_permissions=frozenset(PlatformPermission(value) for value in revoked_raw),
        updated_at=updated_at,
        updated_by_user_id=doc.get("updated_by_user_id"),
    )
