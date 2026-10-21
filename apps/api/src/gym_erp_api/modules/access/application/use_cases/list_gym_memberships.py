"""Lista membresías gym activas del usuario autenticado (platform)."""

from __future__ import annotations

from dataclasses import dataclass

from gym_erp_api.modules.access.application.ports.membership_repository import MembershipRepository
from gym_erp_api.modules.access.domain.enums import GymRole
from gym_erp_api.modules.organization.application.ports.tenant_repository import TenantRepository


@dataclass(frozen=True, slots=True)
class GymMembershipSummary:
    tenant_id: str
    membership_id: str
    display_name: str
    gym_roles: frozenset[str]


class ListGymMembershipsForUserUseCase:
    def __init__(
        self,
        *,
        memberships: MembershipRepository,
        tenants: TenantRepository,
    ) -> None:
        self._memberships = memberships
        self._tenants = tenants

    async def execute(self, *, user_id: str) -> tuple[GymMembershipSummary, ...]:
        rows = await self._memberships.list_active_by_user_id(user_id)
        summaries: list[GymMembershipSummary] = []
        for row in rows:
            tenant = await self._tenants.get_by_id(row.tenant_id)
            display = tenant.display_name if tenant is not None else "Gimnasio"
            roles = frozenset(GymRole(r).value for r in row.gym_roles)
            summaries.append(
                GymMembershipSummary(
                    tenant_id=row.tenant_id,
                    membership_id=row.membership_id,
                    display_name=display,
                    gym_roles=roles,
                )
            )
        return tuple(summaries)
