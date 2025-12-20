"""
ACGS-2 Unified Configuration System
Constitutional Hash: cdd01ef066bc6cf2

Uses pydantic-settings for type-safe environment configuration.
"""

import os
from typing import List, Optional
from pydantic import Field, SecretStr

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    HAS_PYDANTIC_SETTINGS = True
except ImportError:
    HAS_PYDANTIC_SETTINGS = False
    from pydantic import BaseModel as BaseSettings
    class SettingsConfigDict(dict): pass

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


    class Settings(BaseSettings):
        """Global Application Settings."""
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore"
        )

        env: str = Field("development", validation_alias="APP_ENV")
        debug: bool = Field(False, validation_alias="APP_DEBUG")
        
        redis: RedisSettings = RedisSettings()
        ai: AISettings = AISettings()
        blockchain: BlockchainSettings = BlockchainSettings()
        security: SecuritySettings = SecuritySettings()
else:
    # Fallback to pure os.getenv for environment mapping
    from dataclasses import dataclass, field

    @dataclass
    class RedisSettings:
        url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379"))
        db: int = field(default_factory=lambda: int(os.getenv("REDIS_DB", "0")))
        max_connections: int = field(default_factory=lambda: int(os.getenv("REDIS_MAX_CONNECTIONS", "10")))
        socket_timeout: float = field(default_factory=lambda: float(os.getenv("REDIS_SOCKET_TIMEOUT", "5.0")))
        retry_on_timeout: bool = field(default_factory=lambda: os.getenv("REDIS_RETRY_ON_TIMEOUT", "true").lower() == "true")

    @dataclass
    class AISettings:
        openrouter_api_key: Optional[SecretStr] = field(default_factory=lambda: SecretStr(os.getenv("OPENROUTER_API_KEY", "")) if os.getenv("OPENROUTER_API_KEY") else None)
        hf_token: Optional[SecretStr] = field(default_factory=lambda: SecretStr(os.getenv("HF_TOKEN", "")) if os.getenv("HF_TOKEN") else None)
        openai_api_key: Optional[SecretStr] = field(default_factory=lambda: SecretStr(os.getenv("OPENAI_API_KEY", "")) if os.getenv("OPENAI_API_KEY") else None)
        constitutional_hash: str = field(default_factory=lambda: os.getenv("CONSTITUTIONAL_HASH", "cdd01ef066bc6cf2"))

    @dataclass
    class BlockchainSettings:
        eth_l2_network: str = field(default_factory=lambda: os.getenv("ETH_L2_NETWORK", "optimism"))
        eth_rpc_url: str = field(default_factory=lambda: os.getenv("ETH_RPC_URL", "https://mainnet.optimism.io"))
        contract_address: Optional[str] = field(default_factory=lambda: os.getenv("AUDIT_CONTRACT_ADDRESS"))
        private_key: Optional[SecretStr] = field(default_factory=lambda: SecretStr(os.getenv("BLOCKCHAIN_PRIVATE_KEY", "")) if os.getenv("BLOCKCHAIN_PRIVATE_KEY") else None)

    @dataclass
    class SecuritySettings:
        api_key_internal: Optional[SecretStr] = field(default_factory=lambda: SecretStr(os.getenv("API_KEY_INTERNAL", "")) if os.getenv("API_KEY_INTERNAL") else None)
        cors_origins: List[str] = field(default_factory=lambda: os.getenv("CORS_ORIGINS", "*").split(","))
        jwt_secret: Optional[SecretStr] = field(default_factory=lambda: SecretStr(os.getenv("JWT_SECRET", "")) if os.getenv("JWT_SECRET") else None)

    @dataclass
    class Settings:
        env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
        debug: bool = field(default_factory=lambda: os.getenv("APP_DEBUG", "false").lower() == "true")
        
        redis: RedisSettings = field(default_factory=RedisSettings)
        ai: AISettings = field(default_factory=AISettings)
        blockchain: BlockchainSettings = field(default_factory=BlockchainSettings)
        security: SecuritySettings = field(default_factory=SecuritySettings)


# Global settings instance
settings = Settings()

def get_settings() -> Settings:
    """Returns the global settings instance."""
    return settings
