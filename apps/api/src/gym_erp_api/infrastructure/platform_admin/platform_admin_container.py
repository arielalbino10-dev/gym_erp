"""Composición servicios administración platform."""

from __future__ import annotations

from dataclasses import dataclass

from pymongo.asynchronous.database import AsyncDatabase

from gym_erp_api.modules.platform_admin.application.services.platform_authorization_service import (
    PlatformAuthorizationService,
)
from gym_erp_api.modules.platform_admin.application.use_cases.apply_platform_role_assignment import (  # noqa: E501
    ApplyPlatformRoleAssignmentUseCase,
)
from gym_erp_api.modules.platform_admin.application.use_cases.record_platform_audit_event import (
    RecordPlatformAuditEventUseCase,
)
from gym_erp_api.modules.platform_admin.infrastructure.mongo.mongo_platform_audit_repository import (  # noqa: E501
    MongoPlatformAuditRepository,
)
from gym_erp_api.modules.platform_admin.infrastructure.mongo.mongo_platform_role_assignment_repository import (  # noqa: E501
    MongoPlatformRoleAssignmentRepository,
)
from gym_erp_api.modules.platform_admin.infrastructure.mongo.platform_audit_mapper import (
    PLATFORM_AUDIT_EVENTS_COLLECTION,
)
from gym_erp_api.modules.platform_admin.infrastructure.mongo.platform_role_assignment_mapper import (  # noqa: E501
    PLATFORM_ROLE_ASSIGNMENTS_COLLECTION,
)


@dataclass(frozen=True, slots=True)
class PlatformAdminInfrastructure:
    platform_authorization_service: PlatformAuthorizationService
    platform_role_assignment_repository: MongoPlatformRoleAssignmentRepository
    record_platform_audit_event: RecordPlatformAuditEventUseCase
    apply_platform_role_assignment: ApplyPlatformRoleAssignmentUseCase


def build_platform_admin_infrastructure(platform_db: AsyncDatabase) -> PlatformAdminInfrastructure:
    assignments = MongoPlatformRoleAssignmentRepository(
        platform_db[PLATFORM_ROLE_ASSIGNMENTS_COLLECTION],
    )
    audit_repo = MongoPlatformAuditRepository(platform_db[PLATFORM_AUDIT_EVENTS_COLLECTION])
    authz = PlatformAuthorizationService(assignments=assignments)
    record_audit = RecordPlatformAuditEventUseCase(audit=audit_repo)
    apply_assignment = ApplyPlatformRoleAssignmentUseCase(
        assignments=assignments,
        authorization=authz,
        audit=record_audit,
    )
    return PlatformAdminInfrastructure(
        platform_authorization_service=authz,
        platform_role_assignment_repository=assignments,
        record_platform_audit_event=record_audit,
        apply_platform_role_assignment=apply_assignment,
    )
