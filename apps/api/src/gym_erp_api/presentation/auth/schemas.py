"""Esquemas HTTP auth (sin tokens ni secretos)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class MfaVerifyRequest(BaseModel):
    totp_code: str = Field(min_length=1, max_length=32)


class SessionResponse(BaseModel):
    user_id: str
    session_kind: str
    active_tenant_id: str | None = None
    membership_id: str | None = None
    gym_roles: list[str] | None = None
    tenant_display_name: str | None = None


class GymMembershipItem(BaseModel):
    tenant_id: str
    membership_id: str
    display_name: str
    gym_roles: list[str]


class GymMembershipsResponse(BaseModel):
    memberships: list[GymMembershipItem]


class SelectTenantRequest(BaseModel):
    tenant_id: str = Field(min_length=36, max_length=36)
