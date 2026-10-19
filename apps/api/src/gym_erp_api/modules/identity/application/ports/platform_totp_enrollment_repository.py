from typing import Protocol

from gym_erp_api.modules.identity.domain.platform_mfa.platform_totp_enrollment import (
    PlatformTotpEnrollment,
)


class PlatformTotpEnrollmentRepository(Protocol):
    async def get_by_user_id(self, user_id: str) -> PlatformTotpEnrollment | None: ...

    async def save(self, enrollment: PlatformTotpEnrollment) -> None: ...
