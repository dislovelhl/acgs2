"""
Pydantic models for tenant quota configuration
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TenantQuotaConfig(BaseSettings):
    """Configuration for tenant resource quotas and rate limits"""

    model_config = SettingsConfigDict(env_prefix="TENANT_QUOTA_", case_sensitive=False)

    cpu: str = Field(default="2", description="CPU quota (e.g., '2' or '2000m')")
    memory: str = Field(default="4Gi", description="Memory quota")
    storage: str = Field(default="20Gi", description="Storage quota")
    rate_limit_requests: int = Field(default=1000, description="Requests per window")
    rate_limit_window_seconds: int = Field(default=60, description="Rate limit window")
