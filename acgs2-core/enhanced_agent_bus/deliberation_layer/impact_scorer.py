import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

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
USE_TRANSFORMERS = (
    TRANSFORMERS_AVAILABLE and os.getenv("USE_TRANSFORMERS", "true").lower() == "true"
)
USE_ONNX = ONNX_AVAILABLE and os.getenv("USE_ONNX_INFERENCE", "true").lower() == "true"

# ONNX Runtime availability check
ONNX_AVAILABLE = False
try:
    import onnxruntime as ort

    ONNX_AVAILABLE = True
except ImportError:
    pass

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
    """Streamlined ImpactScorer v3.0.0 (ONNX/BERT optimized).

    Features tokenization caching, class-level model singleton, and lazy ONNX
    session loading with warmup for optimal performance.

    ONNX Session Management:
    - Lazy loading: Session created on first inference, not at initialization
    - Class-level caching: Single ONNX session shared across instances
    - Warmup: Pre-warms execution path to avoid cold-start latency
    - Optimized: Graph optimization and threading configured for performance
    """

    # Class-level tokenizer and model cache (singleton pattern to avoid reloading)
    _tokenizer_instance: Optional[Any] = None
    _model_instance: Optional[Any] = None
    _cached_model_name: Optional[str] = None

    # Class-level ONNX session cache (singleton pattern for efficiency)
    _onnx_session_instance: Optional[Any] = None
    _cached_onnx_path: Optional[str] = None

    # Default ONNX model path (relative to deliberation_layer directory)
    DEFAULT_ONNX_PATH = "optimized_models/distilbert_base_uncased.onnx"

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
        self.use_onnx = use_onnx
        # PERFORMANCE: Disable ONNX for now due to performance regression
        self._onnx_enabled = False  # use_onnx if TRANSFORMERS_AVAILABLE and ONNX_AVAILABLE else False
        self._bert_enabled = False
        self.session = None

        # PERFORMANCE: Skip BERT model loading for now to maintain throughput
        # TODO: Re-enable optimized BERT inference after debugging performance issues
        logger.info("BERT inference disabled for performance - using keyword-based scoring")

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
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, cache_dir=cache_dir)

            # Find ONNX model file
            onnx_path = self._find_onnx_model_path()
            if onnx_path is None:
                logger.info("ONNX model not found - will use PyTorch fallback")
                return False

            # Create ONNX session with GPU if available
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            self.onnx_session = ort.InferenceSession(str(onnx_path), providers=providers)

            # Verify GPU provider was loaded
            active_providers = self.onnx_session.get_providers()
            if "CUDAExecutionProvider" in active_providers:
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
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, cache_dir=cache_dir)
            self.model = AutoModel.from_pretrained(self.model_name, cache_dir=cache_dir)
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

    def _tokenize_text(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Tokenize a single text with caching.

        Uses LRU cache to avoid re-tokenizing identical inputs.
        Optimized with fixed max_length=512 for consistent memory usage.

        Args:
            text: Input text to tokenize.

        Returns:
            Tokenized input dict or None if tokenizer not available.
        """
        if not hasattr(self, "tokenizer") or self.tokenizer is None:
            return None

        # Check cache first
        cache_key = hash(text)
        if self._tokenization_cache is not None:
            cached = self._tokenization_cache.get(cache_key)
            if cached is not None:
                return cached

        # Tokenize with optimized settings
        try:
            tokens = self.tokenizer(
                text,
                padding="max_length",
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )

            # Cache the result
            if self._tokenization_cache is not None:
                self._tokenization_cache.set(cache_key, tokens)

            return tokens
        except Exception as e:
            logger.debug("Tokenization failed for text: %s", e)
            return None

    def _tokenize_batch(
        self, texts: List[str], use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Tokenize multiple texts efficiently with optional caching.

        For batch processing, uses single tokenizer call for better throughput.
        Individual cache lookups used when texts may repeat across batches.

        Args:
            texts: List of texts to tokenize.
            use_cache: Whether to check/populate cache for individual texts.

        Returns:
            Batch tokenized inputs or None if tokenizer not available.
        """
        if not hasattr(self, "tokenizer") or self.tokenizer is None:
            return None

        if not texts:
            return None

        # For small batches with caching enabled, check individual cache entries
        if use_cache and self._tokenization_cache is not None and len(texts) <= 8:
            cached_results = []
            uncached_texts = []
            uncached_indices = []

            for i, text in enumerate(texts):
                cache_key = hash(text)
                cached = self._tokenization_cache.get(cache_key)
                if cached is not None:
                    cached_results.append((i, cached))
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)

            # If all texts were cached, reconstruct batch from cache
            if not uncached_texts and cached_results:
                # Merge cached results into batch format
                try:
                    if TRANSFORMERS_AVAILABLE:
                        input_ids = torch.cat(
                            [cached_results[i][1]["input_ids"] for i in range(len(cached_results))],
                            dim=0,
                        )
                        attention_mask = torch.cat(
                            [
                                cached_results[i][1]["attention_mask"]
                                for i in range(len(cached_results))
                            ],
                            dim=0,
                        )
                        return {"input_ids": input_ids, "attention_mask": attention_mask}
                except Exception:
                    pass  # Fall through to full batch tokenization

        # Batch tokenization (single call for all texts - more efficient)
        try:
            batch_tokens = self.tokenizer(
                texts,
                padding="max_length",
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )

            # Optionally cache individual results for future lookups
            if use_cache and self._tokenization_cache is not None:
                for i, text in enumerate(texts):
                    cache_key = hash(text)
                    try:
                        individual_tokens = {
                            "input_ids": batch_tokens["input_ids"][i : i + 1],
                            "attention_mask": batch_tokens["attention_mask"][i : i + 1],
                        }
                        self._tokenization_cache.set(cache_key, individual_tokens)
                    except Exception:
                        pass  # Cache failure is non-critical

            return batch_tokens
        except Exception as e:
            logger.debug("Batch tokenization failed: %s", e)
            return None

    def clear_tokenization_cache(self) -> None:
        """Clear the tokenization cache to free memory."""
        if self._tokenization_cache is not None:
            self._tokenization_cache.clear()

    @classmethod
    def reset_class_cache(cls) -> None:
        """Reset class-level tokenizer, model, and ONNX session cache.

        Use this when switching models or to free memory.
        """
        cls._tokenizer_instance = None
        cls._model_instance = None
        cls._cached_model_name = None
        cls._onnx_session_instance = None
        cls._cached_onnx_path = None

    def _get_onnx_model_path(self) -> Optional[str]:
        """
        Get the ONNX model path, resolving from environment or default.

        Priority:
        1. Instance-level onnx_model_path (constructor parameter)
        2. Environment variable ONNX_MODEL_PATH
        3. Default path relative to this module

        Returns:
            Absolute path to ONNX model file, or None if not found.
        """
        import os
        from pathlib import Path

        # Priority 1: Instance-level path
        if self._onnx_model_path:
            path = Path(self._onnx_model_path)
            if path.exists():
                return str(path.resolve())

        # Priority 2: Environment variable
        env_path = os.environ.get("ONNX_MODEL_PATH")
        if env_path:
            path = Path(env_path)
            if path.exists():
                return str(path.resolve())

        # Priority 3: Default path relative to this module
        module_dir = Path(__file__).parent
        default_path = module_dir / self.DEFAULT_ONNX_PATH
        if default_path.exists():
            return str(default_path.resolve())

        return None

    def _ensure_onnx_session(self) -> Optional[Any]:
        """
        Lazily load ONNX session on first inference.

        Creates the session only when needed, using class-level caching to share
        the session across instances. Performs warmup on first load.

        Returns:
            ONNX InferenceSession or None if unavailable.
        """
        if not self._onnx_enabled or not ONNX_AVAILABLE:
            return None

        onnx_path = self._get_onnx_model_path()
        if onnx_path is None:
            logger.debug("ONNX model file not found, skipping ONNX inference")
            return None

        # Check class-level cache
        if (
            ImpactScorer._onnx_session_instance is not None
            and ImpactScorer._cached_onnx_path == onnx_path
        ):
            self.session = ImpactScorer._onnx_session_instance
            # Warmup if not done for this instance
            if not self._onnx_session_warmed_up:
                self._warmup_session()
            return self.session

        # Create new session with optimization
        session = self._create_onnx_session(onnx_path)
        if session is not None:
            # Update class-level cache
            ImpactScorer._onnx_session_instance = session
            ImpactScorer._cached_onnx_path = onnx_path
            self.session = session
            # Perform warmup
            self._warmup_session()
            logger.info(f"ONNX session loaded and cached: {onnx_path}")

        return self.session

    def _create_onnx_session(self, onnx_path: str) -> Optional[Any]:
        """
        Create ONNX Runtime session with performance optimizations.

        Configures the session with:
        - Maximum graph optimization level
        - Optimal threading configuration
        - CPU execution provider (GPU can be added later)

        Args:
            onnx_path: Path to the ONNX model file.

        Returns:
            Configured ONNX InferenceSession or None on failure.
        """
        if not ONNX_AVAILABLE:
            return None

        try:
            # Configure session options for optimal performance
            sess_options = ort.SessionOptions()

            # Enable all graph optimizations (constant folding, operator fusion, etc.)
            sess_options.graph_optimization_level = (
                ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            )

            # Configure threading for CPU efficiency
            # intra_op: threads for parallel ops within a single operator
            # inter_op: threads for parallel execution of independent operators
            sess_options.intra_op_num_threads = 4
            sess_options.inter_op_num_threads = 2

            # Execution mode: parallel for better throughput
            sess_options.execution_mode = ort.ExecutionMode.ORT_PARALLEL

            # Create session with CPU provider
            # GPU providers (CUDA, TensorRT) can be added in priority order
            providers = ["CPUExecutionProvider"]

            session = ort.InferenceSession(
                onnx_path,
                sess_options=sess_options,
                providers=providers,
            )

            logger.debug(f"ONNX session created with providers: {providers}")
            return session

        except Exception as e:
            logger.warning(f"Failed to create ONNX session: {e}")
            return None

    def _warmup_session(self) -> None:
        """
        Pre-warm the ONNX session to avoid cold-start latency.

        Runs a dummy inference to:
        - Trigger JIT compilation (if applicable)
        - Allocate memory for inference buffers
        - Prime the execution path

        This significantly reduces latency on the first real inference.
        """
        if self.session is None or self._onnx_session_warmed_up:
            return

        if not hasattr(self, "tokenizer") or self.tokenizer is None:
            self._onnx_session_warmed_up = True
            return

        try:
            # Create dummy input matching expected model input shape
            dummy_text = "warmup inference"
            dummy_inputs = self.tokenizer(
                dummy_text,
                padding="max_length",
                truncation=True,
                max_length=512,
                return_tensors="np",
            )

            # Get input names from session
            input_names = [inp.name for inp in self.session.get_inputs()]

            # Create input feed
            input_feed = {}
            if "input_ids" in input_names:
                input_feed["input_ids"] = dummy_inputs["input_ids"].astype(np.int64)
            if "attention_mask" in input_names:
                input_feed["attention_mask"] = dummy_inputs["attention_mask"].astype(
                    np.int64
                )

            # Run warmup inference
            _ = self.session.run(None, input_feed)

            self._onnx_session_warmed_up = True
            logger.debug("ONNX session warmup completed")

        except Exception as e:
            # Warmup failure is non-critical, log and continue
            logger.debug(f"ONNX session warmup failed (non-critical): {e}")
            self._onnx_session_warmed_up = True

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

                    sim = cosine_similarity(emb, kw_emb)
                    embedding_score = float(np.max(sim))
                else:
                    # Manual cosine similarity fallback
                    sims = [cosine_similarity_fallback(emb, kw) for kw in kw_emb]
                    embedding_score = max(sims) if sims else 0.0
            except Exception as e:
                logger.debug("Embedding-based scoring failed, using keyword score: %s", e)

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
        """Get embeddings using ONNX-optimized BERT model."""
        # PERFORMANCE: Disable ONNX for now - it's causing performance regression
        # TODO: Debug ONNX inference issues and re-enable for GPU acceleration
        logger.debug("Using dummy embeddings for performance (ONNX disabled)")
        return np.zeros((1, 768))

        # Original ONNX implementation (disabled due to performance issues)
        if not self._onnx_enabled or not ONNX_AVAILABLE:
            # Fallback to dummy embeddings if ONNX not available
            return np.zeros((1, 768))

        try:
            # Lazy load ONNX session
            if self.session is None:
                import onnxruntime as ort
                from pathlib import Path

                # Try to find ONNX model in optimized_models directory
                model_dir = Path(__file__).parent / "optimized_models"
                onnx_path = model_dir / "distilbert_base_uncased.onnx"

                if not onnx_path.exists():
                    logger.warning(f"ONNX model not found at {onnx_path}, falling back to dummy embeddings")
                    return np.zeros((1, 768))

                # Create ONNX session with GPU if available
                providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
                self.session = ort.InferenceSession(str(onnx_path), providers=providers)

            # Tokenize input
            inputs = self.tokenizer(text, return_tensors="np", truncation=True, max_length=512, padding="max_length")

            # Run inference
            outputs = self.session.run(None, {
                "input_ids": inputs["input_ids"],
                "attention_mask": inputs["attention_mask"]
            })

            # Extract [CLS] token embedding (first token)
            embeddings = outputs[0][:, 0, :]  # Shape: (batch_size, hidden_size)
            return embeddings

        except Exception as e:
            logger.warning(f"ONNX inference failed: {e}, falling back to dummy embeddings")
            return np.zeros((1, 768))

    def _get_keyword_embeddings(self) -> np.ndarray:
        """Get embeddings for high-impact keywords using ONNX model."""
        if self._keyword_embeddings is not None:
            return self._keyword_embeddings

        if not self._onnx_enabled or not ONNX_AVAILABLE:
            # Fallback to dummy embeddings
            self._keyword_embeddings = np.zeros((len(self.high_impact_keywords), 768))
            return self._keyword_embeddings

        try:
            # Get embeddings for each keyword
            embeddings = []
            for keyword in self.high_impact_keywords:
                emb = self._get_embeddings(keyword)
                embeddings.append(emb[0])  # Remove batch dimension

            self._keyword_embeddings = np.array(embeddings)
            return self._keyword_embeddings

        except Exception as e:
            logger.warning(f"Keyword embedding generation failed: {e}, falling back to dummy embeddings")
            self._keyword_embeddings = np.zeros((len(self.high_impact_keywords), 768))
            return self._keyword_embeddings

    def score_batch(
        self, texts: List[str], reference_texts: Optional[List[str]] = None
    ) -> List[float]:
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
                    return_tensors="pt",
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
    """Reset global scorer and class-level caches."""
    global _global_scorer
    _global_scorer = None
    # Also reset class-level tokenizer/model cache
    ImpactScorer.reset_class_cache()

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
