"""Identificadores UUID v4 (string canónico minúsculas)."""

import uuid

from gym_erp_api.shared_kernel.exceptions import InvalidTenantContextError


def new_uuid() -> str:
    return str(uuid.uuid4())


def is_valid_uuid_v4(value: str) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = uuid.UUID(value)
    except ValueError:
        return False
    return parsed.version == 4


def assert_uuid_v4(value: str, field_name: str) -> str:
    if not is_valid_uuid_v4(value):
        raise InvalidTenantContextError(f"{field_name} debe ser un UUID v4 válido.")
    canonical = str(uuid.UUID(value))
    if value != canonical:
        raise InvalidTenantContextError(
            f"{field_name} debe estar en forma canónica (minúsculas con guiones)."
        )
    return canonical
