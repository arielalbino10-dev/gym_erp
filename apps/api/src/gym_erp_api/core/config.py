from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr, field_validator, model_validator
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

    platform_mfa_encryption_key: SecretStr | None = Field(
        default=None,
        alias="MFA_PLATFORM_ENCRYPTION_KEY",
    )
    platform_mfa_encryption_key_version: int = Field(
        default=1,
        ge=1,
        alias="MFA_PLATFORM_ENCRYPTION_KEY_VERSION",
    )
    platform_mfa_encryption_required: bool | None = Field(
        default=None,
        alias="PLATFORM_MFA_ENCRYPTION_REQUIRED",
    )

    trusted_proxy_ips: str = Field(default="127.0.0.1", alias="TRUSTED_PROXY_IPS")
    rate_limit_fail_closed: bool = Field(default=True, alias="RATE_LIMIT_FAIL_CLOSED")
    allow_insecure_cookies: bool = Field(default=True, alias="ALLOW_INSECURE_COOKIES")
    require_https_env: bool | None = Field(default=None, alias="REQUIRE_HTTPS")

    @property
    def https_required(self) -> bool:
        if self.require_https_env is not None:
            return self.require_https_env
        return self.app_env.strip().lower() == "production"

    @property
    def require_platform_mfa_encryption_key(self) -> bool:
        if self.platform_mfa_encryption_required is not None:
            return self.platform_mfa_encryption_required
        return self.app_env.strip().lower() == "production"

    @field_validator("app_env")
    @classmethod
    def normalize_app_env(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = frozenset({"development", "test", "staging", "production"})
        if normalized not in allowed:
            raise ValueError(
                f"APP_ENV inválido: {value!r}. Valores permitidos: {sorted(allowed)!r}."
            )
        return normalized

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

    @model_validator(mode="after")
    def validate_production_http_security(self) -> Settings:
        for origin in self.cors_origin_list:
            stripped = origin.strip()
            if stripped == "*" or "*" in stripped:
                raise ValueError("CORS_ORIGINS no puede contener comodines con allow_credentials.")

        if self.app_env != "production":
            return self

        if self.allow_insecure_cookies:
            raise ValueError(
                "ALLOW_INSECURE_COOKIES no puede estar activo cuando APP_ENV=production."
            )
        if self.require_https_env is False:
            raise ValueError("REQUIRE_HTTPS no puede ser false en production.")
        if not self.rate_limit_fail_closed:
            raise ValueError("RATE_LIMIT_FAIL_CLOSED debe ser true en production.")
        if self.platform_mfa_encryption_required is False:
            raise ValueError("PLATFORM_MFA_ENCRYPTION_REQUIRED no puede ser false en production.")
        if not self.trusted_proxy_ips.strip():
            raise ValueError("TRUSTED_PROXY_IPS debe configurarse explícitamente en production.")

        from urllib.parse import urlparse

        for origin in self.cors_origin_list:
            parsed = urlparse(origin)
            host = (parsed.hostname or "").lower()
            if parsed.scheme != "https":
                raise ValueError("CORS_ORIGINS en production debe usar https://.")
            if host in {"localhost", "127.0.0.1"} or host.endswith(".local"):
                raise ValueError(
                    "CORS_ORIGINS en production no puede apuntar a localhost ni hosts .local."
                )
        return self

    @model_validator(mode="after")
    def validate_platform_mfa_key_when_required(self) -> Settings:
        from gym_erp_api.core.platform_mfa_crypto import resolve_platform_mfa_aes256_key

        if self.require_platform_mfa_encryption_key or self.platform_mfa_encryption_key is not None:
            resolve_platform_mfa_aes256_key(self)
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
