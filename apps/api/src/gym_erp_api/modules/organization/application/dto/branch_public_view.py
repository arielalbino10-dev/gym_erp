"""Representación pública mínima de sucursal (HTTP gym)."""

from __future__ import annotations

from dataclasses import dataclass

from gym_erp_api.modules.organization.domain.branch import Branch


@dataclass(frozen=True, slots=True)
class BranchPublicView:
    branch_id: str
    name: str
    status: str
    timezone: str
    code: str | None

    @classmethod
    def from_branch(cls, branch: Branch) -> BranchPublicView:
        return cls(
            branch_id=branch.branch_id,
            name=branch.name,
            status=branch.status.value,
            timezone=branch.timezone,
            code=branch.code,
        )
