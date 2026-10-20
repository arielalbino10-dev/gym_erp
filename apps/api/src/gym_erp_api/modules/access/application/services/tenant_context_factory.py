"""Construye TenantContext confiable desde auth + membresía platform."""

from __future__ import annotations

from dataclasses import dataclass

from gym_erp_api.modules.access.application.dto.trusted_auth import TrustedGymAuthContext
from gym_erp_api.modules.access.application.errors import (
    MembershipAccessDeniedError,
    MembershipNotFoundError,
    TenantNotSelectedError,
)
from gym_erp_api.modules.access.application.ports.membership_repository import MembershipRepository
from gym_erp_api.modules.access.domain.enums import BranchScopeMode, MembershipStatus
from gym_erp_api.modules.organization.application.errors import (
    TenantNotActiveApplicationError,
    TenantNotFoundApplicationError,
    TenantSuspendedApplicationError,
)
from gym_erp_api.modules.organization.application.policies.tenant_operational import (
    TenantOperationalPolicy,
)
from gym_erp_api.modules.organization.application.ports.tenant_repository import TenantRepository
from gym_erp_api.shared_kernel.tenant_context import TenantContext


@dataclass(frozen=True, slots=True)
class ResolvedTenantContext:
    """TenantContext más metadatos de authz para H2-C.3 (epoch, roles)."""

    context: TenantContext
    authz_epoch: int
    gym_roles: frozenset[str]


class TenantContextFactory:
    """No interpreta roles ni tenant_id del cliente; solo TrustedGymAuthContext + Mongo."""

    def __init__(
        self,
        *,
        memberships: MembershipRepository,
        tenants: TenantRepository,
    ) -> None:
        self._memberships = memberships
        self._tenants = tenants

    async def build_for_gym(
        self,
        auth: TrustedGymAuthContext,
        *,
        session: object | None = None,
    ) -> ResolvedTenantContext:
        if auth.selected_tenant_id is None:
            raise TenantNotSelectedError("No hay tenant seleccionado en la sesión gym autenticada.")

        membership = await self._memberships.get_by_user_and_tenant(
            user_id=auth.user_id,
            tenant_id=auth.selected_tenant_id,
            session=session,
        )
        if membership is None:
            raise MembershipNotFoundError(
                "No existe membresía para el usuario y tenant solicitados."
            )
        if membership.user_id != auth.user_id or membership.tenant_id != auth.selected_tenant_id:
            raise MembershipAccessDeniedError("Membresía inconsistente con identidad confiable.")

        if membership.status is MembershipStatus.SUSPENDED:
            raise MembershipAccessDeniedError("Membresía suspendida.")
        if membership.status is MembershipStatus.REVOKED:
            raise MembershipAccessDeniedError("Membresía revocada.")
        if membership.status is MembershipStatus.INVITED:
            raise MembershipAccessDeniedError("Membresía aún no aceptada.")
        if membership.status is not MembershipStatus.ACTIVE:
            raise MembershipAccessDeniedError("Membresía no operativa.")

        tenant = await self._tenants.get_by_id(auth.selected_tenant_id, session=session)
        try:
            TenantOperationalPolicy.ensure_allows_operational(tenant)
        except TenantNotFoundApplicationError as exc:
            raise MembershipAccessDeniedError("Tenant no encontrado.") from exc
        except TenantSuspendedApplicationError as exc:
            raise MembershipAccessDeniedError("Tenant suspendido.") from exc
        except TenantNotActiveApplicationError as exc:
            raise MembershipAccessDeniedError("Tenant no activo para operación.") from exc

        allowed = membership.context_allowed_branch_ids()
        if (
            membership.branch_scope_mode is BranchScopeMode.EXPLICIT_BRANCHES
            and allowed is not None
            and len(allowed) == 0
        ):
            raise MembershipAccessDeniedError(
                "Alcance de sucursales vacío; operaciones branch-scoped denegadas."
            )

        context = TenantContext(
            tenant_id=membership.tenant_id,
            user_id=membership.user_id,
            membership_id=membership.membership_id,
            allowed_branch_ids=allowed,
        )
        role_values = frozenset(role.value for role in membership.gym_roles)
        return ResolvedTenantContext(
            context=context,
            authz_epoch=membership.authz_epoch,
            gym_roles=role_values,
        )
