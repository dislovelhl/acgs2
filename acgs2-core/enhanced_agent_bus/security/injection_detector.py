"""
ACGS-2 Prompt Injection Detection Module
Constitutional Hash: cdd01ef066bc6cf2

Dedicated module for detecting and neutralizing prompt injection attacks.
Consolidates detection logic from multiple sources into a unified interface.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class InjectionSeverity(Enum):
    """Severity levels for detected injection attempts."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InjectionType(Enum):
    """Types of prompt injection attacks."""

    INSTRUCTION_OVERRIDE = "instruction_override"
    SYSTEM_PROMPT_LEAK = "system_prompt_leak"
    JAILBREAK = "jailbreak"
    PERSONA_OVERRIDE = "persona_override"
    CONTEXT_POISONING = "context_poisoning"
    ENCODING_BYPASS = "encoding_bypass"
    MULTI_STAGE = "multi_stage"


@dataclass
class InjectionDetectionResult:
    """Result of prompt injection detection scan."""

    is_injection: bool
    severity: Optional[InjectionSeverity] = None
    injection_type: Optional[InjectionType] = None
    matched_patterns: List[str] = None
    confidence: float = 0.0
    sanitized_content: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.matched_patterns is None:
            self.matched_patterns = []
        if self.metadata is None:
            self.metadata = {}


