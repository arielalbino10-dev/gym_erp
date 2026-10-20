"""TenantContextFactory (H2-C.2)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from gym_erp_api.modules.access.application.dto.trusted_auth import TrustedGymAuthContext
from gym_erp_api.modules.access.application.errors import (
    MembershipAccessDeniedError,
    MembershipNotFoundError,
    TenantNotSelectedError,
)
from gym_erp_api.modules.access.application.services.tenant_context_factory import (
    TenantContextFactory,
)
from gym_erp_api.modules.access.domain.enums import BranchScopeMode, GymRole
from gym_erp_api.modules.access.domain.tenant_membership import TenantMembership
from gym_erp_api.modules.organization.domain.enums import TenantStatus
from gym_erp_api.modules.organization.domain.tenant import Tenant
from tests.support.tenant_fixtures import (
    BRANCH_X_ID,
    MEMBERSHIP_A_ID,
    TENANT_A_ID,
    TENANT_B_ID,
    USER_A_ID,
)


def _moment() -> datetime:
    return datetime(2026, 6, 2, 9, 0, tzinfo=UTC)


def _active_membership(**kwargs: object) -> TenantMembership:
    defaults = {
        "user_id": USER_A_ID,
        "tenant_id": TENANT_A_ID,
        "gym_roles": frozenset({GymRole.GYM_OWNER}),
        "branch_scope_mode": BranchScopeMode.ALL_BRANCHES,
        "now": _moment(),
    }
    defaults.update(kwargs)
    return TenantMembership.create_active(**defaults)  # type: ignore[arg-type]


def _tenant_active() -> Tenant:
    provisioning = Tenant.create(
        legal_name="Legal",
        display_name="Gym",
        tenant_id=TENANT_A_ID,
        now=_moment(),
    )
    return provisioning.transition_status(TenantStatus.ACTIVE, now=_moment())


@pytest.mark.asyncio
async def test_factory_requires_selected_tenant():
    factory = TenantContextFactory(
        memberships=AsyncMock(),
        tenants=AsyncMock(),
    )
    auth = TrustedGymAuthContext(user_id=USER_A_ID, selected_tenant_id=None)
    with pytest.raises(TenantNotSelectedError):
        await factory.build_for_gym(auth)


@pytest.mark.asyncio
async def test_factory_membership_not_found():
    memberships = AsyncMock()
    memberships.get_by_user_and_tenant = AsyncMock(return_value=None)
    factory = TenantContextFactory(memberships=memberships, tenants=AsyncMock())
    auth = TrustedGymAuthContext(user_id=USER_A_ID, selected_tenant_id=TENANT_A_ID)
    with pytest.raises(MembershipNotFoundError):
        await factory.build_for_gym(auth)


@pytest.mark.asyncio
async def test_factory_rejects_suspended_membership():
    active = _active_membership()
    suspended = active.suspend()
    memberships = AsyncMock()
    memberships.get_by_user_and_tenant = AsyncMock(return_value=suspended)
    tenants = AsyncMock()
    tenants.get_by_id = AsyncMock(return_value=_tenant_active())
    factory = TenantContextFactory(memberships=memberships, tenants=tenants)
    auth = TrustedGymAuthContext(user_id=USER_A_ID, selected_tenant_id=TENANT_A_ID)
    with pytest.raises(MembershipAccessDeniedError, match="suspendida"):
        await factory.build_for_gym(auth)


@pytest.mark.asyncio
async def test_factory_rejects_revoked_membership():
    revoked = _active_membership().revoke()
    memberships = AsyncMock()
    memberships.get_by_user_and_tenant = AsyncMock(return_value=revoked)
    factory = TenantContextFactory(memberships=memberships, tenants=AsyncMock())
    auth = TrustedGymAuthContext(user_id=USER_A_ID, selected_tenant_id=TENANT_A_ID)
    with pytest.raises(MembershipAccessDeniedError, match="revocada"):
        await factory.build_for_gym(auth)


@pytest.mark.asyncio
async def test_factory_rejects_invited_membership():
    invited = TenantMembership.create_invited(
        user_id=USER_A_ID,
        tenant_id=TENANT_A_ID,
        gym_roles=frozenset({GymRole.GYM_ADMIN}),
        branch_scope_mode=BranchScopeMode.ALL_BRANCHES,
        now=_moment(),
    )
    memberships = AsyncMock()
    memberships.get_by_user_and_tenant = AsyncMock(return_value=invited)
    factory = TenantContextFactory(memberships=memberships, tenants=AsyncMock())
    auth = TrustedGymAuthContext(user_id=USER_A_ID, selected_tenant_id=TENANT_A_ID)
    with pytest.raises(MembershipAccessDeniedError, match="no aceptada"):
        await factory.build_for_gym(auth)


@pytest.mark.asyncio
async def test_factory_all_branches_produces_context():
    membership = _active_membership(membership_id=MEMBERSHIP_A_ID)
    memberships = AsyncMock()
    memberships.get_by_user_and_tenant = AsyncMock(return_value=membership)
    tenants = AsyncMock()
    tenants.get_by_id = AsyncMock(return_value=_tenant_active())
    factory = TenantContextFactory(memberships=memberships, tenants=tenants)
    auth = TrustedGymAuthContext(user_id=USER_A_ID, selected_tenant_id=TENANT_A_ID)
    resolved = await factory.build_for_gym(auth)
    assert resolved.context.tenant_id == TENANT_A_ID
    assert resolved.context.user_id == USER_A_ID
    assert resolved.context.membership_id == membership.membership_id
    assert resolved.context.allowed_branch_ids is None
    assert resolved.gym_roles == frozenset({"gym_owner"})


@pytest.mark.asyncio
async def test_factory_explicit_branches():
    membership = _active_membership(
        gym_roles=frozenset({GymRole.BRANCH_ADMIN}),
        branch_scope_mode=BranchScopeMode.EXPLICIT_BRANCHES,
        allowed_branch_ids=frozenset({BRANCH_X_ID}),
    )
    memberships = AsyncMock()
    memberships.get_by_user_and_tenant = AsyncMock(return_value=membership)
    tenants = AsyncMock()
    tenants.get_by_id = AsyncMock(return_value=_tenant_active())
    factory = TenantContextFactory(memberships=memberships, tenants=tenants)
    auth = TrustedGymAuthContext(user_id=USER_A_ID, selected_tenant_id=TENANT_A_ID)
    resolved = await factory.build_for_gym(auth)
    assert resolved.context.allowed_branch_ids == frozenset({BRANCH_X_ID})


@pytest.mark.asyncio
async def test_factory_cross_tenant_denied():
    """Usuario con membresía en A no obtiene contexto al pedir tenant B."""
    membership_a = _active_membership(tenant_id=TENANT_A_ID)
    memberships = AsyncMock()

    async def lookup(*, user_id: str, tenant_id: str, session=None):
        if tenant_id == TENANT_A_ID:
            return membership_a
        return None

    memberships.get_by_user_and_tenant = AsyncMock(side_effect=lookup)
    factory = TenantContextFactory(memberships=memberships, tenants=AsyncMock())
    auth = TrustedGymAuthContext(user_id=USER_A_ID, selected_tenant_id=TENANT_B_ID)
    with pytest.raises(MembershipNotFoundError):
        await factory.build_for_gym(auth)


@pytest.mark.asyncio
async def test_factory_tenant_suspended():
    membership = _active_membership()
    memberships = AsyncMock()
    memberships.get_by_user_and_tenant = AsyncMock(return_value=membership)
    tenant = _tenant_active().transition_status(TenantStatus.SUSPENDED, now=_moment())
    tenants = AsyncMock()
    tenants.get_by_id = AsyncMock(return_value=tenant)
    factory = TenantContextFactory(memberships=memberships, tenants=tenants)
    auth = TrustedGymAuthContext(user_id=USER_A_ID, selected_tenant_id=TENANT_A_ID)
    with pytest.raises(MembershipAccessDeniedError, match="suspendido"):
        await factory.build_for_gym(auth)


@pytest.mark.asyncio
async def test_factory_rejects_provisioning_tenant():
    membership = _active_membership()
    memberships = AsyncMock()
    memberships.get_by_user_and_tenant = AsyncMock(return_value=membership)
    provisioning = Tenant.create(
        legal_name="Legal",
        display_name="Gym",
        tenant_id=TENANT_A_ID,
        now=_moment(),
    )
    tenants = AsyncMock()
    tenants.get_by_id = AsyncMock(return_value=provisioning)
    factory = TenantContextFactory(memberships=memberships, tenants=tenants)
    auth = TrustedGymAuthContext(user_id=USER_A_ID, selected_tenant_id=TENANT_A_ID)
    with pytest.raises(MembershipAccessDeniedError, match="no activo"):
        await factory.build_for_gym(auth)


@pytest.mark.asyncio
async def test_factory_distinguishes_not_selected_vs_denied():
    factory = TenantContextFactory(memberships=AsyncMock(), tenants=AsyncMock())
    with pytest.raises(TenantNotSelectedError):
        await factory.build_for_gym(
            TrustedGymAuthContext(user_id=USER_A_ID, selected_tenant_id=None)
        )
    memberships = AsyncMock()
    memberships.get_by_user_and_tenant = AsyncMock(return_value=_active_membership().revoke())
    factory = TenantContextFactory(memberships=memberships, tenants=AsyncMock())
    with pytest.raises(MembershipAccessDeniedError):
        await factory.build_for_gym(
            TrustedGymAuthContext(user_id=USER_A_ID, selected_tenant_id=TENANT_A_ID)
        )
