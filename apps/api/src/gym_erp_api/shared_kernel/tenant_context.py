"""Contexto de tenant confiable por unidad de trabajo (no implica autenticación HTTP)."""

from dataclasses import dataclass

from gym_erp_api.shared_kernel.identifiers import assert_uuid_v4


@dataclass(frozen=True, slots=True)
class TenantContext:
    """Contexto inmutable. Un contexto válido no equivale a identidad autenticada."""

    tenant_id: str
    user_id: str
    membership_id: str
    allowed_branch_ids: frozenset[str] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "tenant_id", assert_uuid_v4(self.tenant_id, "tenant_id"))
        object.__setattr__(self, "user_id", assert_uuid_v4(self.user_id, "user_id"))
        object.__setattr__(
            self,
            "membership_id",
            assert_uuid_v4(self.membership_id, "membership_id"),
        )
        if self.allowed_branch_ids is not None:
            normalized = frozenset(
                assert_uuid_v4(branch_id, "branch_id") for branch_id in self.allowed_branch_ids
            )
            object.__setattr__(self, "allowed_branch_ids", normalized)
