"""
ACGS-2 Unified Configuration System
Constitutional Hash: cdd01ef066bc6cf2

Uses pydantic-settings for type-safe environment configuration.
"""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, SecretStr, field_validator, model_validator

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    HAS_PYDANTIC_SETTINGS = True
except ImportError:
    HAS_PYDANTIC_SETTINGS = False
    from pydantic import BaseModel as BaseSettings

    class SettingsConfigDict(dict):
        pass


if HAS_PYDANTIC_SETTINGS:

    class RedisSettings(BaseSettings):
        """Redis connection settings."""

        url: str = Field("redis://localhost:6379", validation_alias="REDIS_URL")
        db: int = Field(0, validation_alias="REDIS_DB")
        max_connections: int = Field(10, validation_alias="REDIS_MAX_CONNECTIONS")
        socket_timeout: float = Field(5.0, validation_alias="REDIS_SOCKET_TIMEOUT")
        retry_on_timeout: bool = Field(True, validation_alias="REDIS_RETRY_ON_TIMEOUT")

    class AISettings(BaseSettings):
        """AI Service settings."""

        openrouter_api_key: Optional[SecretStr] = Field(None, validation_alias="OPENROUTER_API_KEY")
        hf_token: Optional[SecretStr] = Field(None, validation_alias="HF_TOKEN")
        openai_api_key: Optional[SecretStr] = Field(None, validation_alias="OPENAI_API_KEY")
        constitutional_hash: str = Field("cdd01ef066bc6cf2", validation_alias="CONSTITUTIONAL_HASH")

    class BlockchainSettings(BaseSettings):
        """Blockchain integration settings."""

        eth_l2_network: str = Field("optimism", validation_alias="ETH_L2_NETWORK")
        eth_rpc_url: str = Field("https://mainnet.optimism.io", validation_alias="ETH_RPC_URL")
        contract_address: Optional[str] = Field(None, validation_alias="AUDIT_CONTRACT_ADDRESS")
        private_key: Optional[SecretStr] = Field(None, validation_alias="BLOCKCHAIN_PRIVATE_KEY")

    class SecuritySettings(BaseSettings):
        """Security and Auth settings."""

        api_key_internal: Optional[SecretStr] = Field(None, validation_alias="API_KEY_INTERNAL")
        cors_origins: List[str] = Field(["*"], validation_alias="CORS_ORIGINS")
        jwt_secret: Optional[SecretStr] = Field(None, validation_alias="JWT_SECRET")
        jwt_public_key: str = Field(
            "SYSTEM_PUBLIC_KEY_PLACEHOLDER", validation_alias="JWT_PUBLIC_KEY"
        )

        @field_validator("jwt_secret", "api_key_internal")
        @classmethod
        def check_no_placeholders(cls, v: Optional[SecretStr]) -> Optional[SecretStr]:
            """Ensure sensitive keys don't use weak placeholders."""
            if v is not None:
                secret_val = v.get_secret_value()
                if secret_val in ["PLACEHOLDER", "CHANGE_ME", "DANGEROUS_DEFAULT"]:
                    raise ValueError("Sensitive credential uses a forbidden placeholder value")
            return v

    class OPASettings(BaseSettings):
        """OPA (Open Policy Agent) settings."""

        url: str = Field("http://localhost:8181", validation_alias="OPA_URL")
        mode: str = Field("http", validation_alias="OPA_MODE")  # http, embedded, fallback
        # SECURITY FIX (VULN-002): OPA is now ALWAYS fail-closed.
        # Parameter removed to prevent insecure overrides.
        fail_closed: bool = True

    class AuditSettings(BaseSettings):
        """Audit Service settings."""

        url: str = Field("http://localhost:8001", validation_alias="AUDIT_SERVICE_URL")

    class BundleSettings(BaseSettings):
        """Policy Bundle settings."""

        registry_url: str = Field("http://localhost:5000", validation_alias="BUNDLE_REGISTRY_URL")
        storage_path: str = Field("./storage/bundles", validation_alias="BUNDLE_STORAGE_PATH")
        s3_bucket: Optional[str] = Field(None, validation_alias="BUNDLE_S3_BUCKET")
        github_webhook_secret: Optional[SecretStr] = Field(
            None, validation_alias="GITHUB_WEBHOOK_SECRET"
        )

    class Settings(BaseSettings):
        """Global Application Settings."""

        model_config = SettingsConfigDict(
            env_file=".env", env_file_encoding="utf-8", extra="ignore"
        )

        env: str = Field("development", validation_alias="APP_ENV")
        debug: bool = Field(False, validation_alias="APP_DEBUG")

        redis: RedisSettings = RedisSettings()
        ai: AISettings = AISettings()
        blockchain: BlockchainSettings = BlockchainSettings()
        security: SecuritySettings = SecuritySettings()
        opa: OPASettings = OPASettings()
        audit: AuditSettings = AuditSettings()
        bundle: BundleSettings = BundleSettings()

        @model_validator(mode="after")
        def validate_production_security(self) -> "Settings":
            """Ensure strict security when running in production."""
            if self.env == "production":
                if not self.security.jwt_secret:
                    raise ValueError("JWT_SECRET is mandatory in production environment")
                if not self.security.api_key_internal:
                    raise ValueError("API_KEY_INTERNAL is mandatory in production environment")
                if self.security.jwt_public_key == "SYSTEM_PUBLIC_KEY_PLACEHOLDER":
                    raise ValueError("JWT_PUBLIC_KEY must be configured in production environment")
            return self

