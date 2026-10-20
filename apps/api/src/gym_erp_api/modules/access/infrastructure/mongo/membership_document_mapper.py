"""Mapper BSON tenant_memberships (gym_platform)."""

from __future__ import annotations

from typing import Any

from gym_erp_api.modules.access.domain.tenant_membership import TenantMembership


def membership_to_document(membership: TenantMembership) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "_id": membership.membership_id,
        "user_id": membership.user_id,
        "tenant_id": membership.tenant_id,
        "status": membership.status.value,
        "branch_scope_mode": membership.branch_scope_mode.value,
        "gym_roles": sorted(role.value for role in membership.gym_roles),
        "authz_epoch": membership.authz_epoch,
        "created_at": membership.created_at,
        "updated_at": membership.updated_at,
    }
    if membership.allowed_branch_ids is not None:
        doc["allowed_branch_ids"] = sorted(membership.allowed_branch_ids)
    if membership.invited_at is not None:
        doc["invited_at"] = membership.invited_at
    if membership.accepted_at is not None:
        doc["accepted_at"] = membership.accepted_at
    if membership.created_by_user_id is not None:
        doc["created_by_user_id"] = membership.created_by_user_id
    return doc


def membership_from_document(raw: dict[str, Any]) -> TenantMembership:
    return TenantMembership.from_persistence(raw)
