"""Factory de BranchRepository scoped al TenantContext confiable (gym HTTP)."""

from typing import Protocol

from gym_erp_api.modules.organization.application.ports.branch_repository import BranchRepository
from gym_erp_api.shared_kernel.tenant_context import TenantContext


class TenantContextBranchRepositoryFactory(Protocol):
    def for_context(self, context: TenantContext) -> BranchRepository: ...
