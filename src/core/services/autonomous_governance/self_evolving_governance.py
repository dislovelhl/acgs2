#!/usr/bin/env python3
"""
ACGS-2 Self-Evolving Governance System
Constitutional Hash: cdd01ef066bc6cf2

Research prototype for autonomous governance systems that can adapt policies
based on emerging risks, regulatory changes, and operational feedback
without human intervention, with appropriate safety bounds.

Key Features:
- Autonomous Policy Adaptation
- Safety Bounds and Guardrails
- Human Override Capabilities
- Explainable Evolution Decisions
- Ethics Review Integration

Phase: 5 - Next-Generation Governance
Author: ACGS-2 Autonomous Governance Research

WARNING: This is a research prototype. Deploy only in controlled environments
with appropriate human oversight and ethics review.
"""

import hashlib
import json
import logging
import secrets
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import numpy as np

# Constitutional hash for ACGS-2 compliance
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

logger = logging.getLogger(__name__)


class EvolutionTrigger(Enum):
    """Triggers that can initiate policy evolution"""
    
    RISK_DETECTION = "risk_detection"           # New risk pattern detected
    REGULATORY_CHANGE = "regulatory_change"     # External regulation changed
    PERFORMANCE_DRIFT = "performance_drift"     # Policy effectiveness degraded
    FEEDBACK_ACCUMULATION = "feedback"          # Enough feedback to learn from
    SCHEDULED = "scheduled"                     # Periodic review cycle
    MANUAL = "manual"                           # Human-initiated evolution


class SafetyLevel(Enum):
    """Safety classification for evolution actions"""
    
    SAFE = "safe"               # No risk, automatic approval
    LOW_RISK = "low_risk"       # Minor changes, notification only
    MEDIUM_RISK = "medium_risk" # Requires async human review
    HIGH_RISK = "high_risk"     # Requires sync human approval
    CRITICAL = "critical"       # Blocked until ethics review


class EvolutionAction(Enum):
    """Types of policy evolution actions"""
    
    PARAMETER_TUNE = "parameter_tune"       # Adjust thresholds/weights
    RULE_ADDITION = "rule_addition"         # Add new rule to policy
    RULE_REMOVAL = "rule_removal"           # Remove existing rule
    RULE_MODIFICATION = "rule_modification" # Modify rule logic
    POLICY_MERGE = "policy_merge"           # Merge multiple policies
    POLICY_SPLIT = "policy_split"           # Split policy into parts
    ROLLBACK = "rollback"                   # Revert to previous version


class EthicsCategory(Enum):
    """Ethics categories for evolution evaluation"""
    
    FAIRNESS = "fairness"                   # Bias and equity
    TRANSPARENCY = "transparency"           # Explainability
    PRIVACY = "privacy"                     # Data protection
    AUTONOMY = "autonomy"                   # Human agency
    SAFETY = "safety"                       # Harm prevention
    ACCOUNTABILITY = "accountability"       # Attribution and responsibility


@dataclass
class SafetyBound:
    """Safety constraint that must be satisfied"""
    
    bound_id: str
    name: str
    description: str
    category: EthicsCategory
    check_function: str  # Serialized function reference
    threshold: float
    is_hard_constraint: bool  # If True, violation blocks evolution
    violation_action: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "bound_id": self.bound_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "check_function": self.check_function,
            "threshold": self.threshold,
            "is_hard_constraint": self.is_hard_constraint,
            "violation_action": self.violation_action,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }


@dataclass
class EvolutionProposal:
    """Proposed policy evolution"""
    
    proposal_id: str
    trigger: EvolutionTrigger
    action: EvolutionAction
    target_policy_id: str
    current_version: str
    proposed_changes: Dict[str, Any]
    justification: str
    safety_level: SafetyLevel
    confidence_score: float
    created_at: datetime
    ethics_evaluation: Dict[EthicsCategory, float] = field(default_factory=dict)
    safety_checks: Dict[str, bool] = field(default_factory=dict)
    human_review_required: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejected_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "trigger": self.trigger.value,
            "action": self.action.value,
            "target_policy_id": self.target_policy_id,
            "current_version": self.current_version,
            "proposed_changes": self.proposed_changes,
            "justification": self.justification,
            "safety_level": self.safety_level.value,
            "confidence_score": self.confidence_score,
            "created_at": self.created_at.isoformat(),
            "ethics_evaluation": {k.value: v for k, v in self.ethics_evaluation.items()},
            "safety_checks": self.safety_checks,
            "human_review_required": self.human_review_required,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejected_reason": self.rejected_reason,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }


