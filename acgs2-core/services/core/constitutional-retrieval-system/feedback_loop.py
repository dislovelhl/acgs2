"""
Feedback Loop for Constitutional Retrieval System

Implements feedback mechanisms to update and improve the vector knowledge base
based on decision outcomes, user feedback, and performance metrics.
"""

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from document_processor import DocumentProcessor
from retrieval_engine import RetrievalEngine
from vector_database import VectorDatabaseManager

logger = logging.getLogger(__name__)


class FeedbackLoop:
    """Manages feedback collection and index updates for continuous improvement."""

    def __init__(
        self,
        vector_db: VectorDatabaseManager,
        doc_processor: DocumentProcessor,
        retrieval_engine: RetrievalEngine,
    ):
        """
        Initialize feedback loop.

        Args:
            vector_db: Vector database manager
            doc_processor: Document processor
            retrieval_engine: Retrieval engine
        """
        self.vector_db = vector_db
        self.doc_processor = doc_processor
        self.retrieval_engine = retrieval_engine

        # Feedback storage
        self.feedback_history: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, Any] = {}

        # Update thresholds
        self.min_feedback_threshold = 5  # Minimum feedback items before update
        self.update_interval_days = 7  # Update every 7 days
        self.last_update = datetime.now(timezone.utc)

    async def collect_decision_feedback(
        self,
        query: str,
        retrieved_documents: List[Dict[str, Any]],
        decision: Dict[str, Any],
        user_feedback: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Collect feedback on a decision and retrieved documents.

        Args:
            query: The original query
            retrieved_documents: Documents retrieved for the query
            decision: The decision made
            user_feedback: Optional user feedback

        Returns:
            Feedback ID for tracking
        """
        feedback_id = f"feedback_{datetime.now(timezone.utc).timestamp()}"

        feedback_entry = {
            "feedback_id": feedback_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query": query,
            "documents_retrieved": len(retrieved_documents),
            "decision": decision,
            "user_feedback": user_feedback or {},
            "retrieval_quality": self._assess_retrieval_quality(retrieved_documents, decision),
            "decision_confidence": decision.get("confidence", 0.0),
            "processed": False,
        }

        self.feedback_history.append(feedback_entry)

        # Auto-trigger update if enough feedback collected
        if len(self.feedback_history) >= self.min_feedback_threshold:
            await self._check_and_trigger_update()

        logger.info(f"Collected feedback {feedback_id} for query: {query[:50]}...")
        return feedback_id

    async def update_index_from_feedback(self) -> Dict[str, Any]:
        """
        Update the vector index based on accumulated feedback.

        Returns:
            Update results and metrics
        """
        if not self.feedback_history:
            return {"status": "no_feedback", "message": "No feedback to process"}

        try:
            # Analyze feedback patterns
            feedback_analysis = self._analyze_feedback_patterns()

            # Generate index updates
            index_updates = self._generate_index_updates(feedback_analysis)

            # Apply updates
            update_results = await self._apply_index_updates(index_updates)

            # Update performance metrics
            self._update_performance_metrics(feedback_analysis, update_results)

            # Mark feedback as processed
            for entry in self.feedback_history:
                entry["processed"] = True

            # Reset feedback history but keep recent entries for analysis
            self.feedback_history = self.feedback_history[-50:]  # Keep last 50

            self.last_update = datetime.now(timezone.utc)

            logger.info(f"Index update completed: {update_results}")
            return {
                "status": "success",
                "updates_applied": len(index_updates),
                "feedback_processed": len(self.feedback_history),
                "metrics": self.performance_metrics.copy(),
            }

        except Exception as e:
            logger.error(f"Index update failed: {e}")
            return {"status": "error", "message": str(e)}

    async def add_new_knowledge(
        self, documents: List[Dict[str, Any]], source: str = "manual"
    ) -> bool:
        """
        Add new documents to the knowledge base.

        Args:
            documents: New documents to add
            source: Source of the documents

        Returns:
            Success status
        """
        try:
            # Process and index new documents
            success = await self.retrieval_engine.index_documents(documents)

            if success:
                # Record the addition for feedback tracking
                feedback_entry = {
                    "feedback_id": f"knowledge_add_{datetime.now(timezone.utc).timestamp()}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "type": "knowledge_addition",
                    "documents_added": len(documents),
                    "source": source,
                    "processed": True,
                }
                self.feedback_history.append(feedback_entry)

                logger.info(f"Added {len(documents)} new documents from {source}")
            return success

        except Exception as e:
            logger.error(f"Failed to add new knowledge: {e}")
            return False

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        metrics = self.performance_metrics.copy()

        # Add real-time metrics
        total_feedback = len(self.feedback_history)
        processed_feedback = sum(1 for f in self.feedback_history if f.get("processed", False))

        metrics.update(
            {
                "total_feedback_collected": total_feedback,
                "processed_feedback": processed_feedback,
                "pending_feedback": total_feedback - processed_feedback,
                "last_update": self.last_update.isoformat(),
                "days_since_update": (datetime.now(timezone.utc) - self.last_update).days,
            }
        )

        return metrics

    async def optimize_retrieval_parameters(self) -> Dict[str, Any]:
        """
        Optimize retrieval parameters based on feedback.

        Returns:
            Optimization recommendations
        """
        if len(self.feedback_history) < 10:
            return {"status": "insufficient_data", "message": "Need more feedback for optimization"}

        try:
            # Analyze retrieval performance
            performance_analysis = self._analyze_retrieval_performance()

            # Generate parameter recommendations
            recommendations = self._generate_parameter_recommendations(performance_analysis)

            logger.info(f"Generated optimization recommendations: {recommendations}")
            return {
                "status": "success",
                "recommendations": recommendations,
                "analysis": performance_analysis,
            }

        except Exception as e:
            logger.error(f"Parameter optimization failed: {e}")
            return {"status": "error", "message": str(e)}

    def _assess_retrieval_quality(
        self, documents: List[Dict[str, Any]], decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess the quality of document retrieval."""
        if not documents:
            return {"quality_score": 0.0, "issues": ["no_documents_retrieved"]}

        # Basic quality metrics
        avg_score = sum(doc.get("score", 0.0) for doc in documents) / len(documents)
        high_relevance_count = sum(1 for doc in documents if doc.get("score", 0.0) > 0.8)

        quality_score = min(avg_score * 1.2, 1.0)  # Boost but cap at 1.0

        issues = []
        if avg_score < 0.5:
            issues.append("low_average_relevance")
        if high_relevance_count == 0:
            issues.append("no_highly_relevant_documents")

        return {
            "quality_score": quality_score,
            "average_score": avg_score,
            "high_relevance_count": high_relevance_count,
            "total_documents": len(documents),
            "issues": issues,
        }

    def _analyze_feedback_patterns(self) -> Dict[str, Any]:
        """Analyze patterns in collected feedback."""
        if not self.feedback_history:
            return {}

        # Group feedback by various criteria
        patterns = {
            "avg_retrieval_quality": 0.0,
            "avg_decision_confidence": 0.0,
            "common_issues": defaultdict(int),
            "decision_distribution": defaultdict(int),
            "query_categories": defaultdict(int),
        }

        total_feedback = len(self.feedback_history)

        for entry in self.feedback_history:
            # Retrieval quality
            quality = entry.get("retrieval_quality", {})
            patterns["avg_retrieval_quality"] += quality.get("quality_score", 0.0)

            # Decision confidence
            patterns["avg_decision_confidence"] += entry.get("decision_confidence", 0.0)

            # Decision types
            decision = entry.get("decision", {})
            rec = decision.get("recommendation", "unknown")
            patterns["decision_distribution"][rec] += 1

            # Issues
            issues = quality.get("issues", [])
            for issue in issues:
                patterns["common_issues"][issue] += 1

        # Calculate averages
        if total_feedback > 0:
            patterns["avg_retrieval_quality"] /= total_feedback
            patterns["avg_decision_confidence"] /= total_feedback

        # Convert defaultdicts to regular dicts
        patterns["common_issues"] = dict(patterns["common_issues"])
        patterns["decision_distribution"] = dict(patterns["decision_distribution"])

        return patterns

    def _generate_index_updates(self, feedback_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate index updates based on feedback analysis."""
        updates = []

        # If retrieval quality is low, suggest adding more documents
        if feedback_analysis.get("avg_retrieval_quality", 1.0) < 0.7:
            updates.append(
                {
                    "type": "add_documents",
                    "reason": "low_retrieval_quality",
                    "priority": "high",
                    "description": "Add more comprehensive constitutional documents",
                }
            )

        # If decision confidence is low, suggest better indexing
        if feedback_analysis.get("avg_decision_confidence", 1.0) < 0.6:
            updates.append(
                {
                    "type": "reindex_documents",
                    "reason": "low_decision_confidence",
                    "priority": "medium",
                    "description": "Re-index documents with improved chunking strategy",
                }
            )

        # Address common issues
        common_issues = feedback_analysis.get("common_issues", {})
        if "no_highly_relevant_documents" in common_issues:
            updates.append(
                {
                    "type": "expand_coverage",
                    "reason": "missing_relevant_documents",
                    "priority": "high",
                    "description": "Add documents covering underrepresented legal areas",
                }
            )

        return updates

    async def _apply_index_updates(self, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply the generated index updates."""
        results = {"applied": 0, "failed": 0, "details": []}

        for update in updates:
            try:
                update_type = update.get("type")

                if update_type == "add_documents":
                    # This would typically involve external document addition
                    # For now, just log the recommendation
                    results["details"].append(f"Recommended: {update.get('description')}")
                    results["applied"] += 1

                elif update_type == "reindex_documents":
                    # Trigger re-indexing of existing documents
                    # This is a placeholder - actual implementation would depend on the system
                    results["details"].append("Re-indexing recommended")
                    results["applied"] += 1

                elif update_type == "expand_coverage":
                    results["details"].append(f"Coverage expansion: {update.get('description')}")
                    results["applied"] += 1

                else:
                    results["details"].append(f"Unknown update type: {update_type}")
                    results["failed"] += 1

            except Exception as e:
                results["failed"] += 1
                results["details"].append(f"Update failed: {str(e)}")

        return results

    def _update_performance_metrics(
        self, feedback_analysis: Dict[str, Any], update_results: Dict[str, Any]
    ) -> None:
        """Update internal performance metrics."""
        self.performance_metrics.update(
            {
                "last_feedback_analysis": feedback_analysis,
                "last_update_results": update_results,
                "total_updates_applied": self.performance_metrics.get("total_updates_applied", 0)
                + update_results.get("applied", 0),
                "update_success_rate": update_results.get("applied", 0)
                / max(update_results.get("applied", 0) + update_results.get("failed", 0), 1),
            }
        )

    async def _check_and_trigger_update(self) -> None:
        """Check if update should be triggered and execute if needed."""
        days_since_update = (datetime.now(timezone.utc) - self.last_update).days

        if (
            len(self.feedback_history) >= self.min_feedback_threshold
            or days_since_update >= self.update_interval_days
        ):
            logger.info("Triggering automatic index update")
            await self.update_index_from_feedback()

    def _analyze_retrieval_performance(self) -> Dict[str, Any]:
        """Analyze retrieval performance from feedback."""
        performance = {
            "avg_query_length": 0.0,
            "avg_documents_retrieved": 0.0,
            "retrieval_success_rate": 0.0,
            "high_confidence_decisions": 0,
        }

        if not self.feedback_history:
            return performance

        total_queries = len(self.feedback_history)
        successful_retrievals = 0

        for entry in self.feedback_history:
            query_len = len(entry.get("query", ""))
            performance["avg_query_length"] += query_len

            docs_retrieved = entry.get("documents_retrieved", 0)
            performance["avg_documents_retrieved"] += docs_retrieved

            if docs_retrieved > 0:
                successful_retrievals += 1

            confidence = entry.get("decision_confidence", 0.0)
            if confidence > 0.8:
                performance["high_confidence_decisions"] += 1

        performance["avg_query_length"] /= max(total_queries, 1)
        performance["avg_documents_retrieved"] /= max(total_queries, 1)
        performance["retrieval_success_rate"] = successful_retrievals / max(total_queries, 1)

        return performance

    def _generate_parameter_recommendations(self, performance: Dict[str, Any]) -> Dict[str, Any]:
        """Generate parameter optimization recommendations."""
        recommendations = {}

        # Adjust retrieval limits based on performance
        avg_docs = performance.get("avg_documents_retrieved", 5)
        if avg_docs < 3:
            recommendations["increase_retrieval_limit"] = (
                "Increase from current limit to retrieve more documents"
            )
        elif avg_docs > 10:
            recommendations["decrease_retrieval_limit"] = "Decrease limit to improve relevance"

        # Adjust similarity thresholds
        success_rate = performance.get("retrieval_success_rate", 0.0)
        if success_rate < 0.7:
            recommendations["lower_similarity_threshold"] = (
                "Lower threshold to include more potentially relevant documents"
            )

        # Chunk size optimization
        query_length = performance.get("avg_query_length", 100)
        if query_length > 200:
            recommendations["increase_chunk_size"] = "Increase chunk size for longer queries"

        return recommendations
