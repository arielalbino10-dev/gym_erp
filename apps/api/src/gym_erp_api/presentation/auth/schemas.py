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
