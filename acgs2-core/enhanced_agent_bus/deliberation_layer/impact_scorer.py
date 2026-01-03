import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np

try:
    from ..models import AgentMessage, MessageType, Priority
    from ..utils import LRUCache, redact_error_message
except (ImportError, ValueError):
    from models import AgentMessage  # type: ignore

logger = logging.getLogger(__name__)

# Backend Detection
try:
    import torch
    from sklearn.metrics.pairwise import cosine_similarity
    from transformers import AutoModel, AutoTokenizer

    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

PROFILING_AVAILABLE = False


@dataclass
class ScoringConfig:
    semantic_weight: float = 0.3
    permission_weight: float = 0.2
    volume_weight: float = 0.1
    context_weight: float = 0.1
    drift_weight: float = 0.1
    priority_weight: float = 0.1
    type_weight: float = 0.1
    critical_priority_boost: float = 0.9
    high_semantic_boost: float = 0.8


@dataclass
class ImpactAnalysis:
    score: float
    factors: Dict[str, float]
    recommendation: str
    requires_deliberation: bool


class ImpactScorer:
    """Streamlined ImpactScorer v3.0.0 (ONNX/BERT optimized)."""

    def __init__(
        self,
        config: Optional[ScoringConfig] = None,
        model_name: str = "distilbert-base-uncased",
        use_onnx: bool = True,
    ):
        self.config = config or ScoringConfig()
        self.model_name = model_name
        self.use_onnx = use_onnx
        self._onnx_enabled = use_onnx if ONNX_AVAILABLE else False
        self._bert_enabled = False
        self.session = None

        if TRANSFORMERS_AVAILABLE:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                if self._onnx_enabled:
                    import pathlib
                    import os

                    # Path to the optimized ONNX model
                    model_dir = pathlib.Path(__file__).parent / "optimized_models"
                    onnx_path = model_dir / f"{model_name.replace('-', '_')}.onnx"

                    if onnx_path.exists():
                        # Create ONNX session with GPU if available
                        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
                        try:
                            self.session = ort.InferenceSession(str(onnx_path), providers=providers)

                            # Verify actual provider
                            active_providers = self.session.get_providers()
                            logger.info(f"ONNX Runtime active providers: {active_providers}")

                            if "CUDAExecutionProvider" in active_providers:
                                logger.info("GPU acceleration ENABLED ✓")
                            else:
                                logger.warning("GPU acceleration DISABLED - running on CPU fallback")

                            self._bert_enabled = True
                        except Exception as e:
                            logger.error(f"Failed to initialize ONNX session: {e}")
                            self._onnx_enabled = False
                    else:
                        logger.warning(f"ONNX model not found at {onnx_path}, falling back to CPU")
                        self._onnx_enabled = False

                if not self._onnx_enabled:
                    # Fallback to standard BERT if ONNX disabled or failed
                    self.model = AutoModel.from_pretrained(model_name).eval()
                    self._bert_enabled = True
            except Exception as e:
                logger.warning(f"Model load failed: {e}")

        self.high_impact_keywords = [
            "critical",
            "emergency",
            "security",
            "breach",
            "violation",
            "danger",
            "risk",
            "threat",
            "attack",
            "exploit",
            "vulnerability",
            "compromise",
            "governance",
            "policy",
            "regulation",
            "compliance",
            "legal",
            "audit",
            "financial",
            "transaction",
            "payment",
            "transfer",
            "blockchain",
            "consensus",
            "unauthorized",
            "abnormal",
            "suspicious",
            "alert",
        ]
        self._agent_rates = {}
        self._agent_history = {}
        self._keyword_embeddings = None

    def _extract_text_content(self, message: Any) -> str:
        if isinstance(message, dict):
            res = []
            if "content" in message:
                c = message["content"]
                res.append(str(c["text"]) if isinstance(c, dict) and "text" in c else str(c))
            if "payload" in message:
                p = message["payload"]
                if isinstance(p, dict) and "message" in p:
                    res.append(str(p["message"]))
            return " ".join(res)  # DO NOT .lower() here, tests are case sensitive
        return str(getattr(message, "content", ""))

    def _calculate_priority_factor(
        self, message: Any, context: Optional[Dict[str, Any]] = None
    ) -> float:
        p = None
        if context and "priority" in context:
            p = context["priority"]
        elif isinstance(message, dict) and "priority" in message:
            p = message["priority"]
        elif hasattr(message, "priority"):
            p = message.priority

        if p is None:
            return 0.5

        if hasattr(p, "name"):
            p_name = p.name.lower()
        elif isinstance(p, str):
            p_name = p.lower()
        else:
            p_name = str(p).lower()

        if "critical" in p_name or p_name == "3":
            return 1.0
        if "high" in p_name or p_name == "2":
            return 0.7
        if p_name in ["medium", "normal", "1"]:
            return 0.5
        if "low" in p_name or p_name == "0":
            return 0.2
        return 0.5

    def _calculate_type_factor(
        self, message: Any, context: Optional[Dict[str, Any]] = None
    ) -> float:
        t = None
        if context and "message_type" in context:
            t = context["message_type"]
        elif isinstance(message, dict) and "message_type" in message:
            t = message["message_type"]
        elif hasattr(message, "message_type"):
            t = message.message_type

        if t is None:
            return 0.2

        if hasattr(t, "name"):
            t_name = t.name.lower()
        elif isinstance(t, str):
            t_name = t.lower()
        else:
            t_name = str(t).lower()

        if "governance" in t_name or "constitutional" in t_name:
            return 0.8
        if "command" in t_name:
            return 0.4
        return 0.2

    def _calculate_permission_score(self, message: Any) -> float:
        tools = []
        if isinstance(message, dict) and "tools" in message:
            tools = message["tools"]
        elif hasattr(message, "tools"):
            tools = message.tools

        if not tools:
            return 0.1

        max_risk = 0.1
        for tool in tools:
            name = (
                tool
                if isinstance(tool, str)
                else (tool.get("name", "") if isinstance(tool, dict) else str(tool))
            ).lower()
            risk = 0.1
            if any(k in name for k in ["execute", "delete", "write", "submit", "transfer"]):
                risk = 0.9
            elif any(k in name for k in ["send", "update", "modify"]):
                risk = 0.5
            elif any(k in name for k in ["read", "get", "list", "view"]):
                risk = 0.2
            max_risk = max(max_risk, risk)
        return max_risk

    def _calculate_volume_score(self, agent_id: str) -> float:
        if not isinstance(agent_id, str):
            return 0.1
        rate = self._agent_rates.get(agent_id, 0)
        self._agent_rates[agent_id] = rate + 1
        if rate >= 150:
            return 1.0
        if rate >= 50:
            return 0.5
        if rate >= 20:
            return 0.2
        return 0.1

    def _calculate_context_score(
        self, message: Any, context: Optional[Dict[str, Any]] = None
    ) -> float:
        base = 0.2
        if isinstance(message, dict) and "payload" in message:
            payload = message["payload"]
            if isinstance(payload, dict) and payload.get("amount", 0) > 1000:
                base += 0.4
        elif hasattr(message, "payload"):
            if getattr(message.payload, "amount", 0) > 1000:
                base += 0.4
        return base

    def _calculate_drift_score(self, agent_id: str, current_score: float) -> float:
        if not isinstance(agent_id, str):
            return 0.0
        hist = self._agent_history.setdefault(agent_id, [])
        if not hist:
            hist.append(current_score)
            return 0.0
        avg = sum(hist) / len(hist)
        drift = abs(current_score - avg)
        hist.append(current_score)
        if len(hist) > 20:
            hist.pop(0)
        return min(1.0, drift * 2.0)

    def _calculate_semantic_score(self, message: Any) -> float:
        text = self._extract_text_content(message).strip().lower()
        if not text:
            return 0.0

        # Keyword-based scoring
        hits = sum(1 for k in self.high_impact_keywords if k in text)
        keyword_score = 0.1
        if hits >= 5:
            keyword_score = 1.0
        elif hits >= 3:
            keyword_score = 0.8
        elif hits > 0:
            keyword_score = 0.5

        # Embedding-based scoring (if BERT enabled)
        embedding_score = 0.0
        if self._bert_enabled:
            try:
                emb = self._get_embeddings(text)
                kw_emb = self._get_keyword_embeddings()
                # Use numpy for cosine similarity to avoid dependency issues in all environments
                if TRANSFORMERS_AVAILABLE:
                    from sklearn.metrics.pairwise import cosine_similarity

                    sim = cosine_similarity(emb, kw_emb)
                    embedding_score = float(np.max(sim))
                else:
                    # Manual cosine similarity fallback
                    sims = [cosine_similarity_fallback(emb, kw) for kw in kw_emb]
                    embedding_score = max(sims) if sims else 0.0
            except Exception:
                pass

        return max(keyword_score, embedding_score)

    def calculate_impact_score(self, message: Any, context: Dict[str, Any] = None) -> float:
        if not message and not context:
            return 0.1

        agent_id = "anonymous"
        if context and "agent_id" in context:
            agent_id = context["agent_id"]
        elif isinstance(message, dict) and "from_agent" in message:
            agent_id = message["from_agent"]
        elif hasattr(message, "from_agent"):
            agent_id = getattr(message, "from_agent", "anonymous")

        # Use pre-computed semantic score if provided in context
        if context and "semantic_override" in context:
            semantic = context["semantic_override"]
        else:
            semantic = self._calculate_semantic_score(message)

        scores = {
            "semantic": semantic,
            "permission": self._calculate_permission_score(message),
            "volume": self._calculate_volume_score(agent_id),
            "context": self._calculate_context_score(message, context),
            "drift": self._calculate_drift_score(agent_id, semantic),
            "priority": self._calculate_priority_factor(message, context),
            "type": self._calculate_type_factor(message, context),
        }

        weighted = sum(scores[k] * getattr(self.config, f"{k}_weight") for k in scores)

        if scores["priority"] >= 0.9:
            weighted = max(weighted, self.config.critical_priority_boost)
        if scores["semantic"] >= 0.8:
            weighted = max(weighted, self.config.high_semantic_boost)

        final = min(1.0, weighted)
        if hasattr(message, "impact_score"):
            message.impact_score = final
        return final

    def score_batch(self, messages: list) -> list[float]:
        """Process multiple messages efficiently with batching."""
        if not messages:
            return []

        # Extract text content for all messages
        texts = [self._extract_text_content(m).strip().lower() for m in messages]

        # If ML is disabled, fallback to sequential
        if not self._bert_enabled:
            return [self.calculate_impact_score(m) for m in messages]

        try:
            # Batch tokenization
            inputs = self.tokenizer(
                texts, return_tensors="np" if self._onnx_enabled else "pt",
                padding=True, truncation=True, max_length=512
            )

            if self._onnx_enabled and self.session:
                onnx_inputs = {k: v for k, v in inputs.items()}
                outputs = self.session.run(None, onnx_inputs)
                embeddings = outputs[0][:, 0, :]
            else:
                import torch
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()

            # For each message, calculate its semantic score using the embedding
            kw_emb = self._get_keyword_embeddings()

            results = []
            for i, message in enumerate(messages):
                emb = embeddings[i : i + 1]

                # Semantic score calculation (max similarity to keywords)
                if TRANSFORMERS_AVAILABLE:
                    from sklearn.metrics.pairwise import cosine_similarity
                    sim = cosine_similarity(emb, kw_emb)
                    embedding_score = float(np.max(sim))
                else:
                    sims = [cosine_similarity_fallback(emb, kw) for kw in kw_emb]
                    embedding_score = max(sims) if sims else 0.0

                # Keyword-based scoring (already in calculate_impact_score, but we want to avoid re-embedding)
                # We'll just call calculate_impact_score but override the semantic part
                # Actually, better to refactor calculate_impact_score to accept an optional semantic score
                results.append(self._calculate_impact_with_semantic(message, embedding_score))

            return results
        except Exception as e:
            logger.error(f"Batch scoring failed: {e}")
            return [self.calculate_impact_score(m) for m in messages]

    def _calculate_impact_with_semantic(self, message: Any, semantic_score: float) -> float:
        """Helper to calculate impact score with a pre-computed semantic score."""
        # This is a simplified version of calculate_impact_score logic
        # For production, we should probably refactor calculate_impact_score to avoid duplication

        # Re-use the keyword hits logic for the semantic part
        text = self._extract_text_content(message).strip().lower()
        hits = sum(1 for k in self.high_impact_keywords if k in text)
        keyword_score = 0.1
        if hits >= 5:
            keyword_score = 1.0
        elif hits >= 3:
            keyword_score = 0.8
        elif hits > 0:
            keyword_score = 0.5

        final_semantic = max(keyword_score, semantic_score)

        # For the rest of the factors, we'll just call the individual methods
        # To avoid code duplication, in a real scenario I'd refactor calculate_impact_score
        # But here I'll just use the existing one for now as a fallback if this gets complex
        return self.calculate_impact_score(message, context={"semantic_override": final_semantic})

    async def calculate_impact(self, message: AgentMessage) -> float:
        return self.calculate_impact_score(message)

    def _get_embeddings(self, text: str) -> np.ndarray:
        if not self._bert_enabled:
            return np.zeros((1, 768))

        try:
            inputs = self.tokenizer(
                text, return_tensors="np" if self._onnx_enabled else "pt",
                padding=True, truncation=True, max_length=512
            )

            if self._onnx_enabled and self.session:
                # Prepare inputs for ONNX
                onnx_inputs = {k: v for k, v in inputs.items()}
                outputs = self.session.run(None, onnx_inputs)
                # DistilBERT output is [last_hidden_state]
                return outputs[0][:, 0, :]  # CLS token
            else:
                # Standard PyTorch BERT
                import torch
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    return outputs.last_hidden_state[:, 0, :].cpu().numpy()
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return np.zeros((1, 768))

    def _get_keyword_embeddings(self) -> np.ndarray:
        if self._keyword_embeddings is None:
            if not self._bert_enabled:
                self._keyword_embeddings = np.zeros((len(self.high_impact_keywords), 768))
            else:
                embs = []
                for kw in self.high_impact_keywords:
                    embs.append(self._get_embeddings(kw))
                self._keyword_embeddings = np.vstack(embs)
        return self._keyword_embeddings


def cosine_similarity_fallback(a: Any, b: Any) -> float:
    try:
        a = np.array(a).flatten()
        b = np.array(b).flatten()
        if a.size == 0 or b.size == 0:
            return 0.0
        norm_a, norm_b = np.linalg.norm(a), np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
    except Exception:
        return 0.0


def get_gpu_decision_matrix():
    return {}


def get_reasoning_matrix():
    return {}


def get_risk_profile():
    return {}


def get_profiling_report():
    return {}


def get_vector_space_metrics():
    return {}


def reset_impact_scorer():
    global _global_scorer
    _global_scorer = None


def reset_profiling():
    pass


_global_scorer = None


def get_impact_scorer(**kwargs):
    global _global_scorer
    if not _global_scorer:
        _global_scorer = ImpactScorer(**kwargs)
    return _global_scorer


def calculate_message_impact(message: AgentMessage) -> float:
    return get_impact_scorer().calculate_impact_score(message)
