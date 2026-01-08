import logging
import unittest
from unittest.mock import AsyncMock, patch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import agents
try:
    from src.agents.base import AgentStatus
    from src.agents.governance_policy_agent import GovernancePolicyAgent

    IMPORT_SUCCESS = True
except ImportError as e:
    logger.error(f"Import failed: {e}")
    IMPORT_SUCCESS = False


class TestAgentProductionLoopV3(unittest.IsolatedAsyncioTestCase):
    """Verify the fixed production loop (Retrieval -> Reasoning)."""

    async def asyncSetUp(self):
        if not IMPORT_SUCCESS:
            self.skipTest("Agents could not be imported")

    @patch("src.agents.base.create_vector_db_manager")
    @patch("src.agents.base.DocumentProcessor")
    @patch("src.agents.base.RetrievalEngine")
    @patch("src.agents.base.LLMReasoner")
    async def test_production_loop_execution_sequence(
        self, MockReasoner, MockEngine, MockProcessor, MockDBManager
    ):
        """Verify that retrieval is called first and context is passed to reasoner."""

        # Setup mocks
        mock_retrieval_engine = MockEngine.return_value
        mock_llm_reasoner = MockReasoner.return_value
        mock_vector_db = MockDBManager.return_value

        # Ensure connect returns True
        mock_vector_db.connect = AsyncMock(return_value=True)

        mock_docs = [{"payload": {"content": "Test context"}}]
        mock_retrieval_engine.retrieve_similar_documents = AsyncMock(return_value=mock_docs)

        mock_response = {"reasoning": "Standard reasoning output", "metrics": {"tokens": 100}}
        mock_llm_reasoner.reason_with_context = AsyncMock(return_value=mock_response)

        # Force CORE_AI_AVAILABLE to True in the module
        import src.agents.base as base_mod

        with patch.object(base_mod, "CORE_AI_AVAILABLE", True):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                # Initialize agent
                agent = GovernancePolicyAgent()

                print(f"\nDEBUG: CORE_AI_AVAILABLE={base_mod.CORE_AI_AVAILABLE}")

                # Run agent
                prompt = "Analyze policy X"
                result = await agent.run(prompt)

                print(f"DEBUG: agent._ai_initialized={agent._ai_initialized}")
                print(f"DEBUG: agent.status={agent.status}")
                print(f"DEBUG: result.result={result.result}")

                # Verify execution sequence and arguments
                # 1. Retrieval called with prompt
                self.assertTrue(
                    mock_retrieval_engine.retrieve_similar_documents.called,
                    "RetrivalEngine.retrieve_similar_documents was NOT called",
                )
                mock_retrieval_engine.retrieve_similar_documents.assert_called_once_with(
                    prompt, limit=5
                )

                # 2. Reasoner called with prompt AND retrieved docs
                self.assertTrue(
                    mock_llm_reasoner.reason_with_context.called,
                    "LLMReasoner.reason_with_context was NOT called",
                )
                mock_llm_reasoner.reason_with_context.assert_called_once_with(
                    query=prompt, context_documents=mock_docs
                )

                # 3. Result contains reasoning
                self.assertTrue(
                    agent._ai_initialized, "Agent AI should be initialized in production loop test"
                )
                self.assertEqual(result.status, AgentStatus.COMPLETED)
                self.assertEqual(result.result, "Standard reasoning output")
                self.assertEqual(result.metrics.get("context_docs_count"), 1)


if __name__ == "__main__":
    unittest.main()
