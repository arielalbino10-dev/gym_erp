from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    api_host: str = Field(default="127.0.0.1", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")

    mongodb_uri: SecretStr | None = Field(default=None, alias="MONGODB_URI")
    mongodb_platform_db: str = Field(default="gym_platform", alias="MONGODB_PLATFORM_DB")
    mongodb_operational_db: str = Field(
        default="gym_operational",
        alias="MONGODB_OPERATIONAL_DB",
    )
    mongodb_ping_timeout_ms: int = Field(default=2000, alias="MONGODB_PING_TIMEOUT_MS")

    cors_origins: str = Field(
        default="http://127.0.0.1:5173,http://localhost:5173",
        alias="CORS_ORIGINS",
    )

    @model_validator(mode="after")
    def validate_mongodb_database_names(self) -> Settings:
        platform = self.mongodb_platform_db.strip()
        operational = self.mongodb_operational_db.strip()
        if not platform or not operational:
            raise ValueError("Los nombres de base MongoDB no pueden estar vacíos.")
        if platform.casefold() == operational.casefold():
            raise ValueError("MONGODB_PLATFORM_DB y MONGODB_OPERATIONAL_DB deben ser distintos.")
        reserved = frozenset({"admin", "local", "config"})
        for name in (platform, operational):
            if len(name.encode("utf-8")) > 63:
                raise ValueError("Nombre de base MongoDB demasiado largo.")
            if any(char in name for char in ("/", "\\", "\0", " ", ".", '"', "$")):
                raise ValueError("Nombre de base MongoDB inválido.")
            if name.casefold() in reserved:
                raise ValueError("Nombre de base MongoDB reservado.")
        object.__setattr__(self, "mongodb_platform_db", platform)
        object.__setattr__(self, "mongodb_operational_db", operational)
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
