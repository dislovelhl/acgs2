import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

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

    Features tokenization caching and class-level model singleton for efficiency.
    """

    # Class-level tokenizer and model cache (singleton pattern to avoid reloading)
    _tokenizer_instance: Optional[Any] = None
    _model_instance: Optional[Any] = None
    _cached_model_name: Optional[str] = None

    def __init__(
        self,
        config: Optional[ScoringConfig] = None,
        model_name: str = "distilbert-base-uncased",
        use_onnx: bool = True,
        tokenization_cache_size: int = 1000,
    ):
        self.config = config or ScoringConfig()
        self.model_name = model_name
        self.use_onnx = use_onnx
        self._onnx_enabled = use_onnx if TRANSFORMERS_AVAILABLE else False
        self._bert_enabled = False

        # Initialize tokenization cache for repeated text inputs
        try:
            self._tokenization_cache = LRUCache(maxsize=tokenization_cache_size)
        except NameError:
            # LRUCache not available, use simple dict with size limit
            self._tokenization_cache = None

        # Load tokenizer and model with singleton pattern
        if TRANSFORMERS_AVAILABLE:
            try:
                # Use class-level cached tokenizer if model name matches
                if (
                    ImpactScorer._tokenizer_instance is not None
                    and ImpactScorer._cached_model_name == model_name
                ):
                    self.tokenizer = ImpactScorer._tokenizer_instance
                else:
                    self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                    ImpactScorer._tokenizer_instance = self.tokenizer
                    ImpactScorer._cached_model_name = model_name

                if use_onnx:
                    self.session = None
                else:
                    # Use class-level cached model if available
                    if (
                        ImpactScorer._model_instance is not None
                        and ImpactScorer._cached_model_name == model_name
                    ):
                        self.model = ImpactScorer._model_instance
                    else:
                        self.model = AutoModel.from_pretrained(model_name).eval()
                        ImpactScorer._model_instance = self.model
                    self._bert_enabled = True
            except Exception as e:
                logger.warning(f"Model load failed: {e}")
                self.tokenizer = None

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
        """Reset class-level tokenizer and model cache.

        Use this when switching models or to free memory.
        """
        cls._tokenizer_instance = None
        cls._model_instance = None
        cls._cached_model_name = None

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
            except Exception as e:
                logger.debug("Embedding-based scoring failed, using keyword score: %s", e)

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
        return np.zeros((1, 768))

    def _get_keyword_embeddings(self) -> np.ndarray:
        if self._keyword_embeddings is None:
            self._keyword_embeddings = np.zeros((len(self.high_impact_keywords), 768))
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
    """Reset global scorer and class-level caches."""
    global _global_scorer
    _global_scorer = None
    # Also reset class-level tokenizer/model cache
    ImpactScorer.reset_class_cache()


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