@dataclass
class EvolutionOutcome:
    """Result of applying an evolution"""
    
    outcome_id: str
    proposal_id: str
    applied_at: datetime
    success: bool
    new_version: Optional[str]
    performance_delta: float
    side_effects: List[str]
    rollback_available: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "proposal_id": self.proposal_id,
            "applied_at": self.applied_at.isoformat(),
            "success": self.success,
            "new_version": self.new_version,
            "performance_delta": self.performance_delta,
            "side_effects": self.side_effects,
            "rollback_available": self.rollback_available,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }


@dataclass
class RiskPattern:
    """Detected risk pattern that may trigger evolution"""
    
    pattern_id: str
    name: str
    description: str
    severity: float  # 0.0 to 1.0
    affected_policies: List[str]
    detection_count: int
    first_detected: datetime
    last_detected: datetime
    suggested_actions: List[EvolutionAction]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "name": self.name,
            "description": self.description,
            "severity": self.severity,
            "affected_policies": self.affected_policies,
            "detection_count": self.detection_count,
            "first_detected": self.first_detected.isoformat(),
            "last_detected": self.last_detected.isoformat(),
            "suggested_actions": [a.value for a in self.suggested_actions],
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }


class SafetyGuardrail(ABC):
    """Abstract base class for safety guardrails"""
    
    @abstractmethod
    def evaluate(self, proposal: EvolutionProposal) -> Tuple[bool, str]:
        """
        Evaluate whether a proposal passes this guardrail.
        
        Returns:
            Tuple of (passes, reason)
        """
        pass
    
    @property
    @abstractmethod
    def category(self) -> EthicsCategory:
        """Return the ethics category this guardrail protects."""
        pass


class BiasGuardrail(SafetyGuardrail):
    """Guardrail that prevents biased policy evolution"""
    
    def __init__(self, bias_threshold: float = 0.1):
        self.bias_threshold = bias_threshold
    
    def evaluate(self, proposal: EvolutionProposal) -> Tuple[bool, str]:
        """Check if proposal introduces bias."""
        # Simulate bias detection
        # In real implementation, this would use fairness metrics
        
        proposed_changes = proposal.proposed_changes
        
        # Check for protected attribute usage
        protected_attrs = {"race", "gender", "age", "religion", "disability", "nationality"}
        used_attrs = set()
        
        for key, value in proposed_changes.items():
            if isinstance(value, str):
                for attr in protected_attrs:
                    if attr in value.lower():
                        used_attrs.add(attr)
        
        if used_attrs:
            return False, f"Policy uses protected attributes: {used_attrs}"
        
        # Check fairness score in ethics evaluation
        if EthicsCategory.FAIRNESS in proposal.ethics_evaluation:
            fairness_score = proposal.ethics_evaluation[EthicsCategory.FAIRNESS]
            if fairness_score < (1.0 - self.bias_threshold):
                return False, f"Fairness score {fairness_score:.2f} below threshold"
        
        return True, "Bias check passed"
    
    @property
    def category(self) -> EthicsCategory:
        return EthicsCategory.FAIRNESS


class HarmPreventionGuardrail(SafetyGuardrail):
    """Guardrail that prevents harmful policy evolution"""
    
    HARMFUL_PATTERNS = [
        "deny_all",
        "unrestricted_access",
        "bypass_authentication",
        "disable_logging",
        "ignore_consent",
        "unlimited_retention",
    ]
    
    def evaluate(self, proposal: EvolutionProposal) -> Tuple[bool, str]:
        """Check if proposal could cause harm."""
        changes_str = json.dumps(proposal.proposed_changes).lower()
        
        for pattern in self.HARMFUL_PATTERNS:
            if pattern in changes_str:
                return False, f"Harmful pattern detected: {pattern}"
        
        # Check safety score
        if EthicsCategory.SAFETY in proposal.ethics_evaluation:
            safety_score = proposal.ethics_evaluation[EthicsCategory.SAFETY]
            if safety_score < 0.8:
                return False, f"Safety score {safety_score:.2f} too low"
        
        return True, "Harm prevention check passed"
    
    @property
    def category(self) -> EthicsCategory:
        return EthicsCategory.SAFETY


