"""
Linear API credentials and configuration.
"""

from typing import Literal, Optional

from pydantic import Field, SecretStr, validator

from ..base import IntegrationCredentials, IntegrationType


class LinearCredentials(IntegrationCredentials):
    """
    Credentials for Linear API integration.

    Linear uses OAuth 2.0 for authentication. The integration requires:
    - API key (personal access token)
    - Base URL for the Linear API
    """

    integration_type: Literal[IntegrationType.TICKETING] = Field(IntegrationType.TICKETING)

    # Linear specific fields
    api_key: SecretStr = Field(..., description="Linear personal access token")
    base_url: str = Field(
        "https://api.linear.app/graphql", description="Linear GraphQL API endpoint"
    )

    # Optional organization settings
    organization_id: Optional[str] = Field(None, description="Linear organization ID")
    default_team_id: Optional[str] = Field(None, description="Default team ID for issue creation")
    default_project_id: Optional[str] = Field(
        None, description="Default project ID for issue creation"
    )

    # Issue creation settings
    default_issue_template: Optional[str] = Field(
        None, description="Template for issue titles and descriptions"
    )
    default_priority: Optional[int] = Field(
        None, description="Default priority level (1-4, where 1 is highest)", ge=1, le=4
    )

    @validator("base_url")
    def validate_base_url(cls, v):
        """Ensure base URL is valid for Linear API."""
        if not v.startswith("https://"):
            raise ValueError("Linear API URL must use HTTPS")
        return v

    @validator("default_priority")
    def validate_priority(cls, v):
        """Validate priority is within Linear's range."""
        if v is not None and not (1 <= v <= 4):
            raise ValueError("Priority must be between 1 (highest) and 4 (lowest)")
        return v

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            SecretStr: lambda v: "***REDACTED***" if v else None,
        }

    def get_auth_headers(self) -> dict:
        """
        Get authentication headers for Linear API requests.

        Returns:
            Dictionary containing Authorization header
        """
        return {
            "Authorization": f"Bearer {self.api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }
