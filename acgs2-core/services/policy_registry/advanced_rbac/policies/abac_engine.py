"""
ACGS-2 Attribute-Based Access Control (ABAC) Engine
Constitutional Hash: cdd01ef066bc6cf2
"""

import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Add acgs2-core/shared to path for type imports
shared_path = Path(__file__).parent.parent.parent.parent.parent / "shared"
if str(shared_path) not in sys.path:
    sys.path.insert(0, str(shared_path))

from types import JSONDict, JSONValue

from ..models.abac_models import (
    ABACPolicy,
    ABACRule,
    AccessRequest,
    Attribute,
    AttributeCondition,
    ComparisonOperator,
    LogicalOperator,
    PolicyDecision,
)


class ABACPolicyEngine:
    """ABAC Policy Engine for evaluating access requests"""

    def __init__(self):
        self.policies: Dict[str, ABACPolicy] = {}
        self.policy_index: Dict[str, Set[str]] = defaultdict(set)  # attribute -> policies
        self.evaluation_cache: Dict[str, Tuple[PolicyDecision, float]] = {}
        self.cache_ttl_seconds = 300  # 5 minutes

    def register_policy(self, policy: ABACPolicy) -> None:
        """Register an ABAC policy"""
        self.policies[policy.policy_id] = policy

        # Update index for faster policy matching
        for condition in policy.target_conditions:
            self.policy_index[condition.attribute_name].add(policy.policy_id)

        for rule in policy.rules:
            for condition in rule.conditions:
                self.policy_index[condition.attribute_name].add(policy.policy_id)

    def unregister_policy(self, policy_id: str) -> None:
        """Unregister an ABAC policy"""
        if policy_id in self.policies:
            policy = self.policies[policy_id]

            # Remove from index
            for condition in policy.target_conditions:
                self.policy_index[condition.attribute_name].discard(policy_id)

            for rule in policy.rules:
                for condition in rule.conditions:
                    self.policy_index[condition.attribute_name].discard(policy_id)

            del self.policies[policy_id]

    def evaluate_access(self, request: AccessRequest) -> PolicyDecision:
        """Evaluate an access request against all policies"""
        start_time = time.time()

        # Check cache first
        cache_key = self._generate_cache_key(request)
        if cache_key in self.evaluation_cache:
            cached_decision, cache_time = self.evaluation_cache[cache_key]
            if time.time() - cache_time < self.cache_ttl_seconds:
                return cached_decision

        # Find applicable policies
        applicable_policies = self._find_applicable_policies(request)

        # Evaluate policies
        decision = self._evaluate_policies(applicable_policies, request)

        # Cache the result
        evaluation_time = (time.time() - start_time) * 1000  # milliseconds
        decision.evaluation_time_ms = evaluation_time
        self.evaluation_cache[cache_key] = (decision, time.time())

        return decision

    def _find_applicable_policies(self, request: AccessRequest) -> List[ABACPolicy]:
        """Find policies that apply to the request"""
        applicable_policies = []

        # Get all attributes from the request
        all_attributes = self._collect_request_attributes(request)

        # Find candidate policies based on attribute index
        candidate_policy_ids = set()
        for attr_name in all_attributes.keys():
            candidate_policy_ids.update(self.policy_index[attr_name])

        # If no candidates from index, check all policies (fallback)
        if not candidate_policy_ids:
            candidate_policy_ids = set(self.policies.keys())

        # Filter policies based on target conditions
        for policy_id in candidate_policy_ids:
            policy = self.policies.get(policy_id)
            if policy and policy.enabled:
                if self._matches_target_conditions(policy, request):
                    applicable_policies.append(policy)

        return applicable_policies

    def _evaluate_policies(
        self, policies: List[ABACPolicy], request: AccessRequest
    ) -> PolicyDecision:
        """Evaluate policies using the specified combining algorithm"""
        matched_rules = []
        denied_rules = []
        obligations = []
        advice = []

        # Sort policies by priority (higher priority first)
        policies.sort(key=lambda p: getattr(p, "priority", 0), reverse=True)

        for policy in policies:
            decision = self._evaluate_single_policy(policy, request)

            if decision.decision == "allow":
                matched_rules.extend(decision.matched_rules)
                obligations.extend(decision.obligations)
                advice.extend(decision.advice)

                if policy.combining_algorithm == "first-applicable":
                    break

            elif decision.decision == "deny":
                denied_rules.extend(decision.denied_rules)

                if policy.combining_algorithm == "deny-overrides":
                    return PolicyDecision(
                        decision="deny",
                        confidence_score=decision.confidence_score,
                        matched_rules=matched_rules,
                        denied_rules=denied_rules,
                        obligations=obligations,
                        advice=advice,
                    )

        # Determine final decision
        if denied_rules and not matched_rules:
            final_decision = "deny"
            confidence = 0.8
        elif matched_rules:
            final_decision = "allow"
            confidence = 0.9
        else:
            final_decision = "not_applicable"
            confidence = 0.5

        return PolicyDecision(
            decision=final_decision,
            confidence_score=confidence,
            matched_rules=matched_rules,
            denied_rules=denied_rules,
            obligations=obligations,
            advice=advice,
        )

    def _evaluate_single_policy(self, policy: ABACPolicy, request: AccessRequest) -> PolicyDecision:
        """Evaluate a single policy"""
        matched_allow_rules = []
        matched_deny_rules = []

        # Evaluate deny rules first (deny-overrides within policy)
        for rule in policy.deny_rules:
            if rule.enabled and self._evaluate_rule(rule, request):
                matched_deny_rules.append(rule.rule_id)

        # Evaluate allow rules
        for rule in policy.allow_rules:
            if rule.enabled and self._evaluate_rule(rule, request):
                matched_allow_rules.append(rule.rule_id)

        # Determine policy decision
        if matched_deny_rules:
            return PolicyDecision(
                decision="deny",
                confidence_score=0.9,
                matched_rules=[],
                denied_rules=matched_deny_rules,
            )
        elif matched_allow_rules:
            return PolicyDecision(
                decision="allow",
                confidence_score=0.9,
                matched_rules=matched_allow_rules,
                denied_rules=[],
            )
        else:
            return PolicyDecision(
                decision="not_applicable", confidence_score=0.5, matched_rules=[], denied_rules=[]
            )

    def _evaluate_rule(self, rule: ABACRule, request: AccessRequest) -> bool:
        """Evaluate a single rule"""
        conditions_results = []

        for condition in rule.conditions:
            result = self._evaluate_condition(condition, request)
            conditions_results.append(result)

        # Combine conditions based on logical operator
        if rule.logical_operator == LogicalOperator.AND:
            return all(conditions_results)
        elif rule.logical_operator == LogicalOperator.OR:
            return any(conditions_results)
        else:  # NOT
            return not all(conditions_results)

    def _evaluate_condition(self, condition: AttributeCondition, request: AccessRequest) -> bool:
        """Evaluate a single condition"""
        # Get attribute value from request
        attribute_value = self._get_attribute_value(condition.attribute_name, request)

        if attribute_value is None:
            return False

        # Apply the comparison operator
        operator = condition.operator
        expected = condition.expected_value

        try:
            if operator == ComparisonOperator.EQUALS:
                return self._equals_comparison(attribute_value, expected, condition.case_sensitive)
            elif operator == ComparisonOperator.NOT_EQUALS:
                return not self._equals_comparison(
                    attribute_value, expected, condition.case_sensitive
                )
            elif operator == ComparisonOperator.GREATER_THAN:
                return float(attribute_value) > float(expected)
            elif operator == ComparisonOperator.GREATER_THAN_EQUAL:
                return float(attribute_value) >= float(expected)
            elif operator == ComparisonOperator.LESS_THAN:
                return float(attribute_value) < float(expected)
            elif operator == ComparisonOperator.LESS_THAN_EQUAL:
                return float(attribute_value) <= float(expected)
            elif operator == ComparisonOperator.CONTAINS:
                return self._contains_comparison(
                    attribute_value, expected, condition.case_sensitive
                )
            elif operator == ComparisonOperator.NOT_CONTAINS:
                return not self._contains_comparison(
                    attribute_value, expected, condition.case_sensitive
                )
            elif operator == ComparisonOperator.IN:
                return attribute_value in expected
            elif operator == ComparisonOperator.NOT_IN:
                return attribute_value not in expected
            elif operator == ComparisonOperator.REGEX_MATCH:
                return bool(re.match(expected, str(attribute_value)))
            elif operator == ComparisonOperator.STARTS_WITH:
                return str(attribute_value).startswith(str(expected))
            elif operator == ComparisonOperator.ENDS_WITH:
                return str(attribute_value).endswith(str(expected))
            else:
                return False

        except (ValueError, TypeError):
            return False

    def _get_attribute_value(self, attribute_name: str, request: AccessRequest) -> JSONValue:
        """Get attribute value from request"""
        # Check all attribute categories
        all_attributes = {}

        # Flatten all attribute categories
        for category_name, category_attrs in [
            ("subject", request.subject_attributes),
            ("resource", request.resource_attributes),
            ("action", request.action_attributes),
            ("environment", request.environment_attributes),
            ("context", request.context_attributes),
        ]:
            for attr_name, attr in category_attrs.items():
                full_name = f"{category_name}.{attr_name}"
                all_attributes[full_name] = attr.value
                all_attributes[attr_name] = attr.value  # Also allow short names

        return all_attributes.get(attribute_name)

    def _collect_request_attributes(self, request: AccessRequest) -> Dict[str, Attribute]:
        """Collect all attributes from the request"""
        all_attributes = {}

        for category_attrs in [
            request.subject_attributes,
            request.resource_attributes,
            request.action_attributes,
            request.environment_attributes,
            request.context_attributes,
        ]:
            all_attributes.update(category_attrs)

        return all_attributes

    def _matches_target_conditions(self, policy: ABACPolicy, request: AccessRequest) -> bool:
        """Check if policy target conditions match the request"""
        for condition in policy.target_conditions:
            if not self._evaluate_condition(condition, request):
                return False
        return True

    def _equals_comparison(
        self, actual: JSONValue, expected: JSONValue, case_sensitive: bool
    ) -> bool:
        """Compare values for equality"""
        if not case_sensitive and isinstance(actual, str) and isinstance(expected, str):
            return actual.lower() == expected.lower()
        return actual == expected

    def _contains_comparison(
        self, actual: JSONValue, expected: JSONValue, case_sensitive: bool
    ) -> bool:
        """Check if actual contains expected"""
        actual_str = str(actual)
        expected_str = str(expected)

        if not case_sensitive:
            return expected_str.lower() in actual_str.lower()
        return expected_str in actual_str

    def _generate_cache_key(self, request: AccessRequest) -> str:
        """Generate a cache key for the request"""
        # Create a deterministic key based on request attributes
        key_parts = [
            request.request_id,
            str(sorted(request.subject_attributes.items())),
            str(sorted(request.resource_attributes.items())),
            str(sorted(request.action_attributes.items())),
            str(sorted(request.environment_attributes.items())),
            str(sorted(request.context_attributes.items())),
        ]

        return "|".join(key_parts)

    def clear_cache(self) -> None:
        """Clear the evaluation cache"""
        self.evaluation_cache.clear()

    def get_cache_stats(self) -> JSONDict:
        """Get cache statistics"""
        return {
            "cache_size": len(self.evaluation_cache),
            "cache_ttl_seconds": self.cache_ttl_seconds,
        }

    def get_policy_stats(self) -> JSONDict:
        """Get policy statistics"""
        total_policies = len(self.policies)
        enabled_policies = sum(1 for p in self.policies.values() if p.enabled)
        total_rules = sum(len(p.rules) for p in self.policies.values())
        enabled_rules = sum(len([r for r in p.rules if r.enabled]) for p in self.policies.values())

        return {
            "total_policies": total_policies,
            "enabled_policies": enabled_policies,
            "disabled_policies": total_policies - enabled_policies,
            "total_rules": total_rules,
            "enabled_rules": enabled_rules,
            "disabled_rules": total_rules - enabled_rules,
        }