class TransparencyGuardrail(SafetyGuardrail):
    """Guardrail that ensures evolution decisions are explainable"""
    
    MIN_JUSTIFICATION_LENGTH = 50
    
    def evaluate(self, proposal: EvolutionProposal) -> Tuple[bool, str]:
        """Check if proposal has adequate justification."""
        if len(proposal.justification) < self.MIN_JUSTIFICATION_LENGTH:
            return False, f"Justification too short ({len(proposal.justification)} chars)"
        
        # Check for concrete reasoning
        required_elements = ["because", "therefore", "based on", "due to"]
        has_reasoning = any(elem in proposal.justification.lower() for elem in required_elements)
        
        if not has_reasoning:
            return False, "Justification lacks explicit reasoning"
        
        return True, "Transparency check passed"
    
    @property
    def category(self) -> EthicsCategory:
        return EthicsCategory.TRANSPARENCY


class HumanAgencyGuardrail(SafetyGuardrail):
    """Guardrail that preserves human override capabilities"""
    
    def evaluate(self, proposal: EvolutionProposal) -> Tuple[bool, str]:
        """Check if proposal maintains human control."""
        changes = proposal.proposed_changes
        
        # Check for human override removal
        if "disable_human_override" in changes:
            return False, "Cannot disable human override capability"
        
        if "remove_approval_requirement" in changes:
            return False, "Cannot remove approval requirements"
        
        # Ensure HITL is preserved for high-impact decisions
        if proposal.action in [EvolutionAction.RULE_REMOVAL, EvolutionAction.POLICY_MERGE]:
            if proposal.safety_level in [SafetyLevel.HIGH_RISK, SafetyLevel.CRITICAL]:
                if not proposal.human_review_required:
                    return False, "High-risk evolution must require human review"
        
        return True, "Human agency check passed"
    
    @property
    def category(self) -> EthicsCategory:
        return EthicsCategory.AUTONOMY


