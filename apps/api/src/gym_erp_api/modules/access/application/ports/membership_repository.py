"""Puerto de persistencia de membresías tenant (platform)."""

from __future__ import annotations

from typing import Protocol

from gym_erp_api.modules.access.domain.tenant_membership import TenantMembership


class MembershipRepository(Protocol):
    async def insert(
        self,
        membership: TenantMembership,
        *,
        session: object | None = None,
    ) -> None: ...

    async def get_by_id(
        self,
        membership_id: str,
        *,
        session: object | None = None,
    ) -> TenantMembership | None: ...

    async def get_by_user_and_tenant(
        self,
        *,
        user_id: str,
        tenant_id: str,
        session: object | None = None,
    ) -> TenantMembership | None: ...

    async def list_active_by_user_id(
        self,
        user_id: str,
        *,
        session: object | None = None,
    ) -> tuple[TenantMembership, ...]: ...

    async def save(
        self,
        membership: TenantMembership,
        *,
        expected_authz_epoch: int,
        session: object | None = None,
    ) -> None: ...
