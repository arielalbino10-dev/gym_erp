"""Comprueba elegibilidad platform antes de continuación MFA o sesión."""

from __future__ import annotations

from gym_erp_api.modules.identity.application.errors import AuthenticationFailedError
from gym_erp_api.modules.identity.application.ports.platform_operator_eligibility_repository import (  # noqa: E501
    PlatformOperatorEligibilityRepository,
)

_GENERIC = "Credenciales inválidas."


class PlatformSessionEligibilityService:
    def __init__(self, *, eligibility: PlatformOperatorEligibilityRepository) -> None:
        self._eligibility = eligibility

    async def require_eligible_operator(self, *, user_id: str) -> None:
        if not await self._eligibility.is_eligible(user_id=user_id):
            raise AuthenticationFailedError(_GENERIC)
