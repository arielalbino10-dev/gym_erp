"""Repositorio operational de sucursales sobre TenantScopedRepository."""

from __future__ import annotations

from typing import Any

from gym_erp_api.infrastructure.mongo.scoped_repository import TenantScopedRepository
from gym_erp_api.modules.organization.domain.branch import Branch
from gym_erp_api.modules.organization.domain.enums import BranchStatus
from gym_erp_api.modules.organization.domain.errors import (
    InvalidOrganizationFieldError,
    OrganizationEntityNotFoundError,
)
from gym_erp_api.modules.organization.domain.validators import require_uuid_v4
from gym_erp_api.modules.organization.infrastructure.mongo.branch_document_mapper import (
    branch_from_document,
    branch_to_document,
)


class OperationalBranchRepository:
    """Persistencia de branches con aislamiento obligatorio por tenant."""

    def __init__(self, scoped: TenantScopedRepository) -> None:
        self._scoped = scoped

    @property
    def tenant_id(self) -> str:
        return self._scoped.context.tenant_id

    def _assert_branch_belongs_to_context(self, branch: Branch) -> None:
        if branch.tenant_id != self._scoped.context.tenant_id:
            raise InvalidOrganizationFieldError(
                "tenant_id de la sucursal no coincide con el TenantContext."
            )

    def _assert_branch_id_allowed_for_context(self, branch_id: str) -> None:
        allowed = self._scoped.context.allowed_branch_ids
        if allowed is not None and branch_id not in allowed:
            raise InvalidOrganizationFieldError(
                "branch_id fuera del alcance permitido por el TenantContext."
            )

    def _list_user_filter(self, user_filter: dict[str, Any]) -> dict[str, Any]:
        allowed = self._scoped.context.allowed_branch_ids
        if allowed is None:
            return user_filter
        if "branch_id" in user_filter:
            raise InvalidOrganizationFieldError(
                "No combine filtros branch_id con restricción de sucursales del contexto."
            )
        if self._scoped.branch_scoped:
            return user_filter
        branch_clause: dict[str, Any] = {"$in": sorted(allowed)}
        return {**user_filter, "branch_id": branch_clause}

    async def insert(self, branch: Branch, *, session: object | None = None) -> None:
        self._assert_branch_belongs_to_context(branch)
        require_uuid_v4(branch.branch_id, "branch_id")
        self._assert_branch_id_allowed_for_context(branch.branch_id)
        await self._scoped.insert_one(branch_to_document(branch), session=session)

    async def get_by_id(self, branch_id: str, *, session: object | None = None) -> Branch | None:
        bid = require_uuid_v4(branch_id, "branch_id")
        allowed = self._scoped.context.allowed_branch_ids
        if allowed is not None and bid not in allowed:
            return None
        raw = await self._scoped.find_one_by_branch_id(bid, session=session)
        if raw is None:
            return None
        return branch_from_document(raw)

    async def list_branches(
        self,
        *,
        status: BranchStatus | None = None,
        session: object | None = None,
    ) -> list[Branch]:
        user_filter: dict[str, Any] = {}
        if status is not None:
            user_filter["status"] = status.value
        cursor = self._scoped.find(self._list_user_filter(user_filter), session=session)
        branches: list[Branch] = []
        async for raw in cursor:
            branches.append(branch_from_document(raw))
        return branches

    async def save(self, branch: Branch, *, session: object | None = None) -> None:
        self._assert_branch_belongs_to_context(branch)
        bid = require_uuid_v4(branch.branch_id, "branch_id")
        self._assert_branch_id_allowed_for_context(bid)
        doc = branch_to_document(branch)
        update_fields = {
            key: value for key, value in doc.items() if key not in {"_id", "branch_id", "tenant_id"}
        }
        result = await self._scoped.update_one_by_branch_id(
            bid,
            {"$set": update_fields},
            session=session,
        )
        if result.matched_count == 0:
            raise OrganizationEntityNotFoundError(f"Sucursal no encontrada: {bid}.")
