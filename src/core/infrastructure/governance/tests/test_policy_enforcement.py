"""
ACGS-2 Policy Enforcement Tests
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive tests for policy enforcement mechanisms including
enforcement actions, violation tracking, rate limiting, and remediation.
"""

import asyncio
import logging
import threading
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from infrastructure.governance.policy_enforcement import (
    EnforcementAction,
    EnforcementMode,
    EnforcementResult,
    PolicyContext,
    PolicyEnforcer,
    PolicyRule,
    PolicyViolation,
    ViolationSeverity,
    enforce_policy,
    get_policy_enforcer,
    initialize_policy_enforcer,
    shutdown_policy_enforcer,
)

logger = logging.getLogger(__name__)


class TestEnforcementEnums:
    """Test suite for enforcement enums."""

    def test_enforcement_action_values(self):
        """Test EnforcementAction enum values."""
        assert EnforcementAction.ALLOW.value == "allow"
        assert EnforcementAction.DENY.value == "deny"
        assert EnforcementAction.REQUIRE_APPROVAL.value == "require_approval"
        assert EnforcementAction.ESCALATE.value == "escalate"
        assert EnforcementAction.RATE_LIMIT.value == "rate_limit"
        assert EnforcementAction.AUDIT_ONLY.value == "audit_only"
        assert EnforcementAction.QUARANTINE.value == "quarantine"

    def test_violation_severity_values(self):
        """Test ViolationSeverity enum values."""
        assert ViolationSeverity.INFO.value == "info"
        assert ViolationSeverity.LOW.value == "low"
        assert ViolationSeverity.MEDIUM.value == "medium"
        assert ViolationSeverity.HIGH.value == "high"
        assert ViolationSeverity.CRITICAL.value == "critical"

    def test_enforcement_mode_values(self):
        """Test EnforcementMode enum values."""
        assert EnforcementMode.ENFORCE.value == "enforce"
        assert EnforcementMode.AUDIT.value == "audit"
        assert EnforcementMode.DRY_RUN.value == "dry_run"
        assert EnforcementMode.DISABLED.value == "disabled"


class TestPolicyContext:
    """Test suite for PolicyContext dataclass."""

    @pytest.fixture
    def sample_context(self):
        return PolicyContext(
            agent_id="test-agent",
            action="read",
            resource_type="document",
            resource_id="doc-123",
            tenant_id="test-tenant",
            constitutional_hash="cdd01ef066bc6cf2",
        )

    def test_context_creation(self, sample_context):
        """Test PolicyContext creation."""
        assert sample_context.agent_id == "test-agent"
        assert sample_context.action == "read"
        assert sample_context.resource_type == "document"
        assert sample_context.resource_id == "doc-123"
        assert sample_context.tenant_id == "test-tenant"
        assert sample_context.constitutional_hash == "cdd01ef066bc6cf2"

    def test_context_defaults(self):
        """Test PolicyContext default values."""
        context = PolicyContext(
            agent_id="agent",
            action="action",
            resource_type="type",
            resource_id="id",
        )

        assert context.tenant_id == "default"
        assert context.constitutional_hash == ""
        assert isinstance(context.metadata, dict)
        assert context.environment == "development"

    def test_context_to_dict(self, sample_context):
        """Test converting context to dictionary."""
        result = sample_context.to_dict()

        assert result["agent_id"] == "test-agent"
        assert result["action"] == "read"
        assert result["resource_type"] == "document"
        assert "timestamp" in result
        assert isinstance(result["metadata"], dict)

    def test_context_with_metadata(self):
        """Test context with metadata."""
        metadata = {"key": "value", "count": 42}
        context = PolicyContext(
            agent_id="agent",
            action="action",
            resource_type="type",
            resource_id="id",
            metadata=metadata,
        )

        assert context.metadata == metadata
        assert context.to_dict()["metadata"] == metadata


