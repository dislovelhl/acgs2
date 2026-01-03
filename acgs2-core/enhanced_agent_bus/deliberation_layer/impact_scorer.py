"""
Impact Scorer v3.1.0 - ML-Powered Impact Assessment

This module provides ML-based impact scoring for governance decisions using:
1. ONNX Runtime (fastest) - GPU-accelerated inference
2. PyTorch Transformers (fallback) - CPU/GPU inference
3. NumPy heuristics (final fallback) - Keyword-based scoring

The fallback cascade ensures the service remains operational even when
ML dependencies are unavailable.
"""
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np

try:
    from ..models import AgentMessage, MessageType, Priority
    from ..utils import LRUCache, redact_error_message
except (ImportError, ValueError):
    from models import AgentMessage  # type: ignore

logger = logging.getLogger(__name__)

# ===== Backend Detection with Proper Fallback Cascade =====

# ONNX Runtime availability check
ONNX_AVAILABLE = False
try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
    logger.info(f"ONNX Runtime available: {ort.__version__}")
except ImportError:
    logger.info("ONNX Runtime not available - will use PyTorch or heuristics fallback")

# Transformers availability check
TRANSFORMERS_AVAILABLE = False
try:
    import torch
    from sklearn.metrics.pairwise import cosine_similarity
    from transformers import AutoModel, AutoTokenizer
    TRANSFORMERS_AVAILABLE = True
    logger.info(f"Transformers available: torch={torch.__version__}")
except ImportError:
    logger.info("Transformers not available - will use heuristics fallback")

# Feature flags based on availability (can be overridden via environment)
USE_TRANSFORMERS = TRANSFORMERS_AVAILABLE and os.getenv("USE_TRANSFORMERS", "true").lower() == "true"
USE_ONNX = ONNX_AVAILABLE and os.getenv("USE_ONNX_INFERENCE", "true").lower() == "true"

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
    """
    ImpactScorer v3.1.0 - ML-Powered Governance Impact Assessment

    Implements a fallback cascade:
    1. ONNX Runtime (fastest) - GPU-accelerated when available
    2. PyTorch Transformers (fallback) - Full model inference
    3. NumPy heuristics (final fallback) - Keyword-based scoring

    Feature flags:
    - USE_TRANSFORMERS: Enable/disable ML inference (env: USE_TRANSFORMERS)
    - USE_ONNX: Enable/disable ONNX optimization (env: USE_ONNX_INFERENCE)
    """

    # Class-level model cache for singleton behavior
    _model_instance: Optional[Any] = None
    _tokenizer_instance: Optional[Any] = None
    _onnx_session_instance: Optional[Any] = None

    def __init__(
        self,
        config: Optional[ScoringConfig] = None,
        model_name: str = "distilbert-base-uncased",
        use_onnx: bool = True,
        tokenization_cache_size: int = 1000,
        onnx_model_path: Optional[str] = None,
    ):
        self.config = config or ScoringConfig()
        self.model_name = model_name
        self.use_onnx = use_onnx and USE_ONNX

        # State flags - will be set during lazy loading
        self._onnx_enabled = False
        self._bert_enabled = False
        self._model_loaded = False

        # Model references (lazy loaded)
        self.model = None
        self.tokenizer = None
        self.onnx_session = None

        # Embeddings cache for performance
        self._embeddings_cache: Dict[str, np.ndarray] = {}

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
        self._agent_rates: Dict[str, int] = {}
        self._agent_history: Dict[str, List[float]] = {}
        self._keyword_embeddings: Optional[np.ndarray] = None

    def _ensure_model_loaded(self) -> bool:
        """
        Lazy load model on first use to reduce startup time.
        Returns True if ML inference is available, False otherwise.

        Implements fallback cascade:
        1. Try ONNX Runtime first (fastest)
        2. Fall back to PyTorch Transformers
        3. Use heuristics if both fail
        """
        if self._model_loaded:
            return self._bert_enabled or self._onnx_enabled

        self._model_loaded = True

        # Try ONNX first (fastest path)
        if self.use_onnx and ONNX_AVAILABLE:
            if self._load_onnx_model():
                return True

        # Fall back to PyTorch Transformers
        if USE_TRANSFORMERS and TRANSFORMERS_AVAILABLE:
            if self._load_transformer_model():
                return True

        logger.warning("ML models unavailable - using keyword-based heuristics fallback")
        return False

    def _load_onnx_model(self) -> bool:
        """Load ONNX model for optimized inference."""
        try:
            # Check for cached instance first
            if ImpactScorer._onnx_session_instance is not None:
                self.onnx_session = ImpactScorer._onnx_session_instance
                self.tokenizer = ImpactScorer._tokenizer_instance
                self._onnx_enabled = True
                logger.info("ONNX session reused from cache")
                return True

            # Load tokenizer
            from transformers import AutoTokenizer
            cache_dir = os.getenv("TRANSFORMERS_CACHE", None)
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                cache_dir=cache_dir
            )

            # Find ONNX model file
            onnx_path = self._find_onnx_model_path()
            if onnx_path is None:
                logger.info("ONNX model not found - will use PyTorch fallback")
                return False

            # Create ONNX session with GPU if available
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            self.onnx_session = ort.InferenceSession(str(onnx_path), providers=providers)

            # Verify GPU provider was loaded
            active_providers = self.onnx_session.get_providers()
            if 'CUDAExecutionProvider' in active_providers:
                logger.info("GPU acceleration ENABLED ✓ - Using ONNX with CUDA")
            else:
                logger.info("GPU acceleration DISABLED - Using ONNX with CPU fallback")

            # Cache for reuse
            ImpactScorer._onnx_session_instance = self.onnx_session
            ImpactScorer._tokenizer_instance = self.tokenizer
            self._onnx_enabled = True

            return True

        except Exception as e:
            logger.warning(f"ONNX model load failed: {e}")
            return False

    def _find_onnx_model_path(self) -> Optional[Path]:
        """Find ONNX model file with configurable path resolution."""
        # Check environment variable first
        env_path = os.getenv("ONNX_MODEL_PATH")
        if env_path and Path(env_path).exists():
            return Path(env_path)

        # Check relative paths from module location
        base_paths = [
            Path(__file__).parent / "optimized_models",
            Path(__file__).parent.parent / "optimized_models",
            Path.cwd() / "optimized_models",
        ]

        model_filename = "distilbert_base_uncased.onnx"

        for base in base_paths:
            model_path = base / model_filename
            if model_path.exists():
                return model_path

        return None

    def _load_transformer_model(self) -> bool:
        """Load PyTorch Transformers model for inference."""
        try:
            # Check for cached instance first
            if ImpactScorer._model_instance is not None:
                self.model = ImpactScorer._model_instance
                self.tokenizer = ImpactScorer._tokenizer_instance
                self._bert_enabled = True
                logger.info("Transformers model reused from cache")
                return True

            from transformers import AutoModel, AutoTokenizer
            cache_dir = os.getenv("TRANSFORMERS_CACHE", None)

            # Load tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                cache_dir=cache_dir
            )
            self.model = AutoModel.from_pretrained(
                self.model_name,
                cache_dir=cache_dir
            )
            self.model.eval()  # Set to evaluation mode

            # Cache for reuse
            ImpactScorer._model_instance = self.model
            ImpactScorer._tokenizer_instance = self.tokenizer
            self._bert_enabled = True

            logger.info(f"Transformers model loaded: {self.model_name}")
            return True

        except Exception as e:
            logger.warning(f"Transformers model load failed: {e}")
            return False

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
        """
        Calculate semantic impact score using ML embeddings or keyword heuristics.

        Uses fallback cascade:
        1. ONNX/BERT embedding similarity (if available)
        2. Keyword-based heuristics (always available)
        """
        text = self._extract_text_content(message).strip().lower()
        if not text:
            return 0.0

        # Keyword-based scoring (always computed as baseline)
        hits = sum(1 for k in self.high_impact_keywords if k in text)
        keyword_score = 0.1
        if hits >= 5:
            keyword_score = 1.0
        elif hits >= 3:
            keyword_score = 0.8
        elif hits > 0:
            keyword_score = 0.5

        # Embedding-based scoring (if ML available)
        embedding_score = 0.0
        if self._ensure_model_loaded() and (self._bert_enabled or self._onnx_enabled):
            try:
                emb = self._get_embeddings(text)
                kw_emb = self._get_keyword_embeddings()

                # Skip if embeddings are zeros (fallback mode)
                if np.any(emb) and np.any(kw_emb):
                    if TRANSFORMERS_AVAILABLE:
                        from sklearn.metrics.pairwise import cosine_similarity
                        sim = cosine_similarity(emb.reshape(1, -1) if emb.ndim == 1 else emb, kw_emb)
                        embedding_score = float(np.max(sim))
                    else:
                        # Manual cosine similarity fallback
                        emb_flat = emb.flatten()
                        sims = [cosine_similarity_fallback(emb_flat, kw) for kw in kw_emb]
                        embedding_score = max(sims) if sims else 0.0

            except Exception as e:
                logger.debug(f"Embedding-based scoring failed: {e}")

        return max(keyword_score, embedding_score)

    async def calculate_impact_score_async(self, message: Any, context: Dict[str, Any] = None) -> float:
        if not message and not context:
            return 0.1

        agent_id = "anonymous"
        if context and "agent_id" in context:
            agent_id = context["agent_id"]
        elif isinstance(message, dict) and "from_agent" in message:
            agent_id = message["from_agent"]
        elif hasattr(message, "from_agent"):
            agent_id = getattr(message, "from_agent", "anonymous")

        # Yield control to event loop for cooperative multitasking
        await asyncio.sleep(0)

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

    async def calculate_impact(self, message: AgentMessage) -> float:
        return self.calculate_impact_score(message)

    def batch_score_impact(
        self,
        messages: List[Any],
        contexts: Optional[List[Optional[Dict[str, Any]]]] = None,
    ) -> List[float]:
        """
        Process multiple messages efficiently with batching.

        This method provides optimized batch inference for high-throughput scenarios.
        When ONNX/BERT is enabled, it batches tokenization and inference operations
        for better throughput. Falls back to sequential processing when ML is unavailable.

        Args:
            messages: List of messages to score. Each message can be a dict or AgentMessage.
            contexts: Optional list of context dicts corresponding to each message.
                     If None, empty contexts are used for all messages.

        Returns:
            List of impact scores (floats between 0.0 and 1.0).

        Example:
            >>> scorer = ImpactScorer()
            >>> messages = [
            ...     {"content": "critical security alert"},
            ...     {"content": "normal status check"},
            ... ]
            >>> scores = scorer.batch_score_impact(messages)
            >>> print(scores)  # [0.85, 0.25]
        """
        if not messages:
            return []

        # Normalize contexts list
        if contexts is None:
            contexts = [None] * len(messages)
        elif len(contexts) != len(messages):
            raise ValueError(
                f"contexts length ({len(contexts)}) must match messages length ({len(messages)})"
            )

        # Extract text content from all messages for batch processing
        texts = [self._extract_text_content(msg) for msg in messages]

        # If ONNX/BERT enabled with batch support, use optimized path
        if self._onnx_enabled and self._bert_enabled and TRANSFORMERS_AVAILABLE:
            return self._batch_score_with_embeddings(messages, texts, contexts)

        # Fallback to sequential processing for keyword-based scoring
        return self._batch_score_sequential(messages, contexts)

    def _batch_score_with_embeddings(
        self,
        messages: List[Any],
        texts: List[str],
        contexts: List[Optional[Dict[str, Any]]],
    ) -> List[float]:
        """
        Batch scoring using BERT embeddings.

        Performs batch tokenization with caching and inference for optimal throughput.
        Uses _tokenize_batch for cached tokenization when texts repeat across batches.
        """
        try:
            # Filter out empty texts and track their indices
            non_empty_indices = [i for i, t in enumerate(texts) if t.strip()]
            non_empty_texts = [texts[i] for i in non_empty_indices]

            if not non_empty_texts:
                # All texts are empty - return low scores
                return [0.0] * len(messages)

            # Batch tokenization with caching (uses _tokenize_batch helper)
            batch_inputs = self._tokenize_batch(non_empty_texts, use_cache=True)
            if batch_inputs is None:
                # Tokenization failed, fall back to sequential
                return self._batch_score_sequential(messages, contexts)

            # Batch inference
            with torch.no_grad():
                outputs = self.model(**batch_inputs)
                # Extract [CLS] token embeddings for each text
                batch_embeddings = outputs.last_hidden_state[:, 0, :].numpy()

            # Get keyword embeddings for similarity computation
            keyword_embs = self._get_keyword_embeddings()

            # Compute batch similarities using vectorized operations
            similarities = cosine_similarity(batch_embeddings, keyword_embs)
            max_similarities = np.max(similarities, axis=1)

            # Build result array with semantic scores
            semantic_scores = np.zeros(len(messages))
            for idx, orig_idx in enumerate(non_empty_indices):
                semantic_scores[orig_idx] = float(max_similarities[idx])

            # Compute full impact scores for all messages
            results = []
            for i, msg in enumerate(messages):
                ctx = contexts[i]
                # Combine semantic score with other factors
                score = self._compute_combined_score(msg, ctx, semantic_scores[i])
                results.append(score)

            return results

        except Exception as e:
            logger.debug("Batch embedding inference failed, falling back to sequential: %s", e)
            return self._batch_score_sequential(messages, contexts)

    def _batch_score_sequential(
        self,
        messages: List[Any],
        contexts: List[Optional[Dict[str, Any]]],
    ) -> List[float]:
        """
        Sequential scoring fallback for keyword-based processing.

        Used when ONNX/BERT is not available or batch inference fails.
        """
        return [
            self.calculate_impact_score(msg, ctx)
            for msg, ctx in zip(messages, contexts)
        ]

    def _compute_combined_score(
        self,
        message: Any,
        context: Optional[Dict[str, Any]],
        semantic_score: float,
    ) -> float:
        """
        Compute combined impact score from semantic and other factors.

        Mirrors the logic in calculate_impact_score but uses pre-computed semantic score.
        """
        agent_id = "anonymous"
        if context and "agent_id" in context:
            agent_id = context["agent_id"]
        elif isinstance(message, dict) and "from_agent" in message:
            agent_id = message["from_agent"]
        elif hasattr(message, "from_agent"):
            agent_id = getattr(message, "from_agent", "anonymous")

        # Use pre-computed semantic score but also check keywords for fallback
        text = self._extract_text_content(message).strip().lower()
        keyword_score = 0.1
        if text:
            hits = sum(1 for k in self.high_impact_keywords if k in text)
            if hits >= 5:
                keyword_score = 1.0
            elif hits >= 3:
                keyword_score = 0.8
            elif hits > 0:
                keyword_score = 0.5

        # Take max of semantic and keyword scores
        final_semantic = max(semantic_score, keyword_score)

        scores = {
            "semantic": final_semantic,
            "permission": self._calculate_permission_score(message),
            "volume": self._calculate_volume_score(agent_id),
            "context": self._calculate_context_score(message, context),
            "drift": self._calculate_drift_score(agent_id, final_semantic),
            "priority": self._calculate_priority_factor(message, context),
            "type": self._calculate_type_factor(message, context),
        }

        weighted = sum(scores[k] * getattr(self.config, f"{k}_weight") for k in scores)

        if scores["priority"] >= 0.9:
            weighted = max(weighted, self.config.critical_priority_boost)
        if scores["semantic"] >= 0.8:
            weighted = max(weighted, self.config.high_semantic_boost)

        return min(1.0, weighted)

    async def batch_calculate_impact(
        self,
        messages: List[AgentMessage],
    ) -> List[float]:
        """
        Async wrapper for batch_score_impact.

        Args:
            messages: List of AgentMessage objects to score.

        Returns:
            List of impact scores.
        """
        return self.batch_score_impact(messages)

    def _get_embeddings(self, text: str) -> np.ndarray:
        """
        Get embeddings for text using available ML backend.

        Implements fallback cascade:
        1. ONNX Runtime (fastest)
        2. PyTorch Transformers
        3. Dummy zeros (heuristics only)
        """
        # Check cache first
        cache_key = hash(text)
        if cache_key in self._embeddings_cache:
            return self._embeddings_cache[cache_key]

        # Ensure model is loaded
        if not self._ensure_model_loaded():
            return np.zeros((1, 768))

        try:
            # Try ONNX inference first
            if self._onnx_enabled and self.onnx_session is not None:
                embeddings = self._onnx_inference(text)
                self._embeddings_cache[cache_key] = embeddings
                return embeddings

            # Fall back to PyTorch Transformers
            if self._bert_enabled and self.model is not None:
                embeddings = self._transformer_inference(text)
                self._embeddings_cache[cache_key] = embeddings
                return embeddings

        except Exception as e:
            logger.warning(f"Embedding generation failed: {e}")

        return np.zeros((1, 768))

    def _onnx_inference(self, text: str) -> np.ndarray:
        """Run inference using ONNX Runtime."""
        if self.tokenizer is None or self.onnx_session is None:
            return np.zeros((1, 768))

        # Tokenize input
        inputs = self.tokenizer(
            text,
            max_length=512,
            truncation=True,
            padding="max_length",
            return_tensors="np"
        )

        # Run ONNX inference
        input_names = [i.name for i in self.onnx_session.get_inputs()]
        onnx_inputs = {name: inputs[name] for name in input_names if name in inputs}

        outputs = self.onnx_session.run(None, onnx_inputs)

        # Extract [CLS] token embedding (first token)
        # Output shape is typically (batch, seq_len, hidden_dim)
        if len(outputs) > 0 and outputs[0].ndim == 3:
            return outputs[0][:, 0, :]  # [CLS] token
        elif len(outputs) > 0:
            return outputs[0]

        return np.zeros((1, 768))

    def _transformer_inference(self, text: str) -> np.ndarray:
        """Run inference using PyTorch Transformers."""
        if self.tokenizer is None or self.model is None:
            return np.zeros((1, 768))

        import torch

        # Tokenize input
        inputs = self.tokenizer(
            text,
            max_length=512,
            truncation=True,
            padding="max_length",
            return_tensors="pt"
        )

        # Run inference without gradient computation
        with torch.no_grad():
            outputs = self.model(**inputs)
            # Get [CLS] token embedding (first token of last hidden state)
            embeddings = outputs.last_hidden_state[:, 0, :].numpy()

        return embeddings

    def _get_keyword_embeddings(self) -> np.ndarray:
        """Get embeddings for high-impact keywords."""
        if self._keyword_embeddings is not None:
            return self._keyword_embeddings

        # Ensure model is loaded
        if not self._ensure_model_loaded():
            self._keyword_embeddings = np.zeros((len(self.high_impact_keywords), 768))
            return self._keyword_embeddings

        # Generate embeddings for all keywords
        try:
            embeddings_list = []
            for keyword in self.high_impact_keywords:
                emb = self._get_embeddings(keyword)
                embeddings_list.append(emb.flatten())

            self._keyword_embeddings = np.array(embeddings_list)
            logger.info(f"Generated embeddings for {len(self.high_impact_keywords)} keywords")

        except Exception as e:
            logger.warning(f"Keyword embedding generation failed: {e}")
            self._keyword_embeddings = np.zeros((len(self.high_impact_keywords), 768))

        return self._keyword_embeddings

    def score_batch(self, texts: List[str], reference_texts: Optional[List[str]] = None) -> List[float]:
        """
        Process multiple texts efficiently with batching.

        Args:
            texts: List of texts to score
            reference_texts: Optional reference texts (uses keywords if None)

        Returns:
            List of impact scores
        """
        self._ensure_model_loaded()

        # Use batch tokenization if Transformers available
        if self._bert_enabled and self.tokenizer is not None and self.model is not None:
            try:
                import torch

                # Batch tokenization
                inputs = self.tokenizer(
                    texts,
                    max_length=512,
                    truncation=True,
                    padding="max_length",
                    return_tensors="pt"
                )

                # Batch inference
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    embeddings = outputs.last_hidden_state[:, 0, :].numpy()

                # Compute similarities against keyword embeddings
                kw_emb = self._get_keyword_embeddings()
                from sklearn.metrics.pairwise import cosine_similarity
                sims = cosine_similarity(embeddings, kw_emb)

                # Return max similarity as score
                return [float(np.max(sim)) for sim in sims]

            except Exception as e:
                logger.warning(f"Batch inference failed: {e}")

        # Fallback to sequential processing
        return [self._calculate_semantic_score({"content": text}) for text in texts]


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
    """Reset global scorer and clear model caches."""
    global _global_scorer
    _global_scorer = None
    # Also reset class-level tokenizer/model cache
    ImpactScorer.reset_class_cache()

    # Clear class-level model caches
    ImpactScorer._model_instance = None
    ImpactScorer._tokenizer_instance = None
    ImpactScorer._onnx_session_instance = None

    logger.info("Impact scorer and model caches reset")

    # Clear class-level model caches
    ImpactScorer._model_instance = None
    ImpactScorer._tokenizer_instance = None
    ImpactScorer._onnx_session_instance = None

    logger.info("Impact scorer and model caches reset")


def reset_profiling():
    """Reset profiling state (placeholder for future profiling features)."""
    pass


def get_ml_backend_status() -> Dict[str, Any]:
    """
    Get current ML backend status for diagnostics.

    Returns:
        Dict with backend availability and configuration info
    """
    return {
        "onnx_available": ONNX_AVAILABLE,
        "transformers_available": TRANSFORMERS_AVAILABLE,
        "use_onnx": USE_ONNX,
        "use_transformers": USE_TRANSFORMERS,
        "model_cached": ImpactScorer._model_instance is not None,
        "onnx_cached": ImpactScorer._onnx_session_instance is not None,
    }


_global_scorer = None


def get_impact_scorer(**kwargs):
    global _global_scorer
    if not _global_scorer:
        _global_scorer = ImpactScorer(**kwargs)
    return _global_scorer


def calculate_message_impact(message: AgentMessage) -> float:
    return get_impact_scorer().calculate_impact_score(message)

async def calculate_message_impact_async(message: AgentMessage) -> float:
    return await get_impact_scorer().calculate_impact_score_async(message)
