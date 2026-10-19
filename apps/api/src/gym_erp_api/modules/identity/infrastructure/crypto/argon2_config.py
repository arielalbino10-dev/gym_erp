"""Parámetros Argon2id (ADR-0003). Ajustar tras benchmark en hardware objetivo."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Argon2PasswordConfig:
    """Valores iniciales documentados en ADR-0003 / identity-module.md."""

    time_cost: int = 3
    memory_cost_kib: int = 65536
    parallelism: int = 4
    hash_len: int = 32
    salt_len: int = 16
    max_time_cost: int = 10
    max_memory_cost_kib: int = 262144
    max_parallelism: int = 8

    def __post_init__(self) -> None:
        if self.time_cost < 1:
            raise ValueError("time_cost debe ser >= 1.")
        if self.memory_cost_kib < 8192:
            raise ValueError("memory_cost_kib demasiado bajo para producción.")
        if self.parallelism < 1:
            raise ValueError("parallelism debe ser >= 1.")
