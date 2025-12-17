"""
ACGS-2 Deliberation Layer - Impact Scorer
Uses BERT embeddings to calculate impact scores for decision-making.
"""

import numpy as np
from typing import Dict, Any, Optional
from transformers import BertTokenizer, BertModel
import torch
from sklearn.metrics.pairwise import cosine_similarity


class ImpactScorer:
    """Calculates impact scores using BERT embeddings and similarity analysis."""

    def __init__(self, model_name: str = 'bert-base-uncased'):
        """Initialize the BERT model and tokenizer."""
        self.tokenizer = BertTokenizer.from_pretrained(model_name)
        self.model = BertModel.from_pretrained(model_name)
        self.model.eval()

        # Pre-defined high-impact keywords for baseline comparison
        self.high_impact_keywords = [
            "critical", "emergency", "security", "breach", "violation", "danger",
            "risk", "threat", "attack", "exploit", "vulnerability", "compromise",
            "governance", "policy", "regulation", "compliance", "legal", "audit",
            "financial", "transaction", "payment", "transfer", "blockchain", "consensus"
        ]

        # Cache for keyword embeddings
        self._keyword_embeddings = None

    def _get_embeddings(self, text: str) -> np.ndarray:
        """Get BERT embeddings for input text."""
        inputs = self.tokenizer(text, return_tensors='pt', truncation=True,
                               padding=True, max_length=512)

        with torch.no_grad():
            outputs = self.model(**inputs)
            # Use mean pooling of last hidden state
            embeddings = outputs.last_hidden_state.mean(dim=1).numpy()

        return embeddings

    def _get_keyword_embeddings(self) -> np.ndarray:
        """Get embeddings for high-impact keywords."""
        if self._keyword_embeddings is None:
            keyword_texts = " ".join(self.high_impact_keywords)
            self._keyword_embeddings = self._get_embeddings(keyword_texts)

        return self._keyword_embeddings

    def calculate_impact_score(self, message_content: Dict[str, Any]) -> float:
        """
        Calculate impact score based on message content.

        Args:
            message_content: Dictionary containing message data

        Returns:
            Float between 0.0 and 1.0 representing impact level
        """
        # Extract text content from message
        text_content = self._extract_text_content(message_content)

        if not text_content:
            return 0.0

        # Get embeddings for message content
        message_embedding = self._get_embeddings(text_content)

        # Get keyword embeddings
        keyword_embedding = self._get_keyword_embeddings()

        # Calculate cosine similarity
        similarity = cosine_similarity(message_embedding, keyword_embedding)[0][0]

        # Additional factors
        priority_factor = self._calculate_priority_factor(message_content)
        type_factor = self._calculate_type_factor(message_content)

        # Combine factors (weighted average)
        base_score = float(similarity)
        combined_score = (base_score * 0.6) + (priority_factor * 0.3) + (type_factor * 0.1)

        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, combined_score))

    def _extract_text_content(self, message_content: Dict[str, Any]) -> str:
        """Extract textual content from message dictionary."""
        text_parts = []

        # Extract from common fields
        for field in ['content', 'payload', 'description', 'reason', 'details']:
            if field in message_content:
                value = message_content[field]
                if isinstance(value, str):
                    text_parts.append(value)
                elif isinstance(value, dict):
                    # Recursively extract from nested dict
                    text_parts.append(self._extract_text_content(value))

        return " ".join(text_parts)

    def _calculate_priority_factor(self, message_content: Dict[str, Any]) -> float:
        """Calculate priority-based factor."""
        priority = message_content.get('priority', 'normal').lower()

        priority_map = {
            'low': 0.1,
            'normal': 0.3,
            'medium': 0.5,
            'high': 0.8,
            'critical': 1.0
        }

        return priority_map.get(priority, 0.3)

    def _calculate_type_factor(self, message_content: Dict[str, Any]) -> float:
        """Calculate message type-based factor."""
        msg_type = message_content.get('message_type', '').lower()

        # High-impact message types
        high_impact_types = [
            'governance_request', 'security_alert', 'critical_command',
            'policy_violation', 'emergency', 'blockchain_consensus'
        ]

        return 0.8 if msg_type in high_impact_types else 0.2


# Global scorer instance
_impact_scorer = None

def get_impact_scorer() -> ImpactScorer:
    """Get or create global impact scorer instance."""
    global _impact_scorer
    if _impact_scorer is None:
        _impact_scorer = ImpactScorer()
    return _impact_scorer

def calculate_message_impact(message_content: Dict[str, Any]) -> float:
    """
    Convenience function to calculate impact score for a message.

    Args:
        message_content: Message content dictionary

    Returns:
        Impact score between 0.0 and 1.0
    """
    scorer = get_impact_scorer()
    return scorer.calculate_impact_score(message_content)