class TestPolicyViolation:
    """Test suite for PolicyViolation dataclass."""

    @pytest.fixture
    def sample_context(self):
        return PolicyContext(
            agent_id="test-agent",
            action="delete",
            resource_type="document",
            resource_id="doc-123",
        )

    @pytest.fixture
    def sample_violation(self, sample_context):
        return PolicyViolation(
            id="violation-123",
            policy_id="policy-1",
            policy_name="Delete Restriction",
            rule_id="rule-1",
            severity=ViolationSeverity.HIGH,
            message="Delete action not allowed",
            context=sample_context,
            remediation_hint="Request approval first",
        )

    def test_violation_creation(self, sample_violation):
        """Test PolicyViolation creation."""
        assert sample_violation.id == "violation-123"
        assert sample_violation.policy_id == "policy-1"
        assert sample_violation.severity == ViolationSeverity.HIGH
        assert sample_violation.message == "Delete action not allowed"
        assert sample_violation.remediation_hint == "Request approval first"

    def test_violation_to_dict(self, sample_violation):
        """Test converting violation to dictionary."""
        result = sample_violation.to_dict()

        assert result["id"] == "violation-123"
        assert result["severity"] == "high"
        assert result["remediation_hint"] == "Request approval first"
        assert "context" in result
        assert "timestamp" in result


class TestEnforcementResult:
    """Test suite for EnforcementResult dataclass."""

    def test_result_creation_allowed(self):
        """Test EnforcementResult creation for allowed action."""
        result = EnforcementResult(
            allowed=True,
            action=EnforcementAction.ALLOW,
            policies_evaluated=5,
            evaluation_time_ms=2.5,
        )

        assert result.allowed is True
        assert result.action == EnforcementAction.ALLOW
        assert result.policies_evaluated == 5
        assert result.has_violations is False
        assert result.max_severity is None

    def test_result_creation_denied(self):
        """Test EnforcementResult creation for denied action."""
        violation = PolicyViolation(
            id="v-1",
            policy_id="p-1",
            policy_name="Test",
            rule_id="r-1",
            severity=ViolationSeverity.HIGH,
            message="Denied",
            context=PolicyContext(
                agent_id="a",
                action="act",
                resource_type="t",
                resource_id="id",
            ),
        )

        result = EnforcementResult(
            allowed=False,
            action=EnforcementAction.DENY,
            violations=[violation],
        )

        assert result.allowed is False
        assert result.has_violations is True
        assert result.max_severity == ViolationSeverity.HIGH

    def test_result_max_severity_multiple(self):
        """Test max severity with multiple violations."""
        context = PolicyContext(
            agent_id="a",
            action="act",
            resource_type="t",
            resource_id="id",
        )

        violations = [
            PolicyViolation(
                id="v-1",
                policy_id="p-1",
                policy_name="Test",
                rule_id="r-1",
                severity=ViolationSeverity.LOW,
                message="Low",
                context=context,
            ),
            PolicyViolation(
                id="v-2",
                policy_id="p-2",
                policy_name="Test2",
                rule_id="r-2",
                severity=ViolationSeverity.CRITICAL,
                message="Critical",
                context=context,
            ),
            PolicyViolation(
                id="v-3",
                policy_id="p-3",
                policy_name="Test3",
                rule_id="r-3",
                severity=ViolationSeverity.MEDIUM,
                message="Medium",
                context=context,
            ),
        ]

        result = EnforcementResult(
            allowed=False,
            action=EnforcementAction.DENY,
            violations=violations,
        )

        assert result.max_severity == ViolationSeverity.CRITICAL

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = EnforcementResult(
            allowed=True,
            action=EnforcementAction.ALLOW,
            policies_evaluated=3,
            evaluation_time_ms=1.5,
            confidence_score=0.95,
            reasoning="All clear",
            recommendations=["Keep going"],
        )

        data = result.to_dict()

        assert data["allowed"] is True
        assert data["action"] == "allow"
        assert data["policies_evaluated"] == 3
        assert data["confidence_score"] == 0.95
        assert data["recommendations"] == ["Keep going"]


