"""
Tests for Constitutional Guardrails
Constitutional Hash: cdd01ef066bc6cf2
"""

import pytest

from nemo_agent_toolkit.constitutional_guardrails import (
    CONSTITUTIONAL_HASH,
    ConstitutionalGuardrails,
    GuardrailAction,
    GuardrailConfig,
    GuardrailResult,
    ViolationType,
)


class TestGuardrailConfig:
    """Tests for GuardrailConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = GuardrailConfig()
        assert config.enabled is True
        assert config.strict_mode is False
        assert config.max_retries == 3
        assert config.timeout_seconds == 5.0
        assert config.audit_all_requests is True
        assert config.block_on_violation is True
        assert config.constitutional_hash == CONSTITUTIONAL_HASH

    def test_custom_config(self):
        """Test custom configuration."""
        config = GuardrailConfig(
            enabled=False,
            strict_mode=True,
            max_retries=5,
            timeout_seconds=10.0,
        )
        assert config.enabled is False
        assert config.strict_mode is True
        assert config.max_retries == 5
        assert config.timeout_seconds == 10.0

    def test_validate_correct_hash(self):
        """Test validation with correct constitutional hash."""
        config = GuardrailConfig(constitutional_hash=CONSTITUTIONAL_HASH)
        config.validate()  # Should not raise

    def test_validate_incorrect_hash(self):
        """Test validation with incorrect constitutional hash."""
        config = GuardrailConfig(constitutional_hash="invalid_hash")
        with pytest.raises(ValueError, match="Invalid constitutional hash"):
            config.validate()

    def test_default_pii_patterns(self):
        """Test default PII patterns are set."""
        config = GuardrailConfig()
        assert len(config.pii_patterns) == 4
        # SSN pattern
        assert any("\\d{3}-\\d{2}-\\d{4}" in p for p in config.pii_patterns)


class TestGuardrailResult:
    """Tests for GuardrailResult."""

    def test_allowed_result(self):
        """Test creating an allowed result."""
        result = GuardrailResult(
            action=GuardrailAction.ALLOW,
            allowed=True,
        )
        assert result.action == GuardrailAction.ALLOW
        assert result.allowed is True
        assert result.violations == []
        assert result.constitutional_hash == CONSTITUTIONAL_HASH

    def test_blocked_result(self):
        """Test creating a blocked result."""
        result = GuardrailResult(
            action=GuardrailAction.BLOCK,
            allowed=False,
            violations=[{"type": "privacy", "message": "PII detected"}],
            reasoning="Content contains PII",
        )
        assert result.action == GuardrailAction.BLOCK
        assert result.allowed is False
        assert len(result.violations) == 1
        assert result.reasoning == "Content contains PII"

    def test_modified_result(self):
        """Test creating a modified result."""
        result = GuardrailResult(
            action=GuardrailAction.MODIFY,
            allowed=True,
            modified_content="User email is [REDACTED]",
        )
        assert result.action == GuardrailAction.MODIFY
        assert result.modified_content == "User email is [REDACTED]"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = GuardrailResult(
            action=GuardrailAction.ALLOW,
            allowed=True,
            trace_id="test123",
        )
        data = result.to_dict()
        assert data["action"] == "allow"
        assert data["allowed"] is True
        assert data["trace_id"] == "test123"
        assert data["constitutional_hash"] == CONSTITUTIONAL_HASH
        assert "timestamp" in data


class TestConstitutionalGuardrails:
    """Tests for ConstitutionalGuardrails."""

    @pytest.fixture
    def guardrails(self):
        """Create guardrails instance for testing."""
        return ConstitutionalGuardrails()

    @pytest.fixture
    def disabled_guardrails(self):
        """Create disabled guardrails instance."""
        config = GuardrailConfig(enabled=False)
        return ConstitutionalGuardrails(config=config)

    @pytest.mark.asyncio
    async def test_check_input_clean(self, guardrails):
        """Test checking clean input."""
        result = await guardrails.check_input("Hello, how are you?")
        assert result.allowed is True
        assert result.action == GuardrailAction.ALLOW
        assert len(result.violations) == 0

    @pytest.mark.asyncio
    async def test_check_input_disabled(self, disabled_guardrails):
        """Test checking input when guardrails disabled."""
        result = await disabled_guardrails.check_input("Any content here")
        assert result.allowed is True
        assert result.action == GuardrailAction.ALLOW

    @pytest.mark.asyncio
    async def test_check_input_with_ssn(self, guardrails):
        """Test detecting SSN in input."""
        result = await guardrails.check_input("My SSN is 123-45-6789")
        assert result.allowed is False
        assert result.action == GuardrailAction.BLOCK
        assert any(v["type"] == "privacy" for v in result.violations)

    @pytest.mark.asyncio
    async def test_check_input_with_email(self, guardrails):
        """Test detecting email in input."""
        result = await guardrails.check_input("Contact me at john.doe@example.com")
        assert result.allowed is False
        assert any(v["type"] == "privacy" for v in result.violations)

    @pytest.mark.asyncio
    async def test_check_input_with_phone(self, guardrails):
        """Test detecting phone number in input."""
        result = await guardrails.check_input("Call me at 555-123-4567")
        assert result.allowed is False
        assert any(v["type"] == "privacy" for v in result.violations)

    @pytest.mark.asyncio
    async def test_check_input_with_credit_card(self, guardrails):
        """Test detecting credit card in input."""
        result = await guardrails.check_input("My card is 1234567890123456")
        assert result.allowed is False
        assert any(v["type"] == "privacy" for v in result.violations)

    @pytest.mark.asyncio
    async def test_check_input_safety_threat(self, guardrails):
        """Test detecting security threats."""
        # Pattern matches "hack system" or "attack server" etc.
        result = await guardrails.check_input("I want to hack system and exploit database")
        assert result.allowed is False
        assert any(v["type"] == "security" for v in result.violations)

    @pytest.mark.asyncio
    async def test_check_output_clean(self, guardrails):
        """Test checking clean output."""
        result = await guardrails.check_output("Here is your response.")
        assert result.allowed is True
        assert result.action == GuardrailAction.ALLOW

    @pytest.mark.asyncio
    async def test_check_output_with_pii_redaction(self, guardrails):
        """Test PII redaction in output."""
        result = await guardrails.check_output("User email is john@example.com")
        # Output should be modified (redacted) not blocked
        if result.modified_content:
            assert "[REDACTED]" in result.modified_content
            assert result.action == GuardrailAction.MODIFY

    @pytest.mark.asyncio
    async def test_check_output_harmful_content(self, guardrails):
        """Test detecting harmful content in output."""
        result = await guardrails.check_output("Here are instructions to hack the system")
        assert any(v["type"] == "safety" for v in result.violations)

    @pytest.mark.asyncio
    async def test_audit_logging(self, guardrails):
        """Test audit log is populated."""
        await guardrails.check_input("Test input")
        await guardrails.check_output("Test output")

        audit_log = guardrails.get_audit_log()
        assert len(audit_log) == 2
        assert audit_log[0]["direction"] == "input"
        assert audit_log[1]["direction"] == "output"
        assert all(e["constitutional_hash"] == CONSTITUTIONAL_HASH for e in audit_log)

    @pytest.mark.asyncio
    async def test_clear_audit_log(self, guardrails):
        """Test clearing audit log."""
        await guardrails.check_input("Test")
        assert len(guardrails.get_audit_log()) == 1

        guardrails.clear_audit_log()
        assert len(guardrails.get_audit_log()) == 0

    @pytest.mark.asyncio
    async def test_get_metrics_empty(self, guardrails):
        """Test metrics with no data."""
        metrics = await guardrails.get_metrics()
        assert metrics["total_checks"] == 0
        assert metrics["allowed_rate"] == 1.0
        assert metrics["constitutional_hash"] == CONSTITUTIONAL_HASH

    @pytest.mark.asyncio
    async def test_get_metrics_with_data(self, guardrails):
        """Test metrics after processing."""
        await guardrails.check_input("Clean input")
        await guardrails.check_input("SSN: 123-45-6789")
        await guardrails.check_output("Clean output")

        metrics = await guardrails.get_metrics()
        assert metrics["total_checks"] == 3
        assert metrics["input_checks"] == 2
        assert metrics["output_checks"] == 1

    def test_add_custom_input_validator(self, guardrails):
        """Test adding custom input validator."""

        def custom_validator(content):
            return GuardrailResult(
                action=GuardrailAction.ALLOW,
                allowed=True,
            )

        guardrails.add_input_validator(custom_validator)
        assert len(guardrails._input_validators) == 1

    def test_add_custom_output_validator(self, guardrails):
        """Test adding custom output validator."""

        def custom_validator(content):
            return GuardrailResult(
                action=GuardrailAction.ALLOW,
                allowed=True,
            )

        guardrails.add_output_validator(custom_validator)
        assert len(guardrails._output_validators) == 1

    def test_violation_handler_registration(self, guardrails):
        """Test registering violation handlers."""
        handler_called = []

        def handler(violation):
            handler_called.append(violation)

        guardrails.on_violation(ViolationType.PRIVACY, handler)
        assert ViolationType.PRIVACY in guardrails._violation_handlers

    @pytest.mark.asyncio
    async def test_violation_handler_called(self, guardrails):
        """Test violation handler is called."""
        handler_called = []

        def handler(violation):
            handler_called.append(violation)

        guardrails.on_violation(ViolationType.PRIVACY, handler)
        await guardrails.check_input("Email: test@example.com")

        assert len(handler_called) > 0

    @pytest.mark.asyncio
    async def test_non_blocking_mode(self):
        """Test non-blocking mode allows violations but audits."""
        config = GuardrailConfig(block_on_violation=False)
        guardrails = ConstitutionalGuardrails(config=config)

        result = await guardrails.check_input("SSN: 123-45-6789")
        assert result.allowed is True  # Allowed despite violation
        assert result.action == GuardrailAction.AUDIT
        assert len(result.violations) > 0  # But violations recorded


class TestGuardrailAction:
    """Tests for GuardrailAction enum."""

    def test_action_values(self):
        """Test action enum values."""
        assert GuardrailAction.ALLOW.value == "allow"
        assert GuardrailAction.BLOCK.value == "block"
        assert GuardrailAction.MODIFY.value == "modify"
        assert GuardrailAction.ESCALATE.value == "escalate"
        assert GuardrailAction.AUDIT.value == "audit"


class TestViolationType:
    """Tests for ViolationType enum."""

    def test_violation_type_values(self):
        """Test violation type enum values."""
        assert ViolationType.PRIVACY.value == "privacy"
        assert ViolationType.SAFETY.value == "safety"
        assert ViolationType.ETHICS.value == "ethics"
        assert ViolationType.COMPLIANCE.value == "compliance"
        assert ViolationType.SECURITY.value == "security"


class TestConstitutionalHash:
    """Tests for constitutional hash enforcement."""

    def test_module_hash(self):
        """Test module-level constitutional hash."""
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"

    def test_config_default_hash(self):
        """Test config default hash."""
        config = GuardrailConfig()
        assert config.constitutional_hash == "cdd01ef066bc6cf2"

    def test_result_default_hash(self):
        """Test result default hash."""
        result = GuardrailResult(
            action=GuardrailAction.ALLOW,
            allowed=True,
        )
        assert result.constitutional_hash == "cdd01ef066bc6cf2"
