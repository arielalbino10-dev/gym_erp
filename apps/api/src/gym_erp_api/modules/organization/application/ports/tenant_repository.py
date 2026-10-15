"""Puerto de persistencia de tenants (platform)."""

from typing import Protocol

from gym_erp_api.modules.organization.domain.tenant import Tenant


class TenantRepository(Protocol):
    async def insert(self, tenant: Tenant, *, session: object | None = None) -> None: ...

    async def get_by_id(
        self, tenant_id: str, *, session: object | None = None
    ) -> Tenant | None: ...

    async def exists_by_id(self, tenant_id: str, *, session: object | None = None) -> bool: ...

    async def save(self, tenant: Tenant, *, session: object | None = None) -> None: ...
