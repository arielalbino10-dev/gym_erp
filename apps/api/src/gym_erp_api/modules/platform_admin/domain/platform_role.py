"""Roles administrativos de la plataforma Gym ERP."""

from __future__ import annotations

from enum import StrEnum


class PlatformRole(StrEnum):
    ROOT_ADMIN = "root_admin"
    PLATFORM_ADMIN = "platform_admin"


ALL_PLATFORM_ROLES: frozenset[PlatformRole] = frozenset(PlatformRole)