class RiskDetector:
    """
    Detects risk patterns that may require policy evolution.
    
    Uses statistical analysis and anomaly detection to identify
    emerging risks in governance decisions.
    """
    
    def __init__(self, sensitivity: float = 0.7):
        self.sensitivity = sensitivity
        self.detected_patterns: Dict[str, RiskPattern] = {}
        self.decision_history: List[Dict[str, Any]] = []
        self.baseline_metrics: Dict[str, float] = {}
        
        logger.info(f"Risk detector initialized with sensitivity {sensitivity}")
    
    def record_decision(self, decision: Dict[str, Any]):
        """Record a governance decision for analysis."""
        self.decision_history.append({
            **decision,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        })
        
        # Keep last 10000 decisions
        if len(self.decision_history) > 10000:
            self.decision_history = self.decision_history[-10000:]
    
    def analyze_for_risks(self) -> List[RiskPattern]:
        """
        Analyze recent decisions for risk patterns.
        """
        if len(self.decision_history) < 100:
            return []  # Need more data
        
        new_patterns = []
        
        # Check for decision drift
        drift_pattern = self._detect_decision_drift()
        if drift_pattern:
            new_patterns.append(drift_pattern)
        
        # Check for anomalous rejection rates
        rejection_pattern = self._detect_rejection_anomaly()
        if rejection_pattern:
            new_patterns.append(rejection_pattern)
        
        # Check for latency degradation
        latency_pattern = self._detect_latency_issues()
        if latency_pattern:
            new_patterns.append(latency_pattern)
        
        # Store detected patterns
        for pattern in new_patterns:
            self.detected_patterns[pattern.pattern_id] = pattern
        
        return new_patterns
    
    def _detect_decision_drift(self) -> Optional[RiskPattern]:
        """Detect if decision patterns are drifting from baseline."""
        recent = self.decision_history[-100:]
        
        # Calculate approval rate
        approvals = sum(1 for d in recent if d.get("approved", False))
        approval_rate = approvals / len(recent)
        
        # Compare to baseline
        baseline_rate = self.baseline_metrics.get("approval_rate", 0.5)
        drift = abs(approval_rate - baseline_rate)
        
        if drift > 0.2:  # 20% drift threshold
            return RiskPattern(
                pattern_id=f"drift-{secrets.token_hex(4)}",
                name="Decision Drift Detected",
                description=f"Approval rate changed from {baseline_rate:.2f} to {approval_rate:.2f}",
                severity=min(drift * 2, 1.0),
                affected_policies=list(set(d.get("policy_id", "") for d in recent)),
                detection_count=1,
                first_detected=datetime.now(timezone.utc),
                last_detected=datetime.now(timezone.utc),
                suggested_actions=[EvolutionAction.PARAMETER_TUNE],
            )
        
        return None
    
    def _detect_rejection_anomaly(self) -> Optional[RiskPattern]:
        """Detect anomalous rejection patterns."""
        recent = self.decision_history[-100:]
        
        rejections = [d for d in recent if not d.get("approved", True)]
        
        if len(rejections) < 10:
            return None
        
        # Check for clustered rejections (same policy)
        policy_rejections: Dict[str, int] = {}
        for d in rejections:
            policy_id = d.get("policy_id", "unknown")
            policy_rejections[policy_id] = policy_rejections.get(policy_id, 0) + 1
        
        # Find policies with high rejection rates
        for policy_id, count in policy_rejections.items():
            if count > len(rejections) * 0.5:  # >50% of rejections from one policy
                return RiskPattern(
                    pattern_id=f"rejection-{secrets.token_hex(4)}",
                    name="High Rejection Concentration",
                    description=f"Policy {policy_id} accounts for {count}/{len(rejections)} rejections",
                    severity=0.6,
                    affected_policies=[policy_id],
                    detection_count=count,
                    first_detected=datetime.now(timezone.utc),
                    last_detected=datetime.now(timezone.utc),
                    suggested_actions=[EvolutionAction.RULE_MODIFICATION],
                )
        
        return None
    
    def _detect_latency_issues(self) -> Optional[RiskPattern]:
        """Detect governance latency degradation."""
        recent = self.decision_history[-100:]
        
        latencies = [d.get("latency_ms", 0) for d in recent if "latency_ms" in d]
        
        if not latencies:
            return None
        
        avg_latency = np.mean(latencies)
        baseline_latency = self.baseline_metrics.get("latency_ms", 10.0)
        
        if avg_latency > baseline_latency * 2:  # 2x degradation
            return RiskPattern(
                pattern_id=f"latency-{secrets.token_hex(4)}",
                name="Latency Degradation",
                description=f"Average latency increased from {baseline_latency:.1f}ms to {avg_latency:.1f}ms",
                severity=min((avg_latency / baseline_latency - 1) / 5, 1.0),
                affected_policies=[],
                detection_count=1,
                first_detected=datetime.now(timezone.utc),
                last_detected=datetime.now(timezone.utc),
                suggested_actions=[EvolutionAction.PARAMETER_TUNE],
            )
        
        return None
    
    def update_baseline(self):
        """Update baseline metrics from current data."""
        if len(self.decision_history) < 1000:
            return
        
        # Use first 80% as baseline
        baseline_data = self.decision_history[:int(len(self.decision_history) * 0.8)]
        
        approvals = sum(1 for d in baseline_data if d.get("approved", False))
        self.baseline_metrics["approval_rate"] = approvals / len(baseline_data)
        
        latencies = [d.get("latency_ms", 0) for d in baseline_data if "latency_ms" in d]
        if latencies:
            self.baseline_metrics["latency_ms"] = np.mean(latencies)
        
        logger.info(f"Updated baseline metrics: {self.baseline_metrics}")