else:
    # Fallback to pure os.getenv for environment mapping
    from dataclasses import dataclass, field

    @dataclass
    class RedisSettings:
        url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379"))
        db: int = field(default_factory=lambda: int(os.getenv("REDIS_DB", "0")))
        max_connections: int = field(
            default_factory=lambda: int(os.getenv("REDIS_MAX_CONNECTIONS", "10"))
        )
        socket_timeout: float = field(
            default_factory=lambda: float(os.getenv("REDIS_SOCKET_TIMEOUT", "5.0"))
        )
        retry_on_timeout: bool = field(
            default_factory=lambda: os.getenv("REDIS_RETRY_ON_TIMEOUT", "true").lower() == "true"
        )

    @dataclass
    class AISettings:
        openrouter_api_key: Optional[SecretStr] = field(
            default_factory=lambda: (
                SecretStr(os.getenv("OPENROUTER_API_KEY", ""))
                if os.getenv("OPENROUTER_API_KEY")
                else None
            )
        )
        hf_token: Optional[SecretStr] = field(
            default_factory=lambda: (
                SecretStr(os.getenv("HF_TOKEN", "")) if os.getenv("HF_TOKEN") else None
            )
        )
        openai_api_key: Optional[SecretStr] = field(
            default_factory=lambda: (
                SecretStr(os.getenv("OPENAI_API_KEY", "")) if os.getenv("OPENAI_API_KEY") else None
            )
        )
        constitutional_hash: str = field(
            default_factory=lambda: os.getenv("CONSTITUTIONAL_HASH", "cdd01ef066bc6cf2")
        )

    @dataclass
    class BlockchainSettings:
        eth_l2_network: str = field(default_factory=lambda: os.getenv("ETH_L2_NETWORK", "optimism"))
        eth_rpc_url: str = field(
            default_factory=lambda: os.getenv("ETH_RPC_URL", "https://mainnet.optimism.io")
        )
        contract_address: Optional[str] = field(
            default_factory=lambda: os.getenv("AUDIT_CONTRACT_ADDRESS")
        )
        private_key: Optional[SecretStr] = field(
            default_factory=lambda: (
                SecretStr(os.getenv("BLOCKCHAIN_PRIVATE_KEY", ""))
                if os.getenv("BLOCKCHAIN_PRIVATE_KEY")
                else None
            )
        )

    @dataclass
    class SecuritySettings:
        api_key_internal: Optional[SecretStr] = field(
            default_factory=lambda: (
                SecretStr(os.getenv("API_KEY_INTERNAL", ""))
                if os.getenv("API_KEY_INTERNAL")
                else None
            )
        )
        cors_origins: List[str] = field(
            default_factory=lambda: os.getenv("CORS_ORIGINS", "*").split(",")
        )
        jwt_secret: Optional[SecretStr] = field(
            default_factory=lambda: (
                SecretStr(os.getenv("JWT_SECRET", "")) if os.getenv("JWT_SECRET") else None
            )
        )
        jwt_public_key: str = field(
            default_factory=lambda: os.getenv("JWT_PUBLIC_KEY", "SYSTEM_PUBLIC_KEY_PLACEHOLDER")
        )
        jwt_private_key: Optional[SecretStr] = field(
            default_factory=lambda: (
                SecretStr(os.getenv("JWT_PRIVATE_KEY", ""))
                if os.getenv("JWT_PRIVATE_KEY")
                else None
            )
        )

    @dataclass
    class OPASettings:
        url: str = field(default_factory=lambda: os.getenv("OPA_URL", "http://localhost:8181"))
        mode: str = field(default_factory=lambda: os.getenv("OPA_MODE", "http"))
        fail_closed: bool = field(
            default_factory=lambda: os.getenv("OPA_FAIL_CLOSED", "true").lower() == "true"
        )

    @dataclass
    class AuditSettings:
        url: str = field(
            default_factory=lambda: os.getenv("AUDIT_SERVICE_URL", "http://localhost:8001")
        )

    @dataclass
    class BundleSettings:
        registry_url: str = field(
            default_factory=lambda: os.getenv("BUNDLE_REGISTRY_URL", "http://localhost:5000")
        )
        storage_path: str = field(
            default_factory=lambda: os.getenv("BUNDLE_STORAGE_PATH", "./storage/bundles")
        )
        s3_bucket: Optional[str] = field(default_factory=lambda: os.getenv("BUNDLE_S3_BUCKET"))
        github_webhook_secret: Optional[SecretStr] = field(
            default_factory=lambda: (
                SecretStr(os.getenv("GITHUB_WEBHOOK_SECRET", ""))
                if os.getenv("GITHUB_WEBHOOK_SECRET")
                else None
            )
        )

    @dataclass
    class Settings:
        env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
        debug: bool = field(
            default_factory=lambda: os.getenv("APP_DEBUG", "false").lower() == "true"
        )

        redis: RedisSettings = field(default_factory=RedisSettings)
        ai: AISettings = field(default_factory=AISettings)
        blockchain: BlockchainSettings = field(default_factory=BlockchainSettings)
        security: SecuritySettings = field(default_factory=SecuritySettings)
        opa: OPASettings = field(default_factory=OPASettings)
        audit: AuditSettings = field(default_factory=AuditSettings)
        bundle: BundleSettings = field(default_factory=BundleSettings)


# Global settings instance
settings = Settings()


@lru_cache()
def get_settings() -> Settings:
    """Returns the global settings instance.

    Uses lru_cache for consistency with FastAPI dependency injection patterns.
    """
    return settings
