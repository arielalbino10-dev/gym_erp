"""Control explícito de emisión de sesiones platform (H2-B.4.1).

Hasta H2-B.5 no existe MFA verificable; la composición en producción debe usar
``HardDisabledPlatformSessionEmission``.
"""

from typing import Protocol


class PlatformSessionEmissionGate(Protocol):
    def assert_emission_allowed(self) -> None:
        """Lanza si la emisión platform no está autorizada en este entorno."""


class HardDisabledPlatformSessionEmission:
    """Bloqueo por defecto: ninguna sesión platform, aunque exista un ticket fabricado."""

    def assert_emission_allowed(self) -> None:
        from gym_erp_api.modules.identity.application.errors import (
            PlatformSessionEmissionDisabledError,
        )

        raise PlatformSessionEmissionDisabledError(
            "Emisión de sesiones platform deshabilitada hasta MFA verificable (H2-B.5)."
        )
