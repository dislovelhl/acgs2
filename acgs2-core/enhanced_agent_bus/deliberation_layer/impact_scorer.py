"""
ACGS-2 Deliberation Layer - Impact Scorer
Uses BERT embeddings to calculate impact scores for decision-making.
Constitutional Hash: cdd01ef066bc6cf2
"""

import logging
import numpy as np
from dataclasses import dataclass
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)
try:
    from transformers import AutoTokenizer, AutoModel
    import torch
    from sklearn.metrics.pairwise import cosine_similarity
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

try:
    import mlflow
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False

try:
    from ..models import Priority, MessageType, MessagePriority
except ImportError:
    # Fallback if not in package context
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from models import Priority, MessageType, MessagePriority # type: ignore

def cosine_similarity_fallback(a, b):
    """Fallback implementation of cosine similarity using dot product."""
    a = np.array(a).flatten()
    b = np.array(b).flatten()
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return np.dot(a, b) / (norm_a * norm_b)


@dataclass
class ScoringConfig:
    """Configuration for impact scoring weights."""
    semantic_weight: float = 0.30
    permission_weight: float = 0.20
    volume_weight: float = 0.10
    context_weight: float = 0.10
    drift_weight: float = 0.15
    priority_weight: float = 0.10
    type_weight: float = 0.05
    
    # Boost thresholds
    critical_priority_boost: float = 0.9
    high_semantic_boost: float = 0.8


