"""
Configuration settings for Policy Registry Service
Constitutional Hash: cdd01ef066bc6cf2
"""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# Constitutional compliance constant
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class Settings(BaseSettings):
    """Application settings"""

    # Service configuration
    service_name: str = "policy-registry"
    service_version: str = "1.0.0"
    constitutional_hash: str = CONSTITUTIONAL_HASH

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # Redis configuration
    redis_url: str = "redis://localhost:6379"
    redis_ttl: int = 3600  # 1 hour
    local_cache_size: int = 100
    local_cache_ttl: int = 300  # 5 minutes

    # Kafka configuration
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "policy-updates"

    # Security configuration
    key_algorithm: str = "Ed25519"

    # Database configuration (for future persistence)
    database_url: Optional[str] = None

    # Vault/OpenBao configuration
    vault_url: Optional[str] = None
    vault_token: Optional[str] = None
    vault_namespace: Optional[str] = None
    vault_transit_mount: str = "transit"
    vault_kv_mount: str = "secret"
    vault_kv_version: int = 2
    vault_timeout: float = 30.0
    vault_skip_verify: bool = False
    vault_ca_cert: Optional[str] = None
    vault_client_cert: Optional[str] = None
    vault_client_key: Optional[str] = None
    vault_fallback_enabled: bool = True
    vault_cache_ttl: int = 300  # 5 minutes
    vault_audit_enabled: bool = True

    model_config = SettingsConfigDict(
        env_prefix="POLICY_REGISTRY_",
        case_sensitive=False,
    )


# Global settings instance
settings = Settings()
