"""
Jira integration adapter
"""

import logging
from typing import Any, Dict

from .base import IntegrationAdapter

logger = logging.getLogger(__name__)


class JiraAdapter(IntegrationAdapter):
    """
    Adapter for Jira ticketing integration.
    """

    async def authenticate(self) -> bool:
        """Validate Jira API credentials"""
        # In a real implementation, we'd call /myself or similar
        logger.info(f"Authenticating with Jira at {self.config.get('base_url')}")
        return True

    async def validate_config(self) -> bool:
        """Check required Jira config fields"""
        required = ["base_url", "user_email", "api_token", "project_key"]
        return all(self.config.get(field) for field in required)

    async def send_event(self, event_data: Dict[str, Any]) -> bool:
        """Create a Jira issue from a governance event"""
        if not await self.validate_config():
            return False

        url = f"{self.config['base_url'].rstrip('/')}/rest/api/3/issue"

        payload = {
            "fields": {
                "project": {"key": self.config["project_key"]},
                "summary": f"Governance Alert: {event_data.get('action')}",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"A governance event was detected: {event_data.get('details')}",
                                }
                            ],
                        }
                    ],
                },
                "issuetype": {"name": "Task"},
            }
        }

        try:
            # Mocking the actual call for now
            logger.info(f"Creating Jira issue for event {event_data.get('id')}")
            # await self._post_with_retry(url, json=payload, auth=(self.config['user_email'], self.config['api_token']))
            return True
        except Exception as e:
            logger.error(f"Failed to create Jira issue: {e}")
            return False