class PolicyDecisionCache:
    """Cache for policy decisions with TTL"""

    def __init__(self, ttl_seconds: int = 300):
        self.cache: Dict[str, Tuple[PolicyDecision, float]] = {}
        self.ttl_seconds = ttl_seconds

    def get(self, key: str) -> Optional[PolicyDecision]:
        """Get cached decision if still valid"""
        if key in self.cache:
            decision, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                return decision
            else:
                del self.cache[key]
        return None

    def put(self, key: str, decision: PolicyDecision) -> None:
        """Cache a decision"""
        self.cache[key] = (decision, time.time())

    def clear(self) -> None:
        """Clear all cached decisions"""
        self.cache.clear()

    def cleanup_expired(self) -> int:
        """Remove expired entries and return count removed"""
        current_time = time.time()
        expired_keys = [
            key
            for key, (_, timestamp) in self.cache.items()
            if current_time - timestamp >= self.ttl_seconds
        ]

        for key in expired_keys:
            del self.cache[key]

        return len(expired_keys)

    def size(self) -> int:
        """Get current cache size"""
        return len(self.cache)


# Global ABAC engine instance
abac_engine = ABACPolicyEngine()


# Convenience functions
def register_abac_policy(policy: ABACPolicy) -> None:
    """Register an ABAC policy"""
    abac_engine.register_policy(policy)


def evaluate_access_request(request: AccessRequest) -> PolicyDecision:
    """Evaluate an access request"""
    return abac_engine.evaluate_access(request)


def get_policy_stats() -> JSONDict:
    """Get policy engine statistics"""
    return abac_engine.get_policy_stats()
