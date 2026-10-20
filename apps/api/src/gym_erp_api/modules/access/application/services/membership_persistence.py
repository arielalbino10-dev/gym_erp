"""Persistencia de membresía con validación de alcance (application, pre-HTTP)."""

from __future__ import annotations

from gym_erp_api.modules.access.application.ports.membership_repository import MembershipRepository
from gym_erp_api.modules.access.application.ports.tenant_branch_scope_validator import (
    TenantBranchScopeValidator,
)
from gym_erp_api.modules.access.application.services.membership_branch_scope import (
    ensure_membership_branch_scope,
)
from gym_erp_api.modules.access.domain.tenant_membership import TenantMembership


async def insert_membership_with_validated_scope(
    membership: TenantMembership,
    *,
    repository: MembershipRepository,
    branch_validator: TenantBranchScopeValidator,
    session: object | None = None,
) -> None:
    await ensure_membership_branch_scope(
        tenant_id=membership.tenant_id,
        branch_scope_mode=membership.branch_scope_mode,
        allowed_branch_ids=membership.allowed_branch_ids,
        validator=branch_validator,
        session=session,
    )
    await repository.insert(membership, session=session)


async def save_membership_with_validated_scope(
    membership: TenantMembership,
    *,
    expected_authz_epoch: int,
    repository: MembershipRepository,
    branch_validator: TenantBranchScopeValidator,
    session: object | None = None,
) -> None:
    await ensure_membership_branch_scope(
        tenant_id=membership.tenant_id,
        branch_scope_mode=membership.branch_scope_mode,
        allowed_branch_ids=membership.allowed_branch_ids,
        validator=branch_validator,
        session=session,
    )
    await repository.save(
        membership,
        expected_authz_epoch=expected_authz_epoch,
        session=session,
    )