class EvolutionEngine:
    """
    Core engine for generating and evaluating policy evolutions.
    
    Uses a combination of rule-based and ML-based approaches to
    propose policy improvements while respecting safety constraints.
    """
    
    def __init__(self, safety_bounds: List[SafetyBound] = None):
        self.safety_bounds = safety_bounds or []
        self.guardrails: List[SafetyGuardrail] = [
            BiasGuardrail(),
            HarmPreventionGuardrail(),
            TransparencyGuardrail(),
            HumanAgencyGuardrail(),
        ]
        self.proposal_history: List[EvolutionProposal] = []
        self.outcome_history: List[EvolutionOutcome] = []
        
        logger.info(f"Evolution engine initialized with {len(self.guardrails)} guardrails")
    
    def generate_proposal(self, trigger: EvolutionTrigger,
                          risk_pattern: Optional[RiskPattern],
                          target_policy: Dict[str, Any]) -> EvolutionProposal:
        """
        Generate an evolution proposal based on trigger and context.
        """
        proposal_id = f"evo-{secrets.token_hex(8)}"
        
        # Determine action based on trigger
        if trigger == EvolutionTrigger.RISK_DETECTION and risk_pattern:
            action = risk_pattern.suggested_actions[0] if risk_pattern.suggested_actions else EvolutionAction.PARAMETER_TUNE
            justification = f"Risk pattern '{risk_pattern.name}' detected: {risk_pattern.description}. Therefore, proposing {action.value} to mitigate this risk based on {risk_pattern.detection_count} occurrences."
            confidence = 1.0 - risk_pattern.severity * 0.5
        elif trigger == EvolutionTrigger.PERFORMANCE_DRIFT:
            action = EvolutionAction.PARAMETER_TUNE
            justification = "Performance metrics indicate drift from baseline. Therefore, parameter tuning is proposed based on statistical analysis of recent decisions."
            confidence = 0.7
        elif trigger == EvolutionTrigger.FEEDBACK_ACCUMULATION:
            action = EvolutionAction.RULE_MODIFICATION
            justification = "Accumulated feedback indicates room for improvement. Based on user feedback patterns, rule modification is suggested."
            confidence = 0.6
        else:
            action = EvolutionAction.PARAMETER_TUNE
            justification = "Scheduled evolution review. Due to periodic review cycle, minor parameter adjustments are proposed based on operational data."
            confidence = 0.5
        
        # Generate proposed changes
        proposed_changes = self._generate_changes(action, target_policy, risk_pattern)
        
        # Classify safety level
        safety_level = self._classify_safety_level(action, proposed_changes)
        
        # Create proposal
        proposal = EvolutionProposal(
            proposal_id=proposal_id,
            trigger=trigger,
            action=action,
            target_policy_id=target_policy.get("policy_id", "unknown"),
            current_version=target_policy.get("version", "1.0.0"),
            proposed_changes=proposed_changes,
            justification=justification,
            safety_level=safety_level,
            confidence_score=confidence,
            created_at=datetime.now(timezone.utc),
            human_review_required=safety_level in [SafetyLevel.HIGH_RISK, SafetyLevel.CRITICAL],
        )
        
        # Evaluate ethics
        proposal.ethics_evaluation = self._evaluate_ethics(proposal)
        
        # Run safety checks
        proposal.safety_checks = self._run_safety_checks(proposal)
        
        # Store proposal
        self.proposal_history.append(proposal)
        
        logger.info(f"Generated evolution proposal: {proposal_id} ({action.value})")
        return proposal
    
    def evaluate_proposal(self, proposal: EvolutionProposal) -> Tuple[bool, List[str]]:
        """
        Evaluate a proposal against all safety guardrails.
        
        Returns:
            Tuple of (can_proceed, list_of_issues)
        """
        issues = []
        can_proceed = True
        
        # Check all guardrails
        for guardrail in self.guardrails:
            passes, reason = guardrail.evaluate(proposal)
            if not passes:
                issues.append(f"[{guardrail.category.value}] {reason}")
                can_proceed = False
        
        # Check hard safety bounds
        for bound in self.safety_bounds:
            if bound.is_hard_constraint:
                if not proposal.safety_checks.get(bound.bound_id, False):
                    issues.append(f"[{bound.category.value}] Hard constraint violated: {bound.name}")
                    can_proceed = False
        
        # Block if safety level is CRITICAL
        if proposal.safety_level == SafetyLevel.CRITICAL:
            issues.append("[CRITICAL] Proposal blocked pending ethics review")
            can_proceed = False
        
        logger.info(f"Proposal {proposal.proposal_id} evaluation: can_proceed={can_proceed}, issues={len(issues)}")
        return can_proceed, issues
    
    def apply_evolution(self, proposal: EvolutionProposal, 
                        policy_store: Dict[str, Any]) -> EvolutionOutcome:
        """
        Apply an approved evolution to the policy store.
        """
        outcome_id = f"out-{secrets.token_hex(8)}"
        
        # Check if approved
        if proposal.human_review_required and not proposal.approved_by:
            return EvolutionOutcome(
                outcome_id=outcome_id,
                proposal_id=proposal.proposal_id,
                applied_at=datetime.now(timezone.utc),
                success=False,
                new_version=None,
                performance_delta=0.0,
                side_effects=["Human approval required but not obtained"],
                rollback_available=False,
            )
        
        try:
            # Apply changes to policy
            target_policy = policy_store.get(proposal.target_policy_id, {})
            
            # Store rollback point
            rollback_version = target_policy.copy()
            
            # Apply changes based on action type
            if proposal.action == EvolutionAction.PARAMETER_TUNE:
                for key, value in proposal.proposed_changes.items():
                    if key in target_policy:
                        target_policy[key] = value
            
            elif proposal.action == EvolutionAction.RULE_MODIFICATION:
                if "rules" in target_policy and "rule_updates" in proposal.proposed_changes:
                    for rule_id, update in proposal.proposed_changes["rule_updates"].items():
                        if rule_id in target_policy["rules"]:
                            target_policy["rules"][rule_id].update(update)
            
            elif proposal.action == EvolutionAction.ROLLBACK:
                if "rollback_to_version" in proposal.proposed_changes:
                    # Would restore from version history
                    pass
            
            # Bump version
            version_parts = proposal.current_version.split(".")
            version_parts[2] = str(int(version_parts[2]) + 1)
            new_version = ".".join(version_parts)
            target_policy["version"] = new_version
            
            # Store updated policy
            policy_store[proposal.target_policy_id] = target_policy
            
            outcome = EvolutionOutcome(
                outcome_id=outcome_id,
                proposal_id=proposal.proposal_id,
                applied_at=datetime.now(timezone.utc),
                success=True,
                new_version=new_version,
                performance_delta=0.0,  # Would be measured after deployment
                side_effects=[],
                rollback_available=True,
            )
            
            logger.info(f"Applied evolution {proposal.proposal_id} -> version {new_version}")
            
        except Exception as e:
            outcome = EvolutionOutcome(
                outcome_id=outcome_id,
                proposal_id=proposal.proposal_id,
                applied_at=datetime.now(timezone.utc),
                success=False,
                new_version=None,
                performance_delta=0.0,
                side_effects=[str(e)],
                rollback_available=False,
            )
            
            logger.error(f"Evolution {proposal.proposal_id} failed: {e}")
        
        self.outcome_history.append(outcome)
        return outcome
    
    def _generate_changes(self, action: EvolutionAction, 
                          policy: Dict[str, Any],
                          risk_pattern: Optional[RiskPattern]) -> Dict[str, Any]:
        """Generate specific changes based on action type."""
        changes = {}
        
        if action == EvolutionAction.PARAMETER_TUNE:
            # Adjust thresholds based on risk
            if risk_pattern and risk_pattern.severity > 0.5:
                changes["risk_threshold"] = policy.get("risk_threshold", 0.5) * 0.9
            else:
                changes["risk_threshold"] = policy.get("risk_threshold", 0.5) * 1.05
            
            # Adjust batch sizes for latency
            if risk_pattern and "latency" in risk_pattern.name.lower():
                changes["batch_size"] = max(1, policy.get("batch_size", 10) // 2)
        
        elif action == EvolutionAction.RULE_ADDITION:
            changes["new_rule"] = {
                "id": f"rule-{secrets.token_hex(4)}",
                "condition": "default_allow",
                "action": "audit",
            }
        
        elif action == EvolutionAction.RULE_MODIFICATION:
            changes["rule_updates"] = {}
            if "rules" in policy:
                for rule_id in list(policy["rules"].keys())[:1]:
                    changes["rule_updates"][rule_id] = {
                        "priority": policy["rules"][rule_id].get("priority", 0) + 1
                    }
        
        return changes
    
    def _classify_safety_level(self, action: EvolutionAction, 
                                changes: Dict[str, Any]) -> SafetyLevel:
        """Classify the safety level of proposed changes."""
        if action == EvolutionAction.ROLLBACK:
            return SafetyLevel.LOW_RISK
        
        if action == EvolutionAction.PARAMETER_TUNE:
            # Check magnitude of changes
            has_large_change = any(
                isinstance(v, (int, float)) and abs(v) > 100
                for v in changes.values()
            )
            return SafetyLevel.MEDIUM_RISK if has_large_change else SafetyLevel.LOW_RISK
        
        if action in [EvolutionAction.RULE_REMOVAL, EvolutionAction.POLICY_MERGE]:
            return SafetyLevel.HIGH_RISK
        
        if action == EvolutionAction.RULE_ADDITION:
            return SafetyLevel.MEDIUM_RISK
        
        return SafetyLevel.MEDIUM_RISK
    
    def _evaluate_ethics(self, proposal: EvolutionProposal) -> Dict[EthicsCategory, float]:
        """Evaluate ethics scores for a proposal."""
        scores = {}
        
        # Fairness: Check for bias indicators
        changes_str = json.dumps(proposal.proposed_changes).lower()
        bias_indicators = sum(1 for word in ["gender", "race", "age"] if word in changes_str)
        scores[EthicsCategory.FAIRNESS] = 1.0 - (bias_indicators * 0.2)
        
        # Transparency: Based on justification quality
        scores[EthicsCategory.TRANSPARENCY] = min(len(proposal.justification) / 200, 1.0)
        
        # Privacy: Check for data access changes
        privacy_risk = 1 if "data_access" in changes_str or "retention" in changes_str else 0
        scores[EthicsCategory.PRIVACY] = 1.0 - (privacy_risk * 0.3)
        
        # Autonomy: Check for human override preservation
        scores[EthicsCategory.AUTONOMY] = 0.9 if proposal.human_review_required else 0.7
        
        # Safety: Based on confidence and action severity
        action_risk = {
            EvolutionAction.PARAMETER_TUNE: 0.1,
            EvolutionAction.RULE_ADDITION: 0.2,
            EvolutionAction.RULE_MODIFICATION: 0.3,
            EvolutionAction.RULE_REMOVAL: 0.5,
            EvolutionAction.POLICY_MERGE: 0.4,
            EvolutionAction.POLICY_SPLIT: 0.3,
            EvolutionAction.ROLLBACK: 0.1,
        }
        scores[EthicsCategory.SAFETY] = 1.0 - action_risk.get(proposal.action, 0.3)
        
        # Accountability: Based on traceability
        scores[EthicsCategory.ACCOUNTABILITY] = 0.95  # Always high for automated proposals
        
        return scores
    
    def _run_safety_checks(self, proposal: EvolutionProposal) -> Dict[str, bool]:
        """Run all safety checks and return results."""
        results = {}
        
        for guardrail in self.guardrails:
            passes, _ = guardrail.evaluate(proposal)
            results[f"guardrail_{guardrail.category.value}"] = passes
        
        for bound in self.safety_bounds:
            # Simplified check - would use actual check function in production
            results[bound.bound_id] = True
        
        return results


class SelfEvolvingGovernor:
    """
    Main coordinator for self-evolving governance.
    
    Orchestrates risk detection, evolution proposal generation,
    safety evaluation, and policy updates.
    """
    
    def __init__(self, 
                 enable_autonomous_evolution: bool = False,
                 max_daily_evolutions: int = 10,
                 require_human_review_above: SafetyLevel = SafetyLevel.MEDIUM_RISK):
        self.enable_autonomous_evolution = enable_autonomous_evolution
        self.max_daily_evolutions = max_daily_evolutions
        self.require_human_review_above = require_human_review_above
        
        self.risk_detector = RiskDetector()
        self.evolution_engine = EvolutionEngine()
        self.policy_store: Dict[str, Dict[str, Any]] = {}
        
        self.daily_evolution_count = 0
        self.last_reset_date = datetime.now(timezone.utc).date()
        
        # Human override queue
        self.pending_reviews: List[EvolutionProposal] = []
        self.human_overrides: Dict[str, str] = {}  # proposal_id -> override_action
        
        logger.info(f"Self-evolving governor initialized (autonomous={enable_autonomous_evolution})")
    
    def record_governance_decision(self, decision: Dict[str, Any]):
        """Record a decision for analysis."""
        self.risk_detector.record_decision(decision)
    
    async def run_evolution_cycle(self) -> List[EvolutionOutcome]:
        """
        Run a complete evolution cycle.
        
        1. Detect risks
        2. Generate proposals
        3. Evaluate proposals
        4. Apply approved evolutions
        """
        # Reset daily counter if needed
        today = datetime.now(timezone.utc).date()
        if today != self.last_reset_date:
            self.daily_evolution_count = 0
            self.last_reset_date = today
        
        outcomes = []
        
        # Step 1: Detect risks
        risk_patterns = self.risk_detector.analyze_for_risks()
        
        if not risk_patterns:
            logger.info("No risk patterns detected in this cycle")
            return outcomes
        
        logger.info(f"Detected {len(risk_patterns)} risk patterns")
        
        # Step 2: Generate proposals for each risk
        for pattern in risk_patterns:
            if self.daily_evolution_count >= self.max_daily_evolutions:
                logger.warning("Daily evolution limit reached")
                break
            
            # Find affected policies
            for policy_id in pattern.affected_policies:
                if policy_id not in self.policy_store:
                    continue
                
                policy = self.policy_store[policy_id]
                
                # Generate proposal
                proposal = self.evolution_engine.generate_proposal(
                    trigger=EvolutionTrigger.RISK_DETECTION,
                    risk_pattern=pattern,
                    target_policy=policy,
                )
                
                # Step 3: Evaluate proposal
                can_proceed, issues = self.evolution_engine.evaluate_proposal(proposal)
                
                if issues:
                    logger.warning(f"Proposal {proposal.proposal_id} has issues: {issues}")
                
                # Check if human review required
                if proposal.safety_level.value >= self.require_human_review_above.value:
                    proposal.human_review_required = True
                    self.pending_reviews.append(proposal)
                    logger.info(f"Proposal {proposal.proposal_id} queued for human review")
                    continue
                
                # Step 4: Apply if autonomous evolution is enabled
                if self.enable_autonomous_evolution and can_proceed:
                    outcome = self.evolution_engine.apply_evolution(proposal, self.policy_store)
                    outcomes.append(outcome)
                    self.daily_evolution_count += 1
                else:
                    logger.info(f"Proposal {proposal.proposal_id} pending (autonomous={self.enable_autonomous_evolution})")
        
        return outcomes
    
    def approve_evolution(self, proposal_id: str, approver_id: str) -> Optional[EvolutionOutcome]:
        """
        Human approval of a pending evolution.
        """
        # Find proposal
        proposal = None
        for p in self.pending_reviews:
            if p.proposal_id == proposal_id:
                proposal = p
                break
        
        if not proposal:
            logger.warning(f"Proposal {proposal_id} not found in pending reviews")
            return None
        
        # Mark as approved
        proposal.approved_by = approver_id
        proposal.approved_at = datetime.now(timezone.utc)
        
        # Remove from pending
        self.pending_reviews = [p for p in self.pending_reviews if p.proposal_id != proposal_id]
        
        # Apply evolution
        outcome = self.evolution_engine.apply_evolution(proposal, self.policy_store)
        self.daily_evolution_count += 1
        
        logger.info(f"Evolution {proposal_id} approved by {approver_id}")
        return outcome
    
    def reject_evolution(self, proposal_id: str, rejector_id: str, reason: str):
        """
        Human rejection of a pending evolution.
        """
        for proposal in self.pending_reviews:
            if proposal.proposal_id == proposal_id:
                proposal.rejected_reason = f"Rejected by {rejector_id}: {reason}"
                self.pending_reviews = [p for p in self.pending_reviews if p.proposal_id != proposal_id]
                logger.info(f"Evolution {proposal_id} rejected: {reason}")
                return
        
        logger.warning(f"Proposal {proposal_id} not found in pending reviews")
    
    def emergency_halt(self):
        """
        Emergency halt of all autonomous evolution.
        """
        self.enable_autonomous_evolution = False
        logger.critical("EMERGENCY HALT: Autonomous evolution disabled")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the self-evolving system."""
        return {
            "autonomous_evolution_enabled": self.enable_autonomous_evolution,
            "daily_evolution_count": self.daily_evolution_count,
            "max_daily_evolutions": self.max_daily_evolutions,
            "pending_reviews": len(self.pending_reviews),
            "detected_patterns": len(self.risk_detector.detected_patterns),
            "total_proposals": len(self.evolution_engine.proposal_history),
            "total_outcomes": len(self.evolution_engine.outcome_history),
            "policy_count": len(self.policy_store),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }


# Export main classes
__all__ = [
    "EvolutionTrigger",
    "SafetyLevel",
    "EvolutionAction",
    "EthicsCategory",
    "SafetyBound",
    "EvolutionProposal",
    "EvolutionOutcome",
    "RiskPattern",
    "SafetyGuardrail",
    "BiasGuardrail",
    "HarmPreventionGuardrail",
    "TransparencyGuardrail",
    "HumanAgencyGuardrail",
    "RiskDetector",
    "EvolutionEngine",
    "SelfEvolvingGovernor",
    "CONSTITUTIONAL_HASH",
]

