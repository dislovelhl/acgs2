"""
Configuration settings for Policy Registry Service
"""

import os
from typing import Optional

from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Service configuration
    service_name: str = "policy-registry"
    service_version: str = "1.0.0"
    
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
    
    # Vault configuration
    vault_url: Optional[str] = None
    vault_token: Optional[str] = None
    
    class Config:
        """Pydantic configuration"""
        env_prefix = "POLICY_REGISTRY_"
        case_sensitive = False


# Global settings instance
settings = Settings()
