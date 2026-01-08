import logging
import unittest
from unittest.mock import patch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import agents
try:
    from src.agents.base import AgentStatus
    from src.agents.c4_docs_agent import C4DocsAgent
    from src.agents.governance_policy_agent import GovernancePolicyAgent
    from src.agents.regulatory_research_agent import RegulatoryResearchAgent

    IMPORT_SUCCESS = True
except ImportError as e:
    logger.error(f"Import failed: {e}")
    IMPORT_SUCCESS = False


class TestAgentProductionLoop(unittest.IsolatedAsyncioTestCase):
    """Verify that agents can initialize and run in 'production' or fallback mode."""

    async def asyncSetUp(self):
        if not IMPORT_SUCCESS:
            self.skipTest("Agents could not be imported")

    async def test_governance_policy_agent_fallback(self):
        """Test that GovernancePolicyAgent falls back to simulation when AI is not configured."""
        agent = GovernancePolicyAgent()
        # Mocking wait to speed up test
        with patch("asyncio.sleep", return_value=None):
            result = await agent.run("Test analysis prompt")

        self.assertEqual(agent.name, "governance-policy-agent")
        self.assertEqual(result.status, AgentStatus.COMPLETED)
        self.assertIn("[SIMULATED]", result.result)
        # Check result text instead of just metrics
        self.assertTrue(result.result.startswith("[SIMULATED]"))

    async def test_regulatory_research_agent_fallback(self):
        """Test that RegulatoryResearchAgent falls back to simulation."""
        agent = RegulatoryResearchAgent()
        with patch("asyncio.sleep", return_value=None):
            result = await agent.run("Find GDPR updates")

        self.assertEqual(agent.name, "regulatory-research-agent")
        self.assertEqual(result.status, AgentStatus.COMPLETED)
        self.assertIn("[SIMULATED]", result.result)
        self.assertIn("GDPR", result.result)

    async def test_c4_docs_agent_fallback(self):
        """Test that C4DocsAgent falls back to simulation."""
        agent = C4DocsAgent()
        with patch("asyncio.sleep", return_value=None):
            result = await agent.run("Generate C4 diagrams")

        self.assertEqual(agent.name, "c4-docs-agent")
        self.assertEqual(result.status, AgentStatus.COMPLETED)
        self.assertIn("[SIMULATED]", result.result)
        self.assertIn("C4", result.result)


if __name__ == "__main__":
    unittest.main()
