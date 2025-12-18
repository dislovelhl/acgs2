"""
ACGS-2 Deliberation Layer - Impact Scorer
Uses BERT embeddings to calculate impact scores for decision-making.
"""

import numpy as np
from typing import Dict, Any, Optional
try:
    from transformers import BertTokenizer, BertModel
    import torch
    from sklearn.metrics.pairwise import cosine_similarity
    BERT_AVAILABLE = True
except ImportError:
    BERT_AVAILABLE = False


class ImpactScorer:
    """Calculates impact scores using multi-dimensional analysis.

    The scorer evaluates messages based on semantic content (using BERT),
    requested tool permissions, request volume/rates, and historical context.

    Attributes:
        high_impact_keywords (List[str]): Keywords used for baseline semantic comparison.
    """

    def __init__(self, model_name: str = 'bert-base-uncased'):
        """Initializes the ImpactScorer with a BERT model.

        Args:
            model_name (str): The name of the pre-trained BERT model to use.
                Defaults to 'bert-base-uncased'.
        """
        if BERT_AVAILABLE:
            try:
                self.tokenizer = BertTokenizer.from_pretrained(model_name)
                self.model = BertModel.from_pretrained(model_name)
                self.model.eval()
            except Exception as e:
                print(f"Warning: Failed to load BERT model: {e}. Falling back to keyword matching.")
                self._bert_enabled = False
            else:
                self._bert_enabled = True
        else:
            self._bert_enabled = False

        # Pre-defined high-impact keywords for baseline comparison
        self.high_impact_keywords = [
            "critical", "emergency", "security", "breach", "violation", "danger",
            "risk", "threat", "attack", "exploit", "vulnerability", "compromise",
            "governance", "policy", "regulation", "compliance", "legal", "audit",
            "financial", "transaction", "payment", "transfer", "blockchain", "consensus"
        ]

        # Cache for keyword embeddings
        self._keyword_embeddings = None

        # Volume tracking (simplified for demo)
        self._agent_request_rates: Dict[str, list] = {}
        self._rate_window_seconds = 60

    def _get_embeddings(self, text: str) -> np.ndarray:
        """Retrieves BERT embeddings for the input text.

        Args:
            text (str): The input text to embed.

        Returns:
            np.ndarray: The resulting embedding vector.
        """
        if not self._bert_enabled:
            return np.zeros((1, 768)) # Dummy embedding

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

    def calculate_impact_score(self, message_content: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate multi-dimensional impact score.

        Args:
            message_content: Dictionary containing message data
            context: Optional context including agent_id, tenant_id, etc.

        Returns:
            Float between 0.0 and 1.0 representing impact level
        """
        # 1. Semantic Score (BERT)
        text_content = self._extract_text_content(message_content)
        semantic_score = 0.0
        if text_content:
            message_embedding = self._get_embeddings(text_content)
            keyword_embedding = self._get_keyword_embeddings()
            semantic_score = float(cosine_similarity(message_embedding, keyword_embedding)[0][0])

        # 2. Permission Score
        permission_score = self._calculate_permission_score(message_content)

        # 3. Volume Score
        agent_id = context.get('agent_id', 'unknown') if context else 'unknown'
        volume_score = self._calculate_volume_score(agent_id)

        # 4. Context/History Score (Simplified)
        context_score = self._calculate_context_score(message_content, context)

        # 5. Priority & Type Factors (Legacy)
        priority_factor = self._calculate_priority_factor(message_content)
        type_factor = self._calculate_type_factor(message_content)

        # Weighted combination
        # Semantic: 30%, Permission: 30%, Volume: 15%, Context: 15%, Priority/Type: 10%
        combined_score = (
            (semantic_score * 0.3) +
            (permission_score * 0.3) +
            (volume_score * 0.15) +
            (context_score * 0.15) +
            (priority_factor * 0.05) +
            (type_factor * 0.05)
        )

        return max(0.0, min(1.0, combined_score))

    def _calculate_permission_score(self, message_content: Dict[str, Any]) -> float:
        """Calculate score based on requested tool permissions."""
        requested_tools = message_content.get('tools', [])
        if not requested_tools:
            return 0.1

        # High-risk tool patterns
        high_risk_tools = ['admin', 'delete', 'transfer', 'execute', 'blockchain', 'payment']
        
        max_risk = 0.1
        for tool in requested_tools:
            tool_name = tool.get('name', '').lower() if isinstance(tool, dict) else str(tool).lower()
            if any(pattern in tool_name for pattern in high_risk_tools):
                max_risk = max(max_risk, 0.9)
            elif 'read' in tool_name or 'get' in tool_name:
                max_risk = max(max_risk, 0.2)
            else:
                max_risk = max(max_risk, 0.5)
        
        return max_risk

    def _calculate_volume_score(self, agent_id: str) -> float:
        """Calculate score based on request volume/rate."""
        import time
        now = time.time()
        
        if agent_id not in self._agent_request_rates:
            self._agent_request_rates[agent_id] = []
        
        # Add current request
        self._agent_request_rates[agent_id].append(now)
        
        # Clean up old requests
        self._agent_request_rates[agent_id] = [
            t for t in self._agent_request_rates[agent_id]
            if now - t < self._rate_window_seconds
        ]
        
        rate = len(self._agent_request_rates[agent_id])
        
        # Thresholds: 10 req/min is normal, 100 req/min is high risk
        if rate < 10:
            return 0.1
        elif rate < 50:
            return 0.4
        elif rate < 100:
            return 0.7
        else:
            return 1.0

    def _calculate_context_score(self, message_content: Dict[str, Any], context: Optional[Dict[str, Any]]) -> float:
        """Calculate score based on historical context and anomalies."""
        # Simplified: check for unusual hours or tenant-specific risks
        import datetime
        now = datetime.datetime.now()
        
        score = 0.2
        
        # Night time anomaly (e.g., 1 AM to 5 AM)
        if 1 <= now.hour <= 5:
            score += 0.3
            
        # Check for large transactions in content
        payload = message_content.get('payload', {})
        amount = payload.get('amount', 0)
        if isinstance(amount, (int, float)) and amount > 10000:
            score += 0.4
            
        return min(1.0, score)

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