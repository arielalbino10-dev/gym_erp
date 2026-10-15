"""Puerto de persistencia de sucursales (operational scoped)."""

from typing import Protocol

from gym_erp_api.modules.organization.domain.branch import Branch
from gym_erp_api.modules.organization.domain.enums import BranchStatus


class BranchRepository(Protocol):
    async def insert(self, branch: Branch, *, session: object | None = None) -> None: ...

    async def get_by_id(
        self, branch_id: str, *, session: object | None = None
    ) -> Branch | None: ...

    async def list_branches(
        self,
        *,
        status: BranchStatus | None = None,
        session: object | None = None,
    ) -> list[Branch]: ...

    async def save(self, branch: Branch, *, session: object | None = None) -> None: ...
