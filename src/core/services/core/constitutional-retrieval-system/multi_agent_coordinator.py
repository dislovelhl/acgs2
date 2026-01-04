"""Constitutional Hash: cdd01ef066bc6cf2
Multi-Agent Coordinator for Constitutional Retrieval System

Enables multiple agents to collaborate by sharing and accessing
a common vector knowledge base of constitutional documents and precedents.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from feedback_loop import FeedbackLoop
from llm_reasoner import LLMReasoner
from retrieval_engine import RetrievalEngine
from vector_database import VectorDatabaseManager

logger = logging.getLogger(__name__)


class MultiAgentCoordinator:
    """Coordinates multiple agents accessing shared constitutional knowledge base."""

    def __init__(
        self,
        vector_db: VectorDatabaseManager,
        retrieval_engine: RetrievalEngine,
        llm_reasoner: LLMReasoner,
        feedback_loop: FeedbackLoop,
    ):
        """
        Initialize multi-agent coordinator.

        Args:
            vector_db: Shared vector database
            retrieval_engine: Shared retrieval engine
            llm_reasoner: Shared LLM reasoner
            feedback_loop: Shared feedback loop
        """
        self.vector_db = vector_db
        self.retrieval_engine = retrieval_engine
        self.llm_reasoner = llm_reasoner
        self.feedback_loop = feedback_loop

        # Agent registry
        self.registered_agents: Dict[str, Dict[str, Any]] = {}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

        # Collaboration settings
        self.max_concurrent_agents = 10
        self.session_timeout_minutes = 30

        # Shared knowledge access control
        self.knowledge_permissions: Dict[str, Set[str]] = {}

        # Collaboration metrics
        self.collaboration_metrics: Dict[str, Any] = {
            "total_agents": 0,
            "active_sessions": 0,
            "shared_queries": 0,
            "knowledge_contributions": 0,
        }

    async def register_agent(self, agent_id: str, agent_info: Dict[str, Any]) -> bool:
        """
        Register an agent for collaboration.

        Args:
            agent_id: Unique agent identifier
            agent_info: Agent metadata (type, capabilities, permissions)

        Returns:
            Registration success
        """
        try:
            if agent_id in self.registered_agents:
                logger.warning(f"Agent {agent_id} already registered")
                return False

            # Validate agent info
            required_fields = ["agent_type", "capabilities"]
            for field in required_fields:
                if field not in agent_info:
                    logger.error(f"Missing required field: {field}")
                    return False

            # Register agent
            registration = {
                "agent_id": agent_id,
                "registered_at": datetime.now(timezone.utc).isoformat(),
                "last_active": datetime.now(timezone.utc).isoformat(),
                "status": "active",
                **agent_info,
            }

            self.registered_agents[agent_id] = registration

            # Initialize permissions
            self.knowledge_permissions[agent_id] = set(agent_info.get("permissions", ["read"]))

            self.collaboration_metrics["total_agents"] += 1

            logger.info(f"Registered agent {agent_id} of type {agent_info.get('agent_type')}")
            return True

        except Exception as e:
            logger.error(f"Failed to register agent {agent_id}: {e}")
            return False

    async def start_collaboration_session(
        self, agent_id: str, session_purpose: str
    ) -> Optional[str]:
        """
        Start a collaboration session for an agent.

        Args:
            agent_id: Agent identifier
            session_purpose: Purpose of the session

        Returns:
            Session ID or None if failed
        """
        try:
            if agent_id not in self.registered_agents:
                logger.error(f"Agent {agent_id} not registered")
                return None

            # Check concurrent session limit
            active_count = sum(
                1 for s in self.active_sessions.values() if s["agent_id"] == agent_id
            )
            if active_count >= 3:  # Max 3 concurrent sessions per agent
                logger.warning(f"Agent {agent_id} has too many active sessions")
                return None

            session_id = f"session_{agent_id}_{datetime.now(timezone.utc).timestamp()}"

            session = {
                "session_id": session_id,
                "agent_id": agent_id,
                "purpose": session_purpose,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "status": "active",
                "queries_made": 0,
                "knowledge_accessed": [],
            }

            self.active_sessions[session_id] = session
            self.registered_agents[agent_id]["last_active"] = datetime.now(timezone.utc).isoformat()

            self.collaboration_metrics["active_sessions"] += 1

            logger.info(f"Started collaboration session {session_id} for agent {agent_id}")
            return session_id

        except Exception as e:
            logger.error(f"Failed to start session for agent {agent_id}: {e}")
            return None

    async def collaborative_query(
        self, session_id: str, query: str, agent_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform a collaborative query using shared knowledge base.

        Args:
            session_id: Active session ID
            query: Query string
            agent_context: Additional context from the querying agent

        Returns:
            Query results with collaboration metadata
        """
        try:
            # Validate session
            if session_id not in self.active_sessions:
                return {"error": "Invalid session", "results": []}

            session = self.active_sessions[session_id]
            agent_id = session["agent_id"]

            # Check permissions
            if "read" not in self.knowledge_permissions.get(agent_id, set()):
                return {"error": "Insufficient permissions", "results": []}

            # Perform retrieval
            retrieved_docs = await self.retrieval_engine.retrieve_similar_documents(query, limit=10)

            # Enhance with agent context if provided
            if agent_context:
                retrieved_docs = self._enhance_with_agent_context(retrieved_docs, agent_context)

            # Record session activity
            session["queries_made"] += 1
            session["knowledge_accessed"].extend([doc.get("id") for doc in retrieved_docs])

            self.collaboration_metrics["shared_queries"] += 1

            # Add collaboration metadata
            result = {
                "query": query,
                "results": retrieved_docs,
                "session_id": session_id,
                "agent_id": agent_id,
                "collaboration_info": {
                    "shared_knowledge_used": True,
                    "results_count": len(retrieved_docs),
                    "query_timestamp": datetime.now(timezone.utc).isoformat(),
                },
            }

            logger.info(f"Collaborative query by agent {agent_id}: {len(retrieved_docs)} results")
            return result

        except Exception as e:
            logger.error(f"Collaborative query failed for session {session_id}: {e}")
            return {"error": str(e), "results": []}

    async def contribute_knowledge(
        self,
        session_id: str,
        documents: List[Dict[str, Any]],
        contribution_metadata: Dict[str, Any],
    ) -> bool:
        """
        Allow an agent to contribute new knowledge to the shared base.

        Args:
            session_id: Active session ID
            documents: Documents to contribute
            contribution_metadata: Metadata about the contribution

        Returns:
            Contribution success
        """
        try:
            # Validate session and permissions
            if session_id not in self.active_sessions:
                logger.error("Invalid session for knowledge contribution")
                return False

            session = self.active_sessions[session_id]
            agent_id = session["agent_id"]

            if "write" not in self.knowledge_permissions.get(agent_id, set()):
                logger.error(f"Agent {agent_id} lacks write permissions")
                return False

            # Add contribution metadata
            for doc in documents:
                doc["metadata"] = doc.get("metadata", {})
                doc["metadata"].update(
                    {
                        "contributed_by": agent_id,
                        "contribution_session": session_id,
                        "contributed_at": datetime.now(timezone.utc).isoformat(),
                        **contribution_metadata,
                    }
                )

            # Index the new documents
            success = await self.retrieval_engine.index_documents(documents)

            if success:
                # Record contribution in feedback loop
                await self.feedback_loop.add_new_knowledge(documents, source=f"agent_{agent_id}")

                session["contributions_made"] = session.get("contributions_made", 0) + len(
                    documents
                )
                self.collaboration_metrics["knowledge_contributions"] += len(documents)

                logger.info(f"Agent {agent_id} contributed {len(documents)} documents")
            return success

        except Exception as e:
            logger.error(f"Knowledge contribution failed: {e}")
            return False

    async def request_peer_assistance(
        self, session_id: str, query: str, required_capabilities: List[str]
    ) -> Dict[str, Any]:
        """
        Request assistance from peer agents with specific capabilities.

        Args:
            session_id: Requesting agent's session
            query: The assistance query
            required_capabilities: Required agent capabilities

        Returns:
            Assistance results from peer agents
        """
        try:
            if session_id not in self.active_sessions:
                return {"error": "Invalid session", "assistance": []}

            requesting_agent = self.active_sessions[session_id]["agent_id"]

            # Find suitable peer agents
            suitable_agents = []
            for agent_id, agent_info in self.registered_agents.items():
                if agent_id == requesting_agent:
                    continue

                agent_caps = set(agent_info.get("capabilities", []))
                required_caps = set(required_capabilities)

                if required_caps.issubset(agent_caps):
                    suitable_agents.append(agent_id)

            if not suitable_agents:
                return {"error": "No suitable peer agents found", "assistance": []}

            # For now, simulate peer assistance (in real implementation, this would
            # involve inter-agent communication)
            assistance_results = []
            for peer_agent in suitable_agents[:3]:  # Limit to 3 peers
                # Simulate peer analysis
                peer_result = await self._simulate_peer_analysis(peer_agent, query)
                assistance_results.append(peer_result)

            logger.info(
                f"Peer assistance requested by {requesting_agent}: {len(assistance_results)} responses"
            )
            return {
                "query": query,
                "assistance": assistance_results,
                "peer_agents_engaged": len(assistance_results),
            }

        except Exception as e:
            logger.error(f"Peer assistance request failed: {e}")
            return {"error": str(e), "assistance": []}

    async def end_session(self, session_id: str) -> bool:
        """
        End a collaboration session.

        Args:
            session_id: Session to end

        Returns:
            Success status
        """
        try:
            if session_id not in self.active_sessions:
                return False

            session = self.active_sessions[session_id]
            session["status"] = "ended"
            session["ended_at"] = datetime.now(timezone.utc).isoformat()

            # Calculate session duration
            start_time = datetime.fromisoformat(session["started_at"])
            end_time = datetime.now(timezone.utc)
            duration_minutes = (end_time - start_time).total_seconds() / 60
            session["duration_minutes"] = duration_minutes

            # Update metrics
            self.collaboration_metrics["active_sessions"] -= 1

            logger.info(f"Ended session {session_id} after {duration_minutes:.1f} minutes")
            return True

        except Exception as e:
            logger.error(f"Failed to end session {session_id}: {e}")
            return False

    def get_collaboration_metrics(self) -> Dict[str, Any]:
        """Get current collaboration metrics."""
        metrics = self.collaboration_metrics.copy()

        # Add real-time stats
        metrics.update(
            {
                "registered_agents": len(self.registered_agents),
                "active_sessions": len(self.active_sessions),
                "current_time": datetime.now(timezone.utc).isoformat(),
            }
        )

        return metrics

    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        current_time = datetime.now(timezone.utc)
        expired_sessions = []

        for session_id, session in self.active_sessions.items():
            start_time = datetime.fromisoformat(session["started_at"])
            duration_minutes = (current_time - start_time).total_seconds() / 60

            if duration_minutes > self.session_timeout_minutes:
                expired_sessions.append(session_id)

        # End expired sessions
        for session_id in expired_sessions:
            await self.end_session(session_id)

        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

        return len(expired_sessions)

    def _enhance_with_agent_context(
        self, documents: List[Dict[str, Any]], agent_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Enhance retrieved documents with agent-specific context."""
        agent_type = agent_context.get("agent_type", "unknown")
        agent_priorities = agent_context.get("priorities", [])

        enhanced_docs = []
        for doc in documents:
            enhanced_doc = doc.copy()

            # Add agent-specific relevance scoring
            base_score = doc.get("score", 0.0)
            context_boost = self._calculate_context_boost(doc, agent_type, agent_priorities)
            enhanced_doc["agent_relevance_score"] = min(base_score + context_boost, 1.0)

            enhanced_docs.append(enhanced_doc)

        # Re-sort by agent relevance
        enhanced_docs.sort(key=lambda x: x.get("agent_relevance_score", 0), reverse=True)

        return enhanced_docs

    def _calculate_context_boost(
        self, document: Dict[str, Any], agent_type: str, priorities: List[str]
    ) -> float:
        """Calculate context-based relevance boost."""
        boost = 0.0

        payload = document.get("payload", {})
        doc_type = payload.get("doc_type", "")
        content = payload.get("content", "").lower()

        # Boost based on agent type
        if agent_type == "constitutional_expert" and doc_type == "constitution":
            boost += 0.2
        elif agent_type == "legal_researcher" and doc_type == "precedent":
            boost += 0.2

        # Boost based on priorities
        for priority in priorities:
            if priority.lower() in content:
                boost += 0.1

        return min(boost, 0.5)  # Cap boost at 0.5

    async def _simulate_peer_analysis(self, peer_agent: str, query: str) -> Dict[str, Any]:
        """Simulate analysis from a peer agent (placeholder for real inter-agent communication)."""
        # In a real implementation, this would involve actual inter-agent messaging
        # For now, return a simulated response

        agent_info = self.registered_agents.get(peer_agent, {})

        simulated_response = {
            "peer_agent": peer_agent,
            "agent_type": agent_info.get("agent_type", "unknown"),
            "analysis": f"Peer analysis of: {query[:100]}...",
            "confidence": 0.8,
            "recommendations": ["Consider additional constitutional provisions"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return simulated_response

    async def get_agent_recommendations(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        Get personalized recommendations for an agent based on their usage patterns.

        Args:
            agent_id: Agent identifier

        Returns:
            List of recommendations
        """
        if agent_id not in self.registered_agents:
            return []

        recommendations = []

        # Analyze agent's session history
        agent_sessions = [s for s in self.active_sessions.values() if s["agent_id"] == agent_id]

        if not agent_sessions:
            recommendations.append(
                {
                    "type": "exploration",
                    "message": "Try exploring the shared knowledge base with some queries",
                }
            )
        else:
            total_queries = sum(s.get("queries_made", 0) for s in agent_sessions)
            if total_queries < 5:
                recommendations.append(
                    {
                        "type": "engagement",
                        "message": "Increase query frequency to better utilize shared knowledge",
                    }
                )

        return recommendations
