"""Comandos gym operational sucursales (H3-B.1)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreateAuthorizedBranchCommand:
    name: str
    timezone: str | None = None
    code: str | None = None