class ImpactScorer:
    """Calculates impact scores using multi-dimensional analysis with configurable weights.

    The scorer evaluates messages based on semantic content (using DistilBERT/ONNX),
    requested tool permissions, request volume/rates, and historical context.

    Attributes:
        high_impact_keywords (List[str]): Keywords used for baseline semantic comparison.
        config (ScoringConfig): Configuration for scoring weights.
    """

    def __init__(self, model_name: str = 'distilbert-base-uncased', onnx_path: Optional[str] = None, config: Optional[ScoringConfig] = None):
        """Initializes the ImpactScorer with a transformer model and configuration.

        Args:
            model_name (str): The name of the pre-trained model to use.
            onnx_path (Optional[str]): Path to an ONNX quantized model file.
            config (Optional[ScoringConfig]): Scoring configuration. Defaults to standard weights.
        """
        self.model_name = model_name
        self.onnx_path = onnx_path
        self.config = config or ScoringConfig()
        self._bert_enabled = False
        self._onnx_enabled = False

        if TRANSFORMERS_AVAILABLE:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                
                if ONNX_AVAILABLE and onnx_path:
                    self.session = ort.InferenceSession(onnx_path)
                    self._onnx_enabled = True
                    logger.info(f"ONNX model loaded from {onnx_path}")
                else:
                    self.model = AutoModel.from_pretrained(model_name)
                    self.model.eval()
                    self._bert_enabled = True
            except Exception as e:
                logger.warning(f"Failed to load AI model: {e}. Falling back to keyword matching.")
        
        if MLFLOW_AVAILABLE:
            # Placeholder for MLflow model versioning
            try:
                mlflow.log_param("model_name", model_name)
                mlflow.log_param("onnx_enabled", self._onnx_enabled)
            except Exception:
                pass

        # Pre-defined high-impact keywords for baseline comparison
        self.high_impact_keywords = [
            "critical", "emergency", "security", "breach", "violation", "danger",
            "risk", "threat", "attack", "exploit", "vulnerability", "compromise",
            "governance", "policy", "regulation", "compliance", "legal", "audit",
            "financial", "transaction", "payment", "transfer", "blockchain", "consensus",
            "unauthorized", "abnormal", "suspicious", "alert"
        ]

        # Cache for keyword embeddings
        self._keyword_embeddings = None

        # Volume tracking (simplified for demo)
        self._agent_request_rates: Dict[str, list] = {}
        self._rate_window_seconds = 60

        # Behavioral context drift tracking
        self._agent_impact_history: Dict[str, list] = {}
        self._history_window = 20
        self._drift_threshold = 0.3 # Deviation from mean to trigger anomaly

    def _get_embeddings(self, text: str) -> np.ndarray:
        """Retrieves embeddings for the input text.

        Args:
            text (str): The input text to embed.

        Returns:
            np.ndarray: The resulting embedding vector.
        """
        if not (self._bert_enabled or self._onnx_enabled):
            return np.zeros((1, 768)) # Dummy embedding

        if self._onnx_enabled:
            # ONNX inference path
            inputs = self.tokenizer(text, return_tensors='np', truncation=True,
                                   padding=True, max_length=512)
            onnx_inputs = {k: v.astype(np.int64) for k, v in inputs.items()}
            outputs = self.session.run(None, onnx_inputs)
            # Use mean pooling of last hidden state (assumed to be the first output)
            embeddings = outputs[0].mean(axis=1)
        else:
            # PyTorch inference path
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
            if self._bert_enabled or self._onnx_enabled:
                 message_embedding = self._get_embeddings(text_content)
                 keyword_embedding = self._get_keyword_embeddings()
                 if TRANSFORMERS_AVAILABLE:
                     semantic_score = float(cosine_similarity(message_embedding, keyword_embedding)[0][0])
                 else:
                     semantic_score = float(cosine_similarity_fallback(message_embedding, keyword_embedding))
            else:
                 # Fallback: simple keyword matching
                 hits = sum(1 for kw in self.high_impact_keywords if kw in text_content.lower())
                 # logical scoring: 1 hit = 0.3, 2 hits = 0.6, 3+ = 0.9
                 semantic_score = min(0.9, hits * 0.3)

        # 2. Permission Score
        permission_score = self._calculate_permission_score(message_content)

        # 3. Volume Score
        agent_id = context.get('agent_id', 'unknown') if context else 'unknown'
        volume_score = self._calculate_volume_score(agent_id)

        # 4. Context/History Score (Simplified)
        context_score = self._calculate_context_score(message_content, context)

        # 4a. Behavioral Drift Score (Anomaly Detection)
        drift_score = self._calculate_drift_score(agent_id, combined_baseline=context_score)

        # 5. Priority & Type Factors (Legacy)
        priority_factor = self._calculate_priority_factor(message_content, context)
        type_factor = self._calculate_type_factor(message_content, context)

        # Weighted combination using config
        combined_score = (
            (semantic_score * self.config.semantic_weight) +
            (permission_score * self.config.permission_weight) +
            (volume_score * self.config.volume_weight) +
            (context_score * self.config.context_weight) +
            (drift_score * self.config.drift_weight) +
            (priority_factor * self.config.priority_weight) +
            (type_factor * self.config.type_weight)
        )

        # Normalize total weight in case customized weights don't sum to 1.0
        total_weight = (
            self.config.semantic_weight +
            self.config.permission_weight +
            self.config.volume_weight + 
            self.config.context_weight +
            self.config.drift_weight +
            self.config.priority_weight +
            self.config.type_weight
        )
        
        if total_weight > 0:
            combined_score = combined_score / total_weight

        # Non-linear boost: Critical priority or high semantic relevance
        boosted_score = combined_score
        
        if priority_factor >= 1.0: # Critical
            boosted_score = max(boosted_score, self.config.critical_priority_boost)
            
        if semantic_score > 0.8:
            boosted_score = max(boosted_score, self.config.high_semantic_boost)

        return max(0.0, min(1.0, boosted_score))

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

    def _calculate_drift_score(self, agent_id: str, combined_baseline: float) -> float:
        """
        Detects behavioral drift by comparing current baseline score to historical mean.
        Identifies deviations from established 'safety envelopes'.
        """
        if agent_id == 'unknown' or agent_id not in self._agent_impact_history:
            if agent_id != 'unknown':
                self._agent_impact_history[agent_id] = [combined_baseline]
            return 0.0

        history = self._agent_impact_history[agent_id]
        mean_impact = sum(history) / len(history)

        # Calculate deviation
        deviation = abs(combined_baseline - mean_impact)

        # Update history
        history.append(combined_baseline)
        if len(history) > self._history_window:
            history.pop(0)

        # Drift is high if deviation exceeds threshold
        if deviation > self._drift_threshold:
            logger.warning(f"Behavioral context drift detected for agent {agent_id}: deviation={deviation:.2f}")
            return min(1.0, (deviation / self._drift_threshold) * 0.5)

        return 0.0

    def _extract_text_content(self, message_content: Dict[str, Any]) -> str:
        """Extract textual content from message dictionary."""
        text_parts = []

        # Extract from common fields
        for field in ['content', 'payload', 'description', 'reason', 'details', 'action', 'type', 'title', 'subject']:
            if field in message_content:
                value = message_content[field]
                if isinstance(value, str):
                    text_parts.append(value)
                elif isinstance(value, dict):
                    # Recursively extract from nested dict
                    text_parts.append(self._extract_text_content(value))

        return " ".join(text_parts)

    def _calculate_priority_factor(self, message_content: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> float:
        """Calculate priority-based factor using Priority enum."""
        priority_val = message_content.get('priority')
        
        # Check context if not in content
        if priority_val is None and context:
            priority_val = context.get('priority')
        
        # Map Priority enum or its value/name to 0.0-1.0
        p = Priority.MEDIUM
        
        # Use name/value comparison to avoid identity issues with different imports
        priority_name = ""
        if hasattr(priority_val, "name"):
            priority_name = priority_val.name.upper()
        elif isinstance(priority_val, str):
            priority_name = priority_val.upper()

        if priority_name in [p.name for p in Priority]:
            p = Priority[priority_name]
        elif priority_name in [p.name for p in MessagePriority]:
            # Legacy conversion
            conversion = {
                "CRITICAL": Priority.CRITICAL,
                "HIGH": Priority.HIGH,
                "NORMAL": Priority.MEDIUM,
                "MEDIUM": Priority.MEDIUM,
                "LOW": Priority.LOW
            }
            p = conversion.get(priority_name, Priority.MEDIUM)
        elif isinstance(priority_val, int):
            try:
                # Handle potential legacy int values (0=Critical in MessagePriority vs 0=Low in Priority)
                # Heuristic: if value > 3, assume it's just wrong and default to medium
                # If it's 0-3, we need to know strictly if we are using new or old system.
                # For safety in this transition phase, if we receive an int, we assume it adheres to
                # the new Priority enum (0=Low, 3=Critical) unless context strongly implies otherwise.
                p = Priority(priority_val)
            except ValueError:
                p = Priority.MEDIUM
        elif isinstance(priority_val, str):
            try:
                # Try direct name matching first
                p = Priority[priority_val.upper()]
            except KeyError:
                # Handle legacy names "NORMAL" -> MEDIUM
                if priority_val.upper() == "NORMAL":
                    p = Priority.MEDIUM
                else:
                    p = Priority.MEDIUM

        priority_map = {
            Priority.LOW: 0.1,
            Priority.MEDIUM: 0.3,
            Priority.NORMAL: 0.3, # Alias
            Priority.HIGH: 0.7,
            Priority.CRITICAL: 1.0
        }

        return priority_map.get(p, 0.3)

    def _calculate_type_factor(self, message_content: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> float:
        """Calculate message type-based factor using MessageType enum."""
        msg_type_val = message_content.get('message_type')

        # Check context if not in content
        if msg_type_val is None and context:
            msg_type_val = context.get('message_type')

        if isinstance(msg_type_val, MessageType):
            mt = msg_type_val
        elif isinstance(msg_type_val, str):
            try:
                mt = MessageType(msg_type_val.lower())
            except ValueError:
                mt = MessageType.COMMAND
        else:
            mt = MessageType.COMMAND

        # High-impact message types
        high_impact_types = [
            MessageType.GOVERNANCE_REQUEST,
            MessageType.CONSTITUTIONAL_VALIDATION,
            MessageType.TASK_REQUEST # Sometimes critical
        ]

        return 0.8 if mt in high_impact_types else 0.2


    def validate_with_baseline(self, message_content: Dict[str, Any], baseline_scorer: 'ImpactScorer') -> bool:
        """Compares current score with a baseline scorer for validation.

        Args:
            message_content: Message content dictionary
            baseline_scorer: Another ImpactScorer instance (e.g., using bert-base-uncased)

        Returns:
            True if scores are within acceptable threshold (0.1)
        """
        current_score = self.calculate_impact_score(message_content)
        baseline_score = baseline_scorer.calculate_impact_score(message_content)
        return abs(current_score - baseline_score) < 0.1


# Global scorer instance
_impact_scorer = None

def get_impact_scorer(model_name: str = 'distilbert-base-uncased', onnx_path: Optional[str] = None, config: Optional[ScoringConfig] = None) -> ImpactScorer:
    """Get or create global impact scorer instance.

    Args:
        model_name: Transformers model name
        onnx_path: Optional path to ONNX model
        config: Optional scoring configuration
    """
    global _impact_scorer
    if _impact_scorer is None:
        _impact_scorer = ImpactScorer(model_name=model_name, onnx_path=onnx_path, config=config)
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