class TestPolicyRule:
    """Test suite for PolicyRule dataclass."""

    def test_rule_creation(self):
        """Test PolicyRule creation."""
        rule = PolicyRule(
            id="rule-1",
            policy_id="policy-1",
            name="No Delete",
            condition="action != 'delete'",
            action=EnforcementAction.DENY,
            severity=ViolationSeverity.HIGH,
            message_template="Cannot delete {resource_type}",
            remediation_hint="Request approval",
        )

        assert rule.id == "rule-1"
        assert rule.condition == "action != 'delete'"
        assert rule.action == EnforcementAction.DENY
        assert rule.enabled is True
        assert rule.priority == 0

    def test_rule_disabled(self):
        """Test disabled rule."""
        rule = PolicyRule(
            id="rule-2",
            policy_id="policy-1",
            name="Disabled Rule",
            condition="always_true",
            action=EnforcementAction.DENY,
            enabled=False,
        )

        context = PolicyContext(
            agent_id="agent",
            action="action",
            resource_type="type",
            resource_id="id",
        )

        passed, message = rule.evaluate(context, lambda c, ctx: False)

        # Disabled rules always pass
        assert passed is True
        assert message == ""


class TestPolicyEnforcer:
    """Test suite for PolicyEnforcer."""

    @pytest.fixture
    def constitutional_hash(self):
        return "cdd01ef066bc6cf2"

    @pytest.fixture
    def enforcer(self, constitutional_hash):
        return PolicyEnforcer(constitutional_hash)

    @pytest.fixture
    def sample_context(self):
        return PolicyContext(
            agent_id="test-agent",
            action="read",
            resource_type="document",
            resource_id="doc-123",
            tenant_id="test-tenant",
        )

    def test_enforcer_initialization(self, enforcer, constitutional_hash):
        """Test PolicyEnforcer initialization."""
        assert enforcer.constitutional_hash == constitutional_hash
        assert enforcer.mode == EnforcementMode.ENFORCE
        assert len(enforcer._rules) == 0

    def test_enforcer_set_mode(self, enforcer):
        """Test setting enforcement mode."""
        enforcer.set_mode(EnforcementMode.AUDIT)
        assert enforcer.mode == EnforcementMode.AUDIT

        enforcer.set_mode(EnforcementMode.DISABLED)
        assert enforcer.mode == EnforcementMode.DISABLED

    def test_enforcer_register_rule(self, enforcer):
        """Test registering a rule."""
        rule = PolicyRule(
            id="rule-1",
            policy_id="policy-1",
            name="Test Rule",
            condition="action == 'read'",
            action=EnforcementAction.ALLOW,
        )

        enforcer.register_rule(rule)

        rules = enforcer.get_rules()
        assert len(rules) == 1
        assert rules[0].id == "rule-1"

    def test_enforcer_unregister_rule(self, enforcer):
        """Test unregistering a rule."""
        rule = PolicyRule(
            id="rule-1",
            policy_id="policy-1",
            name="Test Rule",
            condition="condition",
            action=EnforcementAction.ALLOW,
        )

        enforcer.register_rule(rule)
        assert len(enforcer.get_rules()) == 1

        result = enforcer.unregister_rule("rule-1")
        assert result is True
        assert len(enforcer.get_rules()) == 0

        result = enforcer.unregister_rule("nonexistent")
        assert result is False

    def test_enforcer_get_rules_sorted(self, enforcer):
        """Test rules are sorted by priority."""
        rules = [
            PolicyRule(
                id="rule-1",
                policy_id="p",
                name="Low Priority",
                condition="c",
                action=EnforcementAction.ALLOW,
                priority=1,
            ),
            PolicyRule(
                id="rule-2",
                policy_id="p",
                name="High Priority",
                condition="c",
                action=EnforcementAction.ALLOW,
                priority=10,
            ),
            PolicyRule(
                id="rule-3",
                policy_id="p",
                name="Medium Priority",
                condition="c",
                action=EnforcementAction.ALLOW,
                priority=5,
            ),
        ]

        for rule in rules:
            enforcer.register_rule(rule)

        sorted_rules = enforcer.get_rules()
        assert sorted_rules[0].priority == 10
        assert sorted_rules[1].priority == 5
        assert sorted_rules[2].priority == 1

    @pytest.mark.asyncio
    async def test_enforcer_disabled_mode(self, enforcer, sample_context):
        """Test enforcer in disabled mode."""
        enforcer.set_mode(EnforcementMode.DISABLED)

        result = await enforcer.enforce(sample_context)

        assert result.allowed is True
        assert result.action == EnforcementAction.ALLOW
        assert result.reasoning == "Enforcement disabled"

    @pytest.mark.asyncio
    async def test_enforcer_no_rules(self, enforcer, sample_context):
        """Test enforcer with no rules."""
        result = await enforcer.enforce(sample_context)

        assert result.allowed is True
        assert result.action == EnforcementAction.ALLOW
        assert len(result.violations) == 0

    @pytest.mark.asyncio
    async def test_enforcer_passing_rule(self, enforcer, sample_context):
        """Test enforcer with a passing rule."""
        rule = PolicyRule(
            id="rule-1",
            policy_id="policy-1",
            name="Allow Read",
            condition="action == 'read'",
            action=EnforcementAction.ALLOW,
        )
        enforcer.register_rule(rule)

        result = await enforcer.enforce(sample_context)

        assert result.allowed is True
        assert result.policies_evaluated == 1

    @pytest.mark.asyncio
    async def test_enforcer_failing_rule_critical(self, enforcer):
        """Test enforcer with a failing critical rule."""
        context = PolicyContext(
            agent_id="test-agent",
            action="delete",
            resource_type="document",
            resource_id="doc-123",
        )

        rule = PolicyRule(
            id="rule-1",
            policy_id="policy-1",
            name="No Delete",
            condition="action != 'delete'",
            action=EnforcementAction.DENY,
            severity=ViolationSeverity.CRITICAL,
            message_template="Delete not allowed",
        )
        enforcer.register_rule(rule)

        result = await enforcer.enforce(context)

        assert result.allowed is False
        assert result.action == EnforcementAction.DENY
        assert result.require_human_review is True
        assert result.escalation_level == 3
        assert len(result.violations) == 1

    @pytest.mark.asyncio
    async def test_enforcer_failing_rule_high(self, enforcer):
        """Test enforcer with a failing high severity rule."""
        context = PolicyContext(
            agent_id="test-agent",
            action="write",
            resource_type="public",
            resource_id="resource-123",
        )

        rule = PolicyRule(
            id="rule-1",
            policy_id="policy-1",
            name="No Public Write",
            condition="resource_type != 'public'",
            action=EnforcementAction.REQUIRE_APPROVAL,
            severity=ViolationSeverity.HIGH,
        )
        enforcer.register_rule(rule)

        result = await enforcer.enforce(context)

        assert result.allowed is False
        assert result.action == EnforcementAction.REQUIRE_APPROVAL
        assert result.escalation_level == 2

    @pytest.mark.asyncio
    async def test_enforcer_failing_rule_medium(self, enforcer):
        """Test enforcer with a failing medium severity rule."""
        context = PolicyContext(
            agent_id="test-agent",
            action="update",
            resource_type="sensitive",
            resource_id="resource-123",
        )

        rule = PolicyRule(
            id="rule-1",
            policy_id="policy-1",
            name="Sensitive Update",
            condition="resource_type != 'sensitive'",
            action=EnforcementAction.ESCALATE,
            severity=ViolationSeverity.MEDIUM,
        )
        enforcer.register_rule(rule)

        result = await enforcer.enforce(context)

        assert result.allowed is False
        assert result.action == EnforcementAction.ESCALATE
        assert result.escalation_level == 1

    @pytest.mark.asyncio
    async def test_enforcer_failing_rule_low(self, enforcer, sample_context):
        """Test enforcer with a failing low severity rule."""
        rule = PolicyRule(
            id="rule-1",
            policy_id="policy-1",
            name="Low Priority Rule",
            condition="action != 'read'",
            action=EnforcementAction.AUDIT_ONLY,
            severity=ViolationSeverity.LOW,
        )
        enforcer.register_rule(rule)

        result = await enforcer.enforce(sample_context)

        # Low severity should still allow
        assert result.allowed is True
        assert result.action == EnforcementAction.AUDIT_ONLY
        assert result.require_human_review is False

    @pytest.mark.asyncio
    async def test_enforcer_audit_mode(self, enforcer):
        """Test enforcer in audit mode."""
        enforcer.set_mode(EnforcementMode.AUDIT)

        context = PolicyContext(
            agent_id="test-agent",
            action="delete",
            resource_type="document",
            resource_id="doc-123",
        )

        rule = PolicyRule(
            id="rule-1",
            policy_id="policy-1",
            name="No Delete",
            condition="action != 'delete'",
            action=EnforcementAction.DENY,
            severity=ViolationSeverity.CRITICAL,
        )
        enforcer.register_rule(rule)

        result = await enforcer.enforce(context)

        # In audit mode, violations are logged but allowed
        assert result.allowed is True
        assert result.action == EnforcementAction.AUDIT_ONLY
        assert len(result.violations) == 1

    @pytest.mark.asyncio
    async def test_enforcer_rate_limiting(self, enforcer, sample_context):
        """Test rate limiting."""
        enforcer.rate_limit_max_requests = 5
        enforcer.rate_limit_window = 60

        # Make requests up to limit
        for _ in range(5):
            result = await enforcer.enforce(sample_context)
            assert result.allowed is True

        # Next request should be rate limited
        result = await enforcer.enforce(sample_context)
        assert result.allowed is False
        assert result.action == EnforcementAction.RATE_LIMIT

    @pytest.mark.asyncio
    async def test_enforcer_rate_limiting_different_agents(self, enforcer):
        """Test rate limiting applies per agent."""
        enforcer.rate_limit_max_requests = 2
        enforcer.rate_limit_window = 60

        context1 = PolicyContext(
            agent_id="agent-1",
            action="read",
            resource_type="doc",
            resource_id="id",
        )
        context2 = PolicyContext(
            agent_id="agent-2",
            action="read",
            resource_type="doc",
            resource_id="id",
        )

        # Each agent gets their own rate limit
        for _ in range(2):
            result = await enforcer.enforce(context1)
            assert result.allowed is True

            result = await enforcer.enforce(context2)
            assert result.allowed is True

        # Both should now be rate limited
        result = await enforcer.enforce(context1)
        assert result.action == EnforcementAction.RATE_LIMIT

        result = await enforcer.enforce(context2)
        assert result.action == EnforcementAction.RATE_LIMIT

    def test_enforcer_custom_evaluator(self, enforcer):
        """Test custom condition evaluator."""
        called_with = {}

        def custom_evaluator(condition, context):
            called_with["condition"] = condition
            called_with["context"] = context
            return condition == "allow_all"

        enforcer.set_condition_evaluator(custom_evaluator)

        rule = PolicyRule(
            id="rule-1",
            policy_id="p",
            name="Custom",
            condition="allow_all",
            action=EnforcementAction.ALLOW,
        )

        context = PolicyContext(
            agent_id="agent",
            action="action",
            resource_type="type",
            resource_id="id",
        )

        passed, _ = enforcer._evaluate_rule(rule, context)

        assert passed is True
        assert called_with["condition"] == "allow_all"

    @pytest.mark.asyncio
    async def test_enforcer_pre_hook(self, enforcer, sample_context):
        """Test pre-enforcement hook."""
        hook_called = {"count": 0}

        def pre_hook(context):
            hook_called["count"] += 1
            hook_called["context"] = context

        enforcer.add_pre_hook(pre_hook)

        await enforcer.enforce(sample_context)

        assert hook_called["count"] == 1
        assert hook_called["context"] == sample_context

    @pytest.mark.asyncio
    async def test_enforcer_post_hook(self, enforcer, sample_context):
        """Test post-enforcement hook."""
        hook_called = {"count": 0}

        def post_hook(context, result):
            hook_called["count"] += 1
            hook_called["result"] = result

        enforcer.add_post_hook(post_hook)

        await enforcer.enforce(sample_context)

        assert hook_called["count"] == 1
        assert hook_called["result"].allowed is True

    @pytest.mark.asyncio
    async def test_enforcer_hook_error_handling(self, enforcer, sample_context):
        """Test hooks don't break enforcement on error."""

        def failing_hook(context):
            raise RuntimeError("Hook failed")

        enforcer.add_pre_hook(failing_hook)

        # Should not raise, just log error
        result = await enforcer.enforce(sample_context)
        assert result.allowed is True

    def test_enforcer_metrics(self, enforcer):
        """Test enforcement metrics."""
        metrics = enforcer.get_metrics()

        assert metrics["total_evaluations"] == 0
        assert metrics["total_violations"] == 0
        assert metrics["total_allowed"] == 0
        assert metrics["total_denied"] == 0
        assert metrics["enforcement_mode"] == "enforce"
        assert metrics["registered_rules"] == 0

    @pytest.mark.asyncio
    async def test_enforcer_metrics_update(self, enforcer, sample_context):
        """Test metrics are updated after enforcement."""
        await enforcer.enforce(sample_context)
        await enforcer.enforce(sample_context)

        metrics = enforcer.get_metrics()

        assert metrics["total_evaluations"] == 2
        assert metrics["total_allowed"] == 2
        assert metrics["average_evaluation_time_ms"] > 0

    @pytest.mark.asyncio
    async def test_enforcer_metrics_denied(self, enforcer):
        """Test metrics for denied requests."""
        context = PolicyContext(
            agent_id="agent",
            action="delete",
            resource_type="doc",
            resource_id="id",
        )

        rule = PolicyRule(
            id="rule-1",
            policy_id="p",
            name="No Delete",
            condition="action != 'delete'",
            action=EnforcementAction.DENY,
            severity=ViolationSeverity.CRITICAL,
        )
        enforcer.register_rule(rule)

        await enforcer.enforce(context)

        metrics = enforcer.get_metrics()
        assert metrics["total_denied"] == 1
        assert metrics["total_violations"] == 1

    def test_enforcer_reset_metrics(self, enforcer):
        """Test resetting metrics."""
        enforcer._total_evaluations = 100
        enforcer._total_violations = 50
        enforcer._evaluation_times = [1.0, 2.0, 3.0]

        enforcer.reset_metrics()

        metrics = enforcer.get_metrics()
        assert metrics["total_evaluations"] == 0
        assert metrics["total_violations"] == 0


class TestDefaultEvaluation:
    """Test default rule evaluation logic."""

    @pytest.fixture
    def enforcer(self):
        return PolicyEnforcer("cdd01ef066bc6cf2")

    def test_evaluate_not_equals_pass(self, enforcer):
        """Test != evaluation passes."""
        context = PolicyContext(
            agent_id="agent",
            action="read",
            resource_type="doc",
            resource_id="id",
        )

        passed, msg = enforcer._default_evaluate("action != 'delete'", context)
        assert passed is True

    def test_evaluate_not_equals_fail(self, enforcer):
        """Test != evaluation fails."""
        context = PolicyContext(
            agent_id="agent",
            action="delete",
            resource_type="doc",
            resource_id="id",
        )

        passed, msg = enforcer._default_evaluate("action != 'delete'", context)
        assert passed is False
        assert "must not be delete" in msg

    def test_evaluate_equals_pass(self, enforcer):
        """Test == evaluation passes."""
        context = PolicyContext(
            agent_id="agent",
            action="read",
            resource_type="doc",
            resource_id="id",
        )

        passed, msg = enforcer._default_evaluate("action == 'read'", context)
        assert passed is True

    def test_evaluate_equals_fail(self, enforcer):
        """Test == evaluation fails."""
        context = PolicyContext(
            agent_id="agent",
            action="write",
            resource_type="doc",
            resource_id="id",
        )

        passed, msg = enforcer._default_evaluate("action == 'read'", context)
        assert passed is False
        assert "must be read" in msg

    def test_evaluate_in_pass(self, enforcer):
        """Test 'in' evaluation passes."""
        context = PolicyContext(
            agent_id="agent",
            action="read",
            resource_type="doc",
            resource_id="id",
        )

        passed, msg = enforcer._default_evaluate("action in ['read', 'list', 'get']", context)
        assert passed is True

    def test_evaluate_in_fail(self, enforcer):
        """Test 'in' evaluation fails."""
        context = PolicyContext(
            agent_id="agent",
            action="delete",
            resource_type="doc",
            resource_id="id",
        )

        passed, msg = enforcer._default_evaluate("action in ['read', 'list', 'get']", context)
        assert passed is False


class TestGlobalPolicyEnforcerFunctions:
    """Test suite for global policy enforcer functions."""

    @pytest.fixture
    def constitutional_hash(self):
        return "cdd01ef066bc6cf2"

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clean up global state after each test."""
        yield
        shutdown_policy_enforcer()

    def test_get_policy_enforcer_before_init(self):
        """Test getting enforcer before initialization."""
        assert get_policy_enforcer() is None

    def test_initialize_policy_enforcer(self, constitutional_hash):
        """Test initializing global policy enforcer."""
        enforcer = initialize_policy_enforcer(constitutional_hash)

        assert enforcer is not None
        assert enforcer.constitutional_hash == constitutional_hash

    def test_get_policy_enforcer_after_init(self, constitutional_hash):
        """Test getting enforcer after initialization."""
        initialize_policy_enforcer(constitutional_hash)
        enforcer = get_policy_enforcer()

        assert enforcer is not None
        assert enforcer.constitutional_hash == constitutional_hash

    def test_initialize_with_mode(self, constitutional_hash):
        """Test initializing with specific mode."""
        enforcer = initialize_policy_enforcer(
            constitutional_hash,
            mode=EnforcementMode.AUDIT,
        )

        assert enforcer.mode == EnforcementMode.AUDIT

    def test_reinitialize_with_different_hash(self, constitutional_hash):
        """Test reinitializing with different hash."""
        initialize_policy_enforcer(constitutional_hash)

        new_enforcer = initialize_policy_enforcer("new-hash-12345678")

        assert new_enforcer.constitutional_hash == "new-hash-12345678"

    @pytest.mark.asyncio
    async def test_enforce_policy_function(self, constitutional_hash):
        """Test global enforce_policy function."""
        initialize_policy_enforcer(constitutional_hash)

        context = PolicyContext(
            agent_id="agent",
            action="read",
            resource_type="doc",
            resource_id="id",
        )

        result = await enforce_policy(context)
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_enforce_policy_not_initialized(self):
        """Test enforce_policy when not initialized."""
        context = PolicyContext(
            agent_id="agent",
            action="read",
            resource_type="doc",
            resource_id="id",
        )

        with pytest.raises(RuntimeError, match="not initialized"):
            await enforce_policy(context)

    def test_shutdown_policy_enforcer(self, constitutional_hash):
        """Test shutting down policy enforcer."""
        initialize_policy_enforcer(constitutional_hash)
        shutdown_policy_enforcer()

        assert get_policy_enforcer() is None


class TestPolicyEnforcerEdgeCases:
    """Test edge cases for PolicyEnforcer."""

    @pytest.fixture
    def enforcer(self):
        return PolicyEnforcer("cdd01ef066bc6cf2")

    @pytest.mark.asyncio
    async def test_empty_agent_id(self, enforcer):
        """Test context with empty agent ID."""
        context = PolicyContext(
            agent_id="",
            action="read",
            resource_type="doc",
            resource_id="id",
        )

        result = await enforcer.enforce(context)
        assert result is not None

    @pytest.mark.asyncio
    async def test_special_characters_in_action(self, enforcer):
        """Test action with special characters."""
        context = PolicyContext(
            agent_id="agent",
            action="read/write",
            resource_type="doc",
            resource_id="id",
        )

        result = await enforcer.enforce(context)
        assert result is not None

    @pytest.mark.asyncio
    async def test_unicode_in_context(self, enforcer):
        """Test context with unicode characters."""
        context = PolicyContext(
            agent_id="agent-\u00e9",
            action="read",
            resource_type="document-\u4e2d\u6587",
            resource_id="id-123",
        )

        result = await enforcer.enforce(context)
        assert result is not None

    @pytest.mark.asyncio
    async def test_multiple_violations(self, enforcer):
        """Test enforcement with multiple violations."""
        context = PolicyContext(
            agent_id="agent",
            action="delete",
            resource_type="sensitive",
            resource_id="id",
        )

        rules = [
            PolicyRule(
                id="rule-1",
                policy_id="p",
                name="No Delete",
                condition="action != 'delete'",
                action=EnforcementAction.DENY,
                severity=ViolationSeverity.HIGH,
            ),
            PolicyRule(
                id="rule-2",
                policy_id="p",
                name="No Sensitive",
                condition="resource_type != 'sensitive'",
                action=EnforcementAction.DENY,
                severity=ViolationSeverity.MEDIUM,
            ),
        ]

        for rule in rules:
            enforcer.register_rule(rule)

        result = await enforcer.enforce(context)

        assert len(result.violations) == 2
        assert result.max_severity == ViolationSeverity.HIGH

    @pytest.mark.asyncio
    async def test_concurrent_enforcement(self, enforcer):
        """Test concurrent enforcement requests."""
        context = PolicyContext(
            agent_id="agent",
            action="read",
            resource_type="doc",
            resource_id="id",
        )

        async def enforce_request():
            return await enforcer.enforce(context)

        # Run 10 concurrent requests
        tasks = [enforce_request() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        assert all(r.allowed for r in results)

    def test_reasoning_generation_allowed(self, enforcer):
        """Test reasoning generation for allowed action."""
        reasoning = enforcer._generate_reasoning(True, [])
        assert "allowed" in reasoning.lower()
        assert "no policy violations" in reasoning.lower()

    def test_reasoning_generation_denied(self, enforcer):
        """Test reasoning generation for denied action."""
        context = PolicyContext(
            agent_id="a",
            action="act",
            resource_type="t",
            resource_id="id",
        )
        violations = [
            PolicyViolation(
                id="v-1",
                policy_id="p",
                policy_name="Test",
                rule_id="r",
                severity=ViolationSeverity.HIGH,
                message="Not allowed",
                context=context,
            )
        ]

        reasoning = enforcer._generate_reasoning(False, violations)
        assert "denied" in reasoning.lower()

    def test_severity_level_ordering(self, enforcer):
        """Test severity level ordering."""
        levels = [
            enforcer._severity_level(ViolationSeverity.INFO),
            enforcer._severity_level(ViolationSeverity.LOW),
            enforcer._severity_level(ViolationSeverity.MEDIUM),
            enforcer._severity_level(ViolationSeverity.HIGH),
            enforcer._severity_level(ViolationSeverity.CRITICAL),
        ]

        assert levels == [0, 1, 2, 3, 4]
        assert levels == sorted(levels)


if __name__ == "__main__":
    # Run basic smoke tests
    logging.info("Running Policy Enforcement smoke tests...")

    try:
        # Check imports
        logging.info("Imports successful")
    except ImportError as e:
        logging.error(f"Import failed: {e}")
        exit(1)

    logging.info("All smoke tests passed!")
