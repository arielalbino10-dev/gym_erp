"""Superficie de sesión (ADR-0003)."""

from enum import StrEnum


class SessionKind(StrEnum):
    PLATFORM = "platform"
    GYM = "gym"
