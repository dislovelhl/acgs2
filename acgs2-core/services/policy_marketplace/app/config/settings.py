"""
Settings for policy marketplace service
"""

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MarketplaceSettings(BaseSettings):
    """Global Application Settings"""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    service_name: str = "policy-marketplace"
    service_version: str = "1.0.0"
    port: int = 8003
    host: str = "0.0.0.0"
    debug: bool = False

    # Infrastructure
    database_url: str = Field(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/acgs2_marketplace",
        validation_alias="MARKETPLACE_DATABASE_URL",
    )
    redis_url: str = Field("redis://localhost:6379/0", validation_alias="REDIS_URL")

    # Security
    cors_origins: List[str] = Field(["*"], validation_alias="MARKETPLACE_CORS_ORIGINS")


settings = MarketplaceSettings()
