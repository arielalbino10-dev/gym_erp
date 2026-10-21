"""Catálogo cerrado de permisos operativos gym (MVP H2-C.4)."""

from __future__ import annotations

from enum import StrEnum

GYM_PERMISSION_CATALOG_VERSION = "2026-04-h2c4-mvp"


class GymPermission(StrEnum):
    """Permisos atómicos; el cliente no puede definir strings arbitrarios."""

    BRANCHES_READ = "branches.read"
    BRANCHES_CREATE = "branches.create"
    BRANCHES_UPDATE = "branches.update"
    BRANCHES_DEACTIVATE = "branches.deactivate"
    STAFF_READ = "staff.read"
    TENANT_ROLES_MANAGE = "tenant.roles.manage"


ALL_GYM_PERMISSIONS: frozenset[GymPermission] = frozenset(GymPermission)
