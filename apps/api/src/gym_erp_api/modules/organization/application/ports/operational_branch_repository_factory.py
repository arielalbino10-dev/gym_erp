"""Factory de repositorio operational scoped para un tenant recién provisionado."""

from typing import Protocol

from gym_erp_api.modules.organization.application.ports.branch_repository import BranchRepository


class OperationalBranchRepositoryFactory(Protocol):
    def for_provisioned_tenant(
        self,
        *,
        tenant_id: str,
        allowed_branch_id: str,
        actor_user_id: str,
        actor_membership_id: str,
    ) -> BranchRepository:
        """Repositorio con ``allowed_branch_ids={allowed_branch_id}`` (sin bypass de scope)."""
        ...