class PromptInjectionDetector:
    """
    Production-grade prompt injection detector for ACGS-2.

    Features:
    - Multi-pattern detection (regex + semantic)
    - Severity classification
    - Content sanitization
    - Confidence scoring
    - Support for various injection techniques
    """

    # Core injection patterns (high confidence)
    CORE_PATTERNS: List[Tuple[str, InjectionType, InjectionSeverity]] = [
        (r"(?i)ignore\s+(all\s+)?previous\s+instructions", InjectionType.INSTRUCTION_OVERRIDE, InjectionSeverity.CRITICAL),
        (r"(?i)system\s+prompt\s+(leak|override|reveal)", InjectionType.SYSTEM_PROMPT_LEAK, InjectionSeverity.CRITICAL),
        (r"(?i)do\s+anything\s+now", InjectionType.JAILBREAK, InjectionSeverity.CRITICAL),  # DAN
        (r"(?i)jailbreak", InjectionType.JAILBREAK, InjectionSeverity.HIGH),
        (r"(?i)persona\s+(adoption|override)", InjectionType.PERSONA_OVERRIDE, InjectionSeverity.HIGH),
        (r"(?i)\(note\s+to\s+self:\s*.*\)", InjectionType.CONTEXT_POISONING, InjectionSeverity.MEDIUM),
        (r"(?i)\[INST\].*\[/INST\]", InjectionType.ENCODING_BYPASS, InjectionSeverity.MEDIUM),  # LLM instruction markers
        (r"(?i)actually,\s+do\s+this\s+instead", InjectionType.INSTRUCTION_OVERRIDE, InjectionSeverity.HIGH),
        (r"(?i)forget\s+everything\s+you\s+know", InjectionType.INSTRUCTION_OVERRIDE, InjectionSeverity.HIGH),
        (r"(?i)bypass\s+(rules|safety|guardrails)", InjectionType.JAILBREAK, InjectionSeverity.HIGH),
        (r"(?i)reveal\s+(your\s+)?system\s+instructions", InjectionType.SYSTEM_PROMPT_LEAK, InjectionSeverity.HIGH),
        (r"(?i)new\s+directive:", InjectionType.INSTRUCTION_OVERRIDE, InjectionSeverity.MEDIUM),
        (r"(?i)override\s+(safety|security|rules)", InjectionType.JAILBREAK, InjectionSeverity.HIGH),
        (r"(?i)pretend\s+you\s+are", InjectionType.PERSONA_OVERRIDE, InjectionSeverity.MEDIUM),
        (r"(?i)roleplay\s+as", InjectionType.PERSONA_OVERRIDE, InjectionSeverity.MEDIUM),
    ]

    # Advanced patterns (medium confidence)
    ADVANCED_PATTERNS: List[Tuple[str, InjectionType, InjectionSeverity]] = [
        (r"(?i)you\s+are\s+now", InjectionType.PERSONA_OVERRIDE, InjectionSeverity.MEDIUM),
        (r"(?i)disregard\s+previous", InjectionType.INSTRUCTION_OVERRIDE, InjectionSeverity.MEDIUM),
        (r"(?i)from\s+now\s+on", InjectionType.INSTRUCTION_OVERRIDE, InjectionSeverity.LOW),
        (r"(?i)your\s+new\s+instructions", InjectionType.INSTRUCTION_OVERRIDE, InjectionSeverity.MEDIUM),
        (r"(?i)hidden\s+instructions", InjectionType.CONTEXT_POISONING, InjectionSeverity.MEDIUM),
        (r"(?i)decode\s+this\s+base64", InjectionType.ENCODING_BYPASS, InjectionSeverity.MEDIUM),
        (r"(?i)rot13\s+decode", InjectionType.ENCODING_BYPASS, InjectionSeverity.LOW),
    ]

    # Multi-stage attack indicators
    MULTI_STAGE_INDICATORS: List[str] = [
        r"(?i)step\s+\d+",
        r"(?i)phase\s+\d+",
        r"(?i)first,\s+.*then",
        r"(?i)after\s+that",
    ]

    def __init__(self, strict_mode: bool = True):
        """
        Initialize the prompt injection detector.

        Args:
            strict_mode: If True, use stricter detection (more false positives but safer)
        """
        self.strict_mode = strict_mode
        self._compiled_core = [
            (re.compile(pattern), inj_type, severity)
            for pattern, inj_type, severity in self.CORE_PATTERNS
        ]
        self._compiled_advanced = [
            (re.compile(pattern), inj_type, severity)
            for pattern, inj_type, severity in self.ADVANCED_PATTERNS
        ]
        self._compiled_multi_stage = [
            re.compile(pattern) for pattern in self.MULTI_STAGE_INDICATORS
        ]

    def detect(self, content: Any, context: Optional[Dict[str, Any]] = None) -> InjectionDetectionResult:
        """
        Detect prompt injection attempts in content.

        Args:
            content: Content to scan (str, dict, list, etc.)
            context: Optional context metadata (agent_id, tenant_id, etc.)

        Returns:
            InjectionDetectionResult with detection details
        """
        # Normalize content to string
        content_str = self._normalize_content(content)

        if not content_str or len(content_str.strip()) == 0:
            return InjectionDetectionResult(
                is_injection=False,
                confidence=0.0,
                metadata={"reason": "empty_content"}
            )

        matched_patterns = []
        detected_types = set()
        max_severity = None
        confidence_score = 0.0

        # Scan core patterns (high confidence)
        for pattern, inj_type, severity in self._compiled_core:
            if pattern.search(content_str):
                matched_patterns.append(pattern.pattern)
                detected_types.add(inj_type)
                if max_severity is None or self._severity_value(severity) > self._severity_value(max_severity):
                    max_severity = severity
                confidence_score += 0.3  # High confidence per match

        # Scan advanced patterns (medium confidence)
        if self.strict_mode or len(matched_patterns) > 0:
            for pattern, inj_type, severity in self._compiled_advanced:
                if pattern.search(content_str):
                    matched_patterns.append(pattern.pattern)
                    detected_types.add(inj_type)
                    if max_severity is None or self._severity_value(severity) > self._severity_value(max_severity):
                        max_severity = severity
                    confidence_score += 0.15  # Medium confidence per match

        # Check for multi-stage attacks
        multi_stage_count = sum(1 for pattern in self._compiled_multi_stage if pattern.search(content_str))
        if multi_stage_count >= 2:
            detected_types.add(InjectionType.MULTI_STAGE)
            confidence_score += 0.2
            if max_severity is None or self._severity_value(InjectionSeverity.MEDIUM) > self._severity_value(max_severity):
                max_severity = InjectionSeverity.MEDIUM

        # Determine primary injection type
        primary_type = None
        if detected_types:
            # Prioritize critical types
            if InjectionType.INSTRUCTION_OVERRIDE in detected_types:
                primary_type = InjectionType.INSTRUCTION_OVERRIDE
            elif InjectionType.JAILBREAK in detected_types:
                primary_type = InjectionType.JAILBREAK
            elif InjectionType.SYSTEM_PROMPT_LEAK in detected_types:
                primary_type = InjectionType.SYSTEM_PROMPT_LEAK
            else:
                primary_type = next(iter(detected_types))

        # Cap confidence at 1.0
        confidence_score = min(1.0, confidence_score)

        # Determine if injection detected
        is_injection = (
            len(matched_patterns) > 0 and
            (confidence_score >= 0.3 if self.strict_mode else confidence_score >= 0.5)
        )

        # Generate sanitized content if injection detected
        sanitized_content = None
        if is_injection:
            sanitized_content = self._sanitize_content(content_str, matched_patterns)

        result = InjectionDetectionResult(
            is_injection=is_injection,
            severity=max_severity,
            injection_type=primary_type,
            matched_patterns=matched_patterns,
            confidence=confidence_score,
            sanitized_content=sanitized_content,
            metadata={
                "detected_types": [t.value for t in detected_types],
                "pattern_count": len(matched_patterns),
                "multi_stage_indicators": multi_stage_count,
                "content_length": len(content_str),
                "strict_mode": self.strict_mode,
                **(context or {}),
            }
        )

        if is_injection:
            logger.warning(
                f"Prompt injection detected: type={primary_type.value if primary_type else 'unknown'}, "
                f"severity={max_severity.value if max_severity else 'unknown'}, "
                f"confidence={confidence_score:.2f}, patterns={len(matched_patterns)}"
            )

        return result

    def _normalize_content(self, content: Any) -> str:
        """Normalize content to string for scanning."""
        if isinstance(content, str):
            return content
        elif isinstance(content, dict):
            # Extract text fields from dict
            text_parts = []
            for key, value in content.items():
                if isinstance(value, str):
                    text_parts.append(value)
                elif isinstance(value, (dict, list)):
                    text_parts.append(self._normalize_content(value))
            return " ".join(text_parts)
        elif isinstance(content, list):
            return " ".join(self._normalize_content(item) for item in content)
        else:
            return str(content)

    def _sanitize_content(self, content: str, matched_patterns: List[str]) -> str:
        """
        Sanitize content by removing or neutralizing detected patterns.

        Note: This is a basic sanitization. In production, you may want
        more sophisticated approaches like content rewriting or blocking.
        """
        sanitized = content
        for pattern_str in matched_patterns:
            try:
                pattern = re.compile(pattern_str, re.IGNORECASE)
                sanitized = pattern.sub("[REDACTED]", sanitized)
            except Exception as e:
                logger.warning(f"Failed to sanitize pattern {pattern_str}: {e}")
        return sanitized

    @staticmethod
    def _severity_value(severity: InjectionSeverity) -> int:
        """Get numeric value for severity comparison."""
        return {
            InjectionSeverity.LOW: 1,
            InjectionSeverity.MEDIUM: 2,
            InjectionSeverity.HIGH: 3,
            InjectionSeverity.CRITICAL: 4,
        }.get(severity, 0)


# Convenience function for backward compatibility
def detect_prompt_injection(content: Any, strict_mode: bool = True) -> bool:
    """
    Simple function interface for prompt injection detection.

    Args:
        content: Content to scan
        strict_mode: Use strict detection mode

    Returns:
        True if injection detected, False otherwise
    """
    detector = PromptInjectionDetector(strict_mode=strict_mode)
    result = detector.detect(content)
    return result.is_injection
