from enum import StrEnum


class TotpEnrollmentStatus(StrEnum):
    PENDING = "pending"
    ENABLED = "enabled"
    DISABLED = "disabled"
