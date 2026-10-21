"""Contexto confiable para AuthorizationService (derivado de factory, no HTTP)."""

from __future__ import annotations

from dataclasses import dataclass

from gym_erp_api.modules.access.application.services.tenant_context_factory import (
    ResolvedTenantContext,
)
from gym_erp_api.modules.access.domain.enums import GymRole


@dataclass(frozen=True, slots=True)
class TrustedGymAuthorizationContext:
    user_id: str
    tenant_id: str
    membership_id: str
    authz_epoch: int
    gym_roles: frozenset[GymRole]
    allowed_branch_ids: frozenset[str] | None

    @classmethod
    def from_resolved(cls, resolved: ResolvedTenantContext) -> TrustedGymAuthorizationContext:
        roles = _parse_roles(resolved.gym_roles)
        ctx = resolved.context
        return cls(
            user_id=ctx.user_id,
            tenant_id=ctx.tenant_id,
            membership_id=ctx.membership_id,
            authz_epoch=resolved.authz_epoch,
            gym_roles=roles,
            allowed_branch_ids=ctx.allowed_branch_ids,
        )


def _parse_roles(raw: frozenset[str]) -> frozenset[GymRole]:
    parsed: set[GymRole] = set()
    for value in raw:
        try:
            parsed.add(GymRole(value))
        except ValueError as exc:
            raise ValueError(f"Rol gym desconocido: {value!r}.") from exc
    if not parsed:
        raise ValueError("Membresía sin roles gym reconocidos.")
    return frozenset(parsed)
