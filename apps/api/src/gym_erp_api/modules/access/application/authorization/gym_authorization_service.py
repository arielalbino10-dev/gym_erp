"""Autorización operativa gym por permiso + alcance (H2-C.4)."""

from __future__ import annotations

from gym_erp_api.modules.access.application.authorization.role_permission_matrix import (
    PERMISSIONS_REQUIRING_BRANCH_TARGET_FOR_EXPLICIT_SCOPE,
    effective_permissions_for_roles,
)
from gym_erp_api.modules.access.application.authorization.trusted_gym_authorization import (
    TrustedGymAuthorizationContext,
)
from gym_erp_api.modules.access.application.errors import PermissionDeniedError
from gym_erp_api.modules.access.application.services.tenant_context_factory import (
    ResolvedTenantContext,
)
from gym_erp_api.modules.access.domain.gym_permission import GymPermission
from gym_erp_api.modules.organization.application.authorization.tenant_member import (
    TenantMemberAccess,
)
from gym_erp_api.modules.organization.application.errors import (
    BranchAccessDeniedApplicationError,
    TenantAccessDeniedApplicationError,
)


class GymAuthorizationService:
    """Calcula permisos desde roles persistidos; no acepta roles del cliente."""

    def trusted_context_from_resolved(
        self,
        resolved: ResolvedTenantContext,
    ) -> TrustedGymAuthorizationContext:
        try:
            return TrustedGymAuthorizationContext.from_resolved(resolved)
        except ValueError as exc:
            raise PermissionDeniedError(str(exc)) from exc

    def effective_permissions(
        self,
        auth: TrustedGymAuthorizationContext,
    ) -> frozenset[GymPermission]:
        return effective_permissions_for_roles(auth.gym_roles)

    def require_permission(
        self,
        *,
        auth: TrustedGymAuthorizationContext,
        permission: GymPermission,
        branch_id: str | None = None,
        requested_tenant_id: str | None = None,
    ) -> None:
        if requested_tenant_id is not None:
            member = TenantMemberAccess.bind(
                _tenant_context_from_auth(auth),
            )
            try:
                member.require_matching_tenant(requested_tenant_id)
            except TenantAccessDeniedApplicationError as exc:
                raise PermissionDeniedError("Tenant no autorizado.") from exc

        effective = self.effective_permissions(auth)
        if permission not in effective:
            raise PermissionDeniedError("Permiso no concedido para este rol.")

        member = TenantMemberAccess.bind(_tenant_context_from_auth(auth))
        if branch_id is not None:
            try:
                member.require_branch_in_scope(branch_id)
            except BranchAccessDeniedApplicationError as exc:
                raise PermissionDeniedError("Sucursal fuera de alcance.") from exc
        elif (
            auth.allowed_branch_ids is not None
            and permission in PERMISSIONS_REQUIRING_BRANCH_TARGET_FOR_EXPLICIT_SCOPE
        ):
            raise PermissionDeniedError(
                "Debe indicar sucursal objetivo dentro de su alcance autorizado."
            )


def _tenant_context_from_auth(auth: TrustedGymAuthorizationContext):
    from gym_erp_api.shared_kernel.tenant_context import TenantContext

    return TenantContext(
        tenant_id=auth.tenant_id,
        user_id=auth.user_id,
        membership_id=auth.membership_id,
        allowed_branch_ids=auth.allowed_branch_ids,
    )
