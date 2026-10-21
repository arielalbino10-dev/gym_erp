"""Esquemas HTTP gym — sucursales (H3-B.1)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateBranchRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    timezone: str | None = Field(default=None, max_length=64)
    code: str | None = Field(default=None, max_length=32)


class BranchResponse(BaseModel):
    branch_id: str
    name: str
    status: str
    timezone: str
    code: str | None = None


class BranchListResponse(BaseModel):
    branches: list[BranchResponse]
