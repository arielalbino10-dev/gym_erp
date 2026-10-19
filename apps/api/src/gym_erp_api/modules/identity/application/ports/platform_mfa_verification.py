"""Puerto MFA platform (implementación real en H2-B.5; no bypass por query/body)."""

from typing import Protocol

from gym_erp_api.modules.identity.application.dto.platform_mfa import PlatformMfaVerificationTicket


class PlatformMfaVerificationPort(Protocol):
    async def issue_verification_ticket(self, user_id: str) -> PlatformMfaVerificationTicket:
        """Emite ticket solo tras verificación MFA real (TOTP/WebAuthn futuro)."""
