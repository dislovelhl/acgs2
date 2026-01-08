"""Constitutional Hash: cdd01ef066bc6cf2
Insight Generator - OpenAI SDK integration for AI-powered governance insights

Generates natural language insights from governance data using OpenAI GPT models.
Provides executive-level summaries, business impact analysis, and recommended actions.
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

try:
    from openai import APIConnectionError, APIError, OpenAI, RateLimitError
except ImportError:
    OpenAI = None
    APIError = None
    RateLimitError = None
    APIConnectionError = None

logger = logging.getLogger(__name__)


class GovernanceInsight(BaseModel):
    """Model representing an AI-generated governance insight"""

    summary: str = Field(description="One-sentence executive summary of governance trends")
    business_impact: str = Field(description="Analysis of business implications and risks")
    recommended_action: str = Field(
        description="Actionable recommendation for governance improvement"
    )
    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence score for the insight (0-1)",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when insight was generated",
    )


class QueryResult(BaseModel):
    """Model representing a natural language query result"""

    query: str = Field(description="Original user query")
    answer: str = Field(description="Natural language answer to the query")
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured data relevant to the query",
    )
    query_understood: bool = Field(
        default=True,
        description="Whether the query was successfully parsed",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when response was generated",
    )


class InsightGenerationResult(BaseModel):
    """Result of insight generation analysis"""

    generation_timestamp: datetime
    insight: Optional[GovernanceInsight] = None
    model_used: str
    tokens_used: int = 0
    cached: bool = False
    error_message: Optional[str] = None


class InsightGenerator:
    """
    OpenAI-powered insight generator for governance analytics.

    Generates natural language insights from governance metrics including:
    - Executive summaries of governance trends
    - Business impact analysis
    - Recommended actions for compliance improvement
    - Natural language query responses

    Uses GPT-4o for high-quality insights and GPT-4o-mini for query parsing.
    Implements exponential backoff for rate limit handling.
    """

    # Model selection: gpt-4o for insights (quality), gpt-4o-mini for queries (cost)
    INSIGHT_MODEL = "gpt-4o"
    QUERY_MODEL = "gpt-4o-mini"

    # Retry configuration with exponential backoff
    MAX_RETRIES = 5
    INITIAL_RETRY_DELAY = 1.0  # seconds
    MAX_RETRY_DELAY = 16.0  # seconds

    # Temperature settings
    INSIGHT_TEMPERATURE = 0.3  # Lower temperature for factual analysis
    QUERY_TEMPERATURE = 0.5  # Slightly higher for query interpretation

    def __init__(
        self,
        api_key: Optional[str] = None,
        insight_model: Optional[str] = None,
        query_model: Optional[str] = None,
        max_retries: int = 5,
        cache_enabled: bool = True,
        cache_ttl_seconds: int = 3600,
    ):
        """
        Initialize the insight generator.

        Args:
            api_key: OpenAI API key (default from OPENAI_API_KEY env var)
            insight_model: Model for insight generation (default: gpt-4o)
            query_model: Model for query parsing (default: gpt-4o-mini)
            max_retries: Maximum retry attempts for rate limits
            cache_enabled: Enable caching of generated insights
            cache_ttl_seconds: Cache time-to-live in seconds
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.insight_model = insight_model or self.INSIGHT_MODEL
        self.query_model = query_model or self.QUERY_MODEL
        self.max_retries = max_retries
        self.cache_enabled = cache_enabled
        self.cache_ttl_seconds = cache_ttl_seconds

        self._client: Optional[OpenAI] = None
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._last_generation_time: Optional[datetime] = None

        # Initialize client if OpenAI is available and API key is set
        if OpenAI is not None and self.api_key:
            try:
                self._client = OpenAI(api_key=self.api_key)
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")
                self._client = None
        elif OpenAI is None:
            logger.warning("OpenAI SDK not available. Install with: pip install openai")
        elif not self.api_key:
            logger.warning("OPENAI_API_KEY not set. AI insights will be unavailable.")

    @property
    def is_available(self) -> bool:
        """Check if the OpenAI client is available and configured"""
        return self._client is not None

    def _check_openai_available(self) -> bool:
        """Check if OpenAI SDK is available and client is initialized"""
        if OpenAI is None:
            logger.error("OpenAI SDK is not installed. Install with: pip install openai")
            return False
        if self._client is None:
            logger.error(
                "OpenAI client not initialized. Check OPENAI_API_KEY environment variable."
            )
            return False
        return True

    def _get_cache_key(self, data: Dict[str, Any], operation: str) -> str:
        """
        Generate a cache key for the given data and operation.

        Args:
            data: Input data for the operation
            operation: Type of operation (insight, query)

        Returns:
            Hash string for cache lookup
        """
        content = json.dumps(data, sort_keys=True, default=str) + operation
        return hashlib.sha256(content.encode()).hexdigest()

    def _get_cached(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached result if valid.

        Args:
            cache_key: Cache key to look up

        Returns:
            Cached result or None if not found/expired
        """
        if not self.cache_enabled:
            return None

        cached = self._cache.get(cache_key)
        if cached is None:
            return None

        # Check TTL
        cached_time = cached.get("timestamp")
        if cached_time:
            age = (datetime.now(timezone.utc) - cached_time).total_seconds()
            if age < self.cache_ttl_seconds:
                return cached.get("data")

        # Expired, remove from cache
        del self._cache[cache_key]
        return None

    def _set_cached(self, cache_key: str, data: Dict[str, Any]) -> None:
        """
        Store result in cache.

        Args:
            cache_key: Cache key
            data: Data to cache
        """
        if not self.cache_enabled:
            return

        self._cache[cache_key] = {
            "timestamp": datetime.now(timezone.utc),
            "data": data,
        }

    async def _call_openai_with_retry(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int = 500,
    ) -> Optional[Dict[str, Any]]:
        """
        Call OpenAI API with exponential backoff retry logic.

        Args:
            messages: List of message dicts for chat completion
            model: Model to use
            temperature: Temperature setting
            max_tokens: Maximum tokens in response

        Returns:
            Response dict or None if all retries failed
        """
        if not self._check_openai_available():
            return None

        retry_delay = self.INITIAL_RETRY_DELAY

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                return {
                    "content": response.choices[0].message.content,
                    "model": response.model,
                    "tokens": response.usage.total_tokens if response.usage else 0,
                }

            except RateLimitError as e:
                if attempt < self.max_retries:
                    logger.warning(
                        f"Rate limit hit (attempt {attempt}/{self.max_retries}), "
                        f"retrying in {retry_delay}s..."
                    )
                    import asyncio

                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, self.MAX_RETRY_DELAY)
                else:
                    logger.error(f"Rate limit exceeded after {self.max_retries} retries: {e}")
                    return None

            except APIConnectionError as e:
                if attempt < self.max_retries:
                    logger.warning(
                        f"API connection error (attempt {attempt}/{self.max_retries}), "
                        f"retrying in {retry_delay}s..."
                    )
                    import asyncio

                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, self.MAX_RETRY_DELAY)
                else:
                    logger.error(f"API connection failed after {self.max_retries} retries: {e}")
                    return None

            except APIError as e:
                logger.error(f"OpenAI API error: {e}")
                return None

            except Exception as e:
                logger.error(f"Unexpected error calling OpenAI: {e}")
                return None

        return None

    def _build_insight_prompt(self, governance_data: Dict[str, Any]) -> str:
        """
        Build the prompt for insight generation.

        Args:
            governance_data: Dictionary with governance metrics

        Returns:
            Formatted prompt string
        """
        violations = governance_data.get("violation_count", 0)
        top_policy = governance_data.get("top_violated_policy", "Unknown")
        trend = governance_data.get("trend", "stable")
        total_events = governance_data.get("total_events", 0)
        unique_users = governance_data.get("unique_users", 0)
        severity_dist = governance_data.get("severity_distribution", {})

        prompt = f"""Analyze this governance data and provide executive-level insights:

Policy violations this period: {violations}
Top violating policy: {top_policy}
Trend: {trend}
Total governance events: {total_events}
Unique users involved: {unique_users}
Severity distribution: {json.dumps(severity_dist)}

Provide your analysis in the following JSON format:
{{
    "summary": "One-sentence executive summary of the governance situation",
    "business_impact": "Analysis of business implications, risks, and potential compliance issues",
    "recommended_action": "Specific, actionable recommendation for governance improvement"
}}

Focus on:
1. Clear, concise communication for non-technical executives
2. Business risk implications
3. Actionable next steps

Respond ONLY with the JSON object, no additional text."""

        return prompt

    async def generate_insight(
        self,
        governance_data: Dict[str, Any],
    ) -> InsightGenerationResult:
        """
        Generate AI-powered insights from governance data.

        Args:
            governance_data: Dictionary containing governance metrics:
                - violation_count: Number of violations
                - top_violated_policy: Most violated policy ID/name
                - trend: Trend direction (increasing, decreasing, stable)
                - total_events: Total governance events
                - unique_users: Number of unique users
                - severity_distribution: Dict of severity counts

        Returns:
            InsightGenerationResult with generated insight or error
        """
        now = datetime.now(timezone.utc)

        # Check cache first
        cache_key = self._get_cache_key(governance_data, "insight")
        cached = self._get_cached(cache_key)
        if cached:
            return InsightGenerationResult(
                generation_timestamp=now,
                insight=GovernanceInsight(**cached["insight"]),
                model_used=cached.get("model", self.insight_model),
                tokens_used=cached.get("tokens", 0),
                cached=True,
                error_message=None,
            )

        # Check OpenAI availability
        if not self._check_openai_available():
            return InsightGenerationResult(
                generation_timestamp=now,
                insight=None,
                model_used=self.insight_model,
                tokens_used=0,
                cached=False,
                error_message="AI insights temporarily unavailable. OpenAI client not configured.",
            )

        # Build and send prompt
        prompt = self._build_insight_prompt(governance_data)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a governance analyst expert providing insights for "
                    "compliance officers and executives. Respond only with valid JSON."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        response = await self._call_openai_with_retry(
            messages=messages,
            model=self.insight_model,
            temperature=self.INSIGHT_TEMPERATURE,
            max_tokens=500,
        )

        if response is None:
            return InsightGenerationResult(
                generation_timestamp=now,
                insight=None,
                model_used=self.insight_model,
                tokens_used=0,
                cached=False,
                error_message="AI insights temporarily unavailable.",
            )

        # Parse response
        try:
            content = response["content"].strip()
            # Handle potential markdown code blocks
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])

            insight_data = json.loads(content)

            insight = GovernanceInsight(
                summary=insight_data.get("summary", ""),
                business_impact=insight_data.get("business_impact", ""),
                recommended_action=insight_data.get("recommended_action", ""),
                confidence=0.85,
                generated_at=now,
            )

            # Cache the result
            self._set_cached(
                cache_key,
                {
                    "insight": insight.model_dump(),
                    "model": response["model"],
                    "tokens": response["tokens"],
                },
            )

            self._last_generation_time = now

            logger.info(
                f"Generated insight using {response['model']} ({response['tokens']} tokens)"
            )

            return InsightGenerationResult(
                generation_timestamp=now,
                insight=insight,
                model_used=response["model"],
                tokens_used=response["tokens"],
                cached=False,
                error_message=None,
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {e}")
            return InsightGenerationResult(
                generation_timestamp=now,
                insight=None,
                model_used=self.insight_model,
                tokens_used=response.get("tokens", 0),
                cached=False,
                error_message="Failed to parse AI response",
            )

    async def process_natural_language_query(
        self,
        query: str,
        governance_context: Optional[Dict[str, Any]] = None,
    ) -> QueryResult:
        """
        Process a natural language query about governance data.

        Args:
            query: Natural language question from user
            governance_context: Optional context with current governance data

        Returns:
            QueryResult with answer and relevant data
        """
        now = datetime.now(timezone.utc)

        # Validate query
        if not query or len(query.strip()) < 3:
            return QueryResult(
                query=query,
                answer=(
                    "Could not understand query. Try: 'Show violations this week' "
                    "or 'Which policy is violated most?'"
                ),
                data={},
                query_understood=False,
                generated_at=now,
            )

        # Check OpenAI availability
        if not self._check_openai_available():
            return QueryResult(
                query=query,
                answer="Natural language queries temporarily unavailable.",
                data={},
                query_understood=False,
                generated_at=now,
            )

        # Build query prompt
        context_str = ""
        if governance_context:
            context_str = (
                f"\nCurrent governance context:\n{json.dumps(governance_context, indent=2)}"
            )

        prompt = f"""Parse this governance query and provide a helpful response.

User Query: "{query}"
{context_str}

Analyze the query intent and respond with JSON:
{{
    "understood": true/false,
    "intent": "violations_count|top_policy|trend|user_activity|general",
    "time_range": "today|this_week|this_month|all_time|custom",
    "answer": "Natural language answer to the query",
    "relevant_metrics": ["list", "of", "relevant", "metric", "names"]
}}

If you cannot understand the query, set "understood" to false and suggest example queries.
Respond ONLY with the JSON object."""

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant that interprets natural language "
                    "queries about governance and compliance data. Respond only with valid JSON."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        response = await self._call_openai_with_retry(
            messages=messages,
            model=self.query_model,
            temperature=self.QUERY_TEMPERATURE,
            max_tokens=300,
        )

        if response is None:
            return QueryResult(
                query=query,
                answer="Query processing temporarily unavailable.",
                data={},
                query_understood=False,
                generated_at=now,
            )

        # Parse response
        try:
            content = response["content"].strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])

            parsed = json.loads(content)

            return QueryResult(
                query=query,
                answer=parsed.get("answer", "Unable to generate answer"),
                data={
                    "intent": parsed.get("intent", "general"),
                    "time_range": parsed.get("time_range", "all_time"),
                    "relevant_metrics": parsed.get("relevant_metrics", []),
                },
                query_understood=parsed.get("understood", True),
                generated_at=now,
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse query response: {e}")
            return QueryResult(
                query=query,
                answer=(
                    "Could not understand query. Try: 'Show violations this week' "
                    "or 'Which policy is violated most?'"
                ),
                data={},
                query_understood=False,
                generated_at=now,
            )

    async def generate_report_narrative(
        self,
        governance_data: Dict[str, Any],
        include_recommendations: bool = True,
    ) -> str:
        """
        Generate a narrative summary for PDF reports.

        Args:
            governance_data: Dictionary with governance metrics
            include_recommendations: Whether to include recommendations

        Returns:
            Narrative text for report inclusion
        """
        # Try to generate AI-powered narrative
        if self.is_available:
            recommendations_text = "3. Recommended next steps" if include_recommendations else ""
            prompt = f"""Create a brief executive narrative (2-3 paragraphs) summarizing \
this governance data:

{json.dumps(governance_data, indent=2)}

Focus on:
1. Key findings and trends
2. Areas of concern
{recommendations_text}

Write in a professional, executive-friendly tone suitable for a governance report."""

            messages = [
                {
                    "role": "system",
                    "content": "You are a governance report writer creating executive summaries.",
                },
                {"role": "user", "content": prompt},
            ]

            response = await self._call_openai_with_retry(
                messages=messages,
                model=self.insight_model,
                temperature=self.INSIGHT_TEMPERATURE,
                max_tokens=400,
            )

            if response and response.get("content"):
                return response["content"]

        # Fallback to template-based narrative
        violations = governance_data.get("violation_count", 0)
        total_events = governance_data.get("total_events", 0)
        trend = governance_data.get("trend", "stable")

        narrative = (
            f"During the reporting period, the governance system processed "
            f"{total_events} events, with {violations} policy violations detected. "
            f"The overall trend in violations is {trend}."
        )

        if include_recommendations:
            if violations > 0:
                narrative += (
                    " We recommend reviewing the most frequently violated policies "
                    "and implementing additional training or controls as needed."
                )
            else:
                narrative += (
                    " Continue monitoring governance metrics and maintain current "
                    "compliance practices."
                )

        return narrative

    def clear_cache(self) -> int:
        """
        Clear the insight cache.

        Returns:
            Number of cached items cleared
        """
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cleared {count} cached insights")
        return count

    def get_generator_info(self) -> Dict[str, Any]:
        """
        Get information about the current generator state.

        Returns:
            Dictionary with generator configuration and status
        """
        return {
            "is_available": self.is_available,
            "insight_model": self.insight_model,
            "query_model": self.query_model,
            "max_retries": self.max_retries,
            "cache_enabled": self.cache_enabled,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "cached_items": len(self._cache),
            "last_generation_time": (
                self._last_generation_time.isoformat() if self._last_generation_time else None
            ),
            "openai_sdk_available": OpenAI is not None,
            "api_key_configured": bool(self.api_key),
        }

    def get_insight_as_dict(
        self,
        result: InsightGenerationResult,
    ) -> Dict[str, Any]:
        """
        Convert InsightGenerationResult to a dictionary suitable for API responses.

        Args:
            result: InsightGenerationResult object

        Returns:
            Dictionary representation for JSON serialization
        """
        response = {
            "generation_timestamp": result.generation_timestamp.isoformat(),
            "model_used": result.model_used,
            "tokens_used": result.tokens_used,
            "cached": result.cached,
            "error_message": result.error_message,
        }

        if result.insight:
            response.update(
                {
                    "summary": result.insight.summary,
                    "business_impact": result.insight.business_impact,
                    "recommended_action": result.insight.recommended_action,
                    "confidence": result.insight.confidence,
                }
            )

        return response

    def get_query_result_as_dict(
        self,
        result: QueryResult,
    ) -> Dict[str, Any]:
        """
        Convert QueryResult to a dictionary suitable for API responses.

        Args:
            result: QueryResult object

        Returns:
            Dictionary representation for JSON serialization
        """
        return {
            "query": result.query,
            "answer": result.answer,
            "data": result.data,
            "query_understood": result.query_understood,
            "generated_at": result.generated_at.isoformat(),
        }
