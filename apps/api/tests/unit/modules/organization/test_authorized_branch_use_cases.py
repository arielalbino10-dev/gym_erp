"""Casos de uso sucursales autorizadas (H3-B.1)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from gym_erp_api.modules.access.application.authorization.gym_authorization_service import (
    GymAuthorizationService,
)
from gym_erp_api.modules.access.application.services.tenant_context_factory import (
    ResolvedTenantContext,
)
from gym_erp_api.modules.access.domain.enums import GymRole
from gym_erp_api.modules.organization.application.commands.gym_branch_commands import (
    CreateAuthorizedBranchCommand,
)
from gym_erp_api.modules.organization.application.errors import BranchNotFoundApplicationError
from gym_erp_api.modules.organization.application.use_cases.create_authorized_branch import (
    CreateAuthorizedBranchUseCase,
)
from gym_erp_api.modules.organization.application.use_cases.get_authorized_branch import (
    GetAuthorizedBranchUseCase,
)
from gym_erp_api.modules.organization.application.use_cases.list_authorized_branches import (
    ListAuthorizedBranchesUseCase,
)
from gym_erp_api.modules.organization.domain.branch import Branch
from gym_erp_api.shared_kernel.tenant_context import TenantContext
from tests.support.tenant_fixtures import (
    BRANCH_X_ID,
    MEMBERSHIP_A_ID,
    TENANT_A_ID,
    TENANT_B_ID,
    USER_A_ID,
)

_MOMENT = datetime(2026, 12, 10, tzinfo=UTC)


def _tenant_ctx(*, allowed: frozenset[str] | None = None) -> ResolvedTenantContext:
    return ResolvedTenantContext(
        context=TenantContext(
            tenant_id=TENANT_A_ID,
            user_id=USER_A_ID,
            membership_id=MEMBERSHIP_A_ID,
            allowed_branch_ids=allowed,
        ),
        authz_epoch=1,
        gym_roles=frozenset({GymRole.GYM_OWNER.value}),
    )


@pytest.mark.asyncio
async def test_create_branch_persists_via_repository():
    authz = GymAuthorizationService()
    repo = MagicMock()
    repo.insert = AsyncMock()
    factory = MagicMock()
    factory.for_context.return_value = repo
    use_case = CreateAuthorizedBranchUseCase(
        authorization=authz,
        branch_repository_factory=factory,
        id_generator=lambda: BRANCH_X_ID,
        clock=lambda: _MOMENT,
    )
    result = await use_case.execute(
        tenant=_tenant_ctx(),
        command=CreateAuthorizedBranchCommand(name="Centro"),
    )
    assert result.branch_id == BRANCH_X_ID
    repo.insert.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_branch_not_found():
    authz = GymAuthorizationService()
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=None)
    factory = MagicMock()
    factory.for_context.return_value = repo
    use_case = GetAuthorizedBranchUseCase(
        authorization=authz,
        branch_repository_factory=factory,
    )
    with pytest.raises(BranchNotFoundApplicationError):
        await use_case.execute(tenant=_tenant_ctx(), branch_id=BRANCH_X_ID)


@pytest.mark.asyncio
async def test_list_scoped_to_explicit_branches():
    authz = GymAuthorizationService()
    branch = Branch.create(
        tenant_id=TENANT_A_ID,
        name="X",
        branch_id=BRANCH_X_ID,
        now=_MOMENT,
    )
    repo = MagicMock()
    repo.list_branches = AsyncMock(return_value=[branch])
    factory = MagicMock()
    factory.for_context.return_value = repo
    use_case = ListAuthorizedBranchesUseCase(
        authorization=authz,
        branch_repository_factory=factory,
    )
    rows = await use_case.execute(
        tenant=_tenant_ctx(allowed=frozenset({BRANCH_X_ID})),
    )
    assert len(rows) == 1
    factory.for_context.assert_called_once()
    assert factory.for_context.call_args[0][0].tenant_id == TENANT_A_ID
    assert factory.for_context.call_args[0][0].tenant_id != TENANT_B_ID
