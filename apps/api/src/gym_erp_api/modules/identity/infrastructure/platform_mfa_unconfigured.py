"""Implementación placeholder: MFA platform no disponible en H2-B.4."""

from __future__ import annotations

from gym_erp_api.modules.identity.application.dto.platform_mfa import PlatformMfaVerificationTicket
from gym_erp_api.modules.identity.application.errors import PlatformMfaNotConfiguredError
from gym_erp_api.modules.identity.application.ports.platform_mfa_verification import (
    PlatformMfaVerificationPort,
)


class UnconfiguredPlatformMfaVerification(PlatformMfaVerificationPort):
    async def issue_verification_ticket(self, user_id: str) -> PlatformMfaVerificationTicket:
        raise PlatformMfaNotConfiguredError(
            "MFA platform no configurado; sesión platform no disponible (H2-B.5)."
        )
