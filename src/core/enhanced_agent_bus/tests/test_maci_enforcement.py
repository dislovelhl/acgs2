"""
ACGS-2 MACI Enforcement Tests
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive tests for MACI role separation enforcement including:
- Role registration and management
- Action permission validation
- Self-validation prevention (Gödel bypass)
- Cross-role validation constraints
- Validation strategy integration
"""

import pytest

try:
    from src.core.shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

from src.core.enhanced_agent_bus.exceptions import (
    MACICrossRoleValidationError,
    MACIRoleNotAssignedError,
    MACIRoleViolationError,
    MACISelfValidationError,
)
from src.core.enhanced_agent_bus.maci_enforcement import (
    ROLE_PERMISSIONS,
    VALIDATION_CONSTRAINTS,
    MACIAction,
    MACIAgentRecord,
    MACIEnforcer,
    MACIRole,
    MACIRoleRegistry,
    MACIValidationContext,
    MACIValidationResult,
    MACIValidationStrategy,
    create_maci_enforcement_middleware,
)
from src.core.enhanced_agent_bus.models import AgentMessage, MessageType

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def maci_registry():
    """Create a fresh MACI role registry."""
    return MACIRoleRegistry()


@pytest.fixture
def maci_enforcer(maci_registry):
    """Create a MACI enforcer with registry."""
    return MACIEnforcer(registry=maci_registry, strict_mode=True)


@pytest.fixture
def maci_enforcer_non_strict(maci_registry):
    """Create a non-strict MACI enforcer."""
    return MACIEnforcer(registry=maci_registry, strict_mode=False)


@pytest.fixture
def maci_strategy(maci_enforcer):
    """Create a MACI validation strategy."""
    return MACIValidationStrategy(enforcer=maci_enforcer)


@pytest.fixture
def sample_message():
    """Create a sample agent message."""
    return AgentMessage(
        message_id="msg-001",
        source_agent_id="agent-exec-1",
        target_agent_id="agent-judicial-1",
        message_type=MessageType.GOVERNANCE_REQUEST,
        content="Test governance request",
        constitutional_hash=CONSTITUTIONAL_HASH,
    )


# =============================================================================
# MACIAgentRecord Tests
# =============================================================================


class TestMACIAgentRecord:
    """Tests for MACIAgentRecord dataclass."""

    def test_create_record(self):
        """Test creating an agent record."""
        record = MACIAgentRecord(
            agent_id="agent-1",
            role=MACIRole.EXECUTIVE,
        )
        assert record.agent_id == "agent-1"
        assert record.role == MACIRole.EXECUTIVE
        assert record.outputs == []
        assert record.constitutional_hash == CONSTITUTIONAL_HASH

    def test_add_output(self):
        """Test adding outputs to a record."""
        record = MACIAgentRecord(agent_id="agent-1", role=MACIRole.EXECUTIVE)
        record.add_output("output-1")
        record.add_output("output-2")
        assert "output-1" in record.outputs
        assert "output-2" in record.outputs
        assert len(record.outputs) == 2

    def test_owns_output(self):
        """Test checking output ownership."""
        record = MACIAgentRecord(agent_id="agent-1", role=MACIRole.EXECUTIVE)
        record.add_output("output-1")
        assert record.owns_output("output-1") is True
        assert record.owns_output("output-2") is False

    def test_can_perform_executive(self):
        """Test Executive role permissions."""
        record = MACIAgentRecord(agent_id="agent-1", role=MACIRole.EXECUTIVE)
        assert record.can_perform(MACIAction.PROPOSE) is True
        assert record.can_perform(MACIAction.SYNTHESIZE) is True
        assert record.can_perform(MACIAction.QUERY) is True
        assert record.can_perform(MACIAction.VALIDATE) is False
        assert record.can_perform(MACIAction.EXTRACT_RULES) is False

    def test_can_perform_legislative(self):
        """Test Legislative role permissions."""
        record = MACIAgentRecord(agent_id="agent-1", role=MACIRole.LEGISLATIVE)
        assert record.can_perform(MACIAction.EXTRACT_RULES) is True
        assert record.can_perform(MACIAction.SYNTHESIZE) is True
        assert record.can_perform(MACIAction.QUERY) is True
        assert record.can_perform(MACIAction.PROPOSE) is False
        assert record.can_perform(MACIAction.VALIDATE) is False

    def test_can_perform_judicial(self):
        """Test Judicial role permissions."""
        record = MACIAgentRecord(agent_id="agent-1", role=MACIRole.JUDICIAL)
        assert record.can_perform(MACIAction.VALIDATE) is True
        assert record.can_perform(MACIAction.AUDIT) is True
        assert record.can_perform(MACIAction.QUERY) is True
        assert record.can_perform(MACIAction.PROPOSE) is False
        assert record.can_perform(MACIAction.EXTRACT_RULES) is False

    def test_can_validate_role(self):
        """Test cross-role validation permissions."""
        judicial = MACIAgentRecord(agent_id="j1", role=MACIRole.JUDICIAL)
        assert judicial.can_validate_role(MACIRole.EXECUTIVE) is True
        assert judicial.can_validate_role(MACIRole.LEGISLATIVE) is True
        assert judicial.can_validate_role(MACIRole.JUDICIAL) is False

        executive = MACIAgentRecord(agent_id="e1", role=MACIRole.EXECUTIVE)
        assert executive.can_validate_role(MACIRole.EXECUTIVE) is False
        assert executive.can_validate_role(MACIRole.LEGISLATIVE) is False


# =============================================================================
# MACIRoleRegistry Tests
# =============================================================================


class TestMACIRoleRegistry:
    """Tests for MACIRoleRegistry."""

    @pytest.mark.asyncio
    async def test_register_agent(self, maci_registry):
        """Test registering an agent."""
        record = await maci_registry.register_agent(
            agent_id="agent-1",
            role=MACIRole.EXECUTIVE,
            metadata={"team": "alpha"},
        )
        assert record.agent_id == "agent-1"
        assert record.role == MACIRole.EXECUTIVE
        assert record.metadata["team"] == "alpha"

    @pytest.mark.asyncio
    async def test_get_agent(self, maci_registry):
        """Test retrieving a registered agent."""
        await maci_registry.register_agent("agent-1", MACIRole.EXECUTIVE)
        record = await maci_registry.get_agent("agent-1")
        assert record is not None
        assert record.agent_id == "agent-1"

    @pytest.mark.asyncio
    async def test_get_nonexistent_agent(self, maci_registry):
        """Test retrieving a non-existent agent."""
        record = await maci_registry.get_agent("nonexistent")
        assert record is None

    @pytest.mark.asyncio
    async def test_unregister_agent(self, maci_registry):
        """Test unregistering an agent."""
        await maci_registry.register_agent("agent-1", MACIRole.EXECUTIVE)
        record = await maci_registry.unregister_agent("agent-1")
        assert record is not None
        assert await maci_registry.get_agent("agent-1") is None

    @pytest.mark.asyncio
    async def test_record_output(self, maci_registry):
        """Test recording agent outputs."""
        await maci_registry.register_agent("agent-1", MACIRole.EXECUTIVE)
        await maci_registry.record_output("agent-1", "output-1")

        record = await maci_registry.get_agent("agent-1")
        assert "output-1" in record.outputs

    @pytest.mark.asyncio
    async def test_get_output_producer(self, maci_registry):
        """Test finding the producer of an output."""
        await maci_registry.register_agent("agent-1", MACIRole.EXECUTIVE)
        await maci_registry.record_output("agent-1", "output-1")

        producer = await maci_registry.get_output_producer("output-1")
        assert producer == "agent-1"

    @pytest.mark.asyncio
    async def test_get_agents_by_role(self, maci_registry):
        """Test retrieving agents by role."""
        await maci_registry.register_agent("exec-1", MACIRole.EXECUTIVE)
        await maci_registry.register_agent("exec-2", MACIRole.EXECUTIVE)
        await maci_registry.register_agent("judicial-1", MACIRole.JUDICIAL)

        executives = await maci_registry.get_agents_by_role(MACIRole.EXECUTIVE)
        assert len(executives) == 2

        judicials = await maci_registry.get_agents_by_role(MACIRole.JUDICIAL)
        assert len(judicials) == 1

    @pytest.mark.asyncio
    async def test_is_self_output(self, maci_registry):
        """Test self-output checking."""
        await maci_registry.register_agent("agent-1", MACIRole.EXECUTIVE)
        await maci_registry.record_output("agent-1", "output-1")

        assert await maci_registry.is_self_output("agent-1", "output-1") is True
        assert await maci_registry.is_self_output("agent-1", "output-2") is False
        assert await maci_registry.is_self_output("agent-2", "output-1") is False


# =============================================================================
# MACIEnforcer Tests - Role Permissions
# =============================================================================


class TestMACIEnforcerRolePermissions:
    """Tests for MACI role permission enforcement."""

    @pytest.mark.asyncio
    async def test_executive_can_propose(self, maci_enforcer, maci_registry):
        """Test Executive can perform PROPOSE action."""
        await maci_registry.register_agent("exec-1", MACIRole.EXECUTIVE)
        result = await maci_enforcer.validate_action(
            agent_id="exec-1",
            action=MACIAction.PROPOSE,
        )
        assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_executive_cannot_validate(self, maci_enforcer, maci_registry):
        """Test Executive cannot perform VALIDATE action."""
        await maci_registry.register_agent("exec-1", MACIRole.EXECUTIVE)
        with pytest.raises(MACIRoleViolationError) as exc_info:
            await maci_enforcer.validate_action(
                agent_id="exec-1",
                action=MACIAction.VALIDATE,
            )
        assert exc_info.value.role == "executive"
        assert exc_info.value.action == "validate"

    @pytest.mark.asyncio
    async def test_legislative_can_extract_rules(self, maci_enforcer, maci_registry):
        """Test Legislative can perform EXTRACT_RULES action."""
        await maci_registry.register_agent("leg-1", MACIRole.LEGISLATIVE)
        result = await maci_enforcer.validate_action(
            agent_id="leg-1",
            action=MACIAction.EXTRACT_RULES,
        )
        assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_legislative_cannot_propose(self, maci_enforcer, maci_registry):
        """Test Legislative cannot perform PROPOSE action."""
        await maci_registry.register_agent("leg-1", MACIRole.LEGISLATIVE)
        with pytest.raises(MACIRoleViolationError) as exc_info:
            await maci_enforcer.validate_action(
                agent_id="leg-1",
                action=MACIAction.PROPOSE,
            )
        assert exc_info.value.role == "legislative"

    @pytest.mark.asyncio
    async def test_judicial_can_validate(self, maci_enforcer, maci_registry):
        """Test Judicial can perform VALIDATE action."""
        await maci_registry.register_agent("jud-1", MACIRole.JUDICIAL)
        await maci_registry.register_agent("exec-1", MACIRole.EXECUTIVE)
        await maci_registry.record_output("exec-1", "output-1")

        result = await maci_enforcer.validate_action(
            agent_id="jud-1",
            action=MACIAction.VALIDATE,
            target_output_id="output-1",
        )
        assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_judicial_cannot_propose(self, maci_enforcer, maci_registry):
        """Test Judicial cannot perform PROPOSE action."""
        await maci_registry.register_agent("jud-1", MACIRole.JUDICIAL)
        with pytest.raises(MACIRoleViolationError) as exc_info:
            await maci_enforcer.validate_action(
                agent_id="jud-1",
                action=MACIAction.PROPOSE,
            )
        assert exc_info.value.role == "judicial"

    @pytest.mark.asyncio
    async def test_all_roles_can_query(self, maci_enforcer, maci_registry):
        """Test all roles can perform QUERY action."""
        await maci_registry.register_agent("exec-1", MACIRole.EXECUTIVE)
        await maci_registry.register_agent("leg-1", MACIRole.LEGISLATIVE)
        await maci_registry.register_agent("jud-1", MACIRole.JUDICIAL)

        for agent_id in ["exec-1", "leg-1", "jud-1"]:
            result = await maci_enforcer.validate_action(
                agent_id=agent_id,
                action=MACIAction.QUERY,
            )
            assert result.is_valid is True


# =============================================================================
# MACIEnforcer Tests - Self-Validation Prevention (Gödel Bypass)
# =============================================================================


class TestMACIEnforcerSelfValidation:
    """Tests for Gödel bypass prevention (self-validation)."""

    @pytest.mark.asyncio
    async def test_judicial_cannot_validate_own_output(self, maci_enforcer, maci_registry):
        """Test Judicial cannot validate its own output."""
        await maci_registry.register_agent("jud-1", MACIRole.JUDICIAL)
        await maci_registry.record_output("jud-1", "jud-output-1")

        with pytest.raises(MACISelfValidationError) as exc_info:
            await maci_enforcer.validate_action(
                agent_id="jud-1",
                action=MACIAction.VALIDATE,
                target_output_id="jud-output-1",
            )
        assert exc_info.value.agent_id == "jud-1"
        assert exc_info.value.output_id == "jud-output-1"

    @pytest.mark.asyncio
    async def test_judicial_can_validate_other_agent_output(self, maci_enforcer, maci_registry):
        """Test Judicial can validate another agent's output."""
        await maci_registry.register_agent("jud-1", MACIRole.JUDICIAL)
        await maci_registry.register_agent("exec-1", MACIRole.EXECUTIVE)
        await maci_registry.record_output("exec-1", "exec-output-1")

        result = await maci_enforcer.validate_action(
            agent_id="jud-1",
            action=MACIAction.VALIDATE,
            target_output_id="exec-output-1",
        )
        assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_self_validation_detected_via_registry(self, maci_enforcer, maci_registry):
        """Test self-validation is detected even without local tracking."""
        await maci_registry.register_agent("jud-1", MACIRole.JUDICIAL)
        # Record output directly to registry
        await maci_registry.record_output("jud-1", "jud-output-2")

        with pytest.raises(MACISelfValidationError):
            await maci_enforcer.validate_action(
                agent_id="jud-1",
                action=MACIAction.VALIDATE,
                target_output_id="jud-output-2",
            )


# =============================================================================
# MACIEnforcer Tests - Cross-Role Validation
# =============================================================================


class TestMACIEnforcerCrossRoleValidation:
    """Tests for cross-role validation constraints."""

    @pytest.mark.asyncio
    async def test_judicial_cannot_validate_judicial_output(self, maci_enforcer, maci_registry):
        """Test Judicial cannot validate another Judicial's output."""
        await maci_registry.register_agent("jud-1", MACIRole.JUDICIAL)
        await maci_registry.register_agent("jud-2", MACIRole.JUDICIAL)
        await maci_registry.record_output("jud-2", "jud2-output-1")

        with pytest.raises(MACICrossRoleValidationError) as exc_info:
            await maci_enforcer.validate_action(
                agent_id="jud-1",
                action=MACIAction.VALIDATE,
                target_output_id="jud2-output-1",
            )
        assert exc_info.value.validator_role == "judicial"
        assert exc_info.value.target_role == "judicial"

    @pytest.mark.asyncio
    async def test_judicial_can_validate_executive_output(self, maci_enforcer, maci_registry):
        """Test Judicial can validate Executive's output."""
        await maci_registry.register_agent("jud-1", MACIRole.JUDICIAL)
        await maci_registry.register_agent("exec-1", MACIRole.EXECUTIVE)
        await maci_registry.record_output("exec-1", "exec-output-1")

        result = await maci_enforcer.validate_action(
            agent_id="jud-1",
            action=MACIAction.VALIDATE,
            target_output_id="exec-output-1",
        )
        assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_judicial_can_validate_legislative_output(self, maci_enforcer, maci_registry):
        """Test Judicial can validate Legislative's output."""
        await maci_registry.register_agent("jud-1", MACIRole.JUDICIAL)
        await maci_registry.register_agent("leg-1", MACIRole.LEGISLATIVE)
        await maci_registry.record_output("leg-1", "leg-output-1")

        result = await maci_enforcer.validate_action(
            agent_id="jud-1",
            action=MACIAction.VALIDATE,
            target_output_id="leg-output-1",
        )
        assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_cross_role_validation_with_target_agent_id(self, maci_enforcer, maci_registry):
        """Test cross-role validation using target_agent_id."""
        await maci_registry.register_agent("jud-1", MACIRole.JUDICIAL)
        await maci_registry.register_agent("jud-2", MACIRole.JUDICIAL)

        with pytest.raises(MACICrossRoleValidationError):
            await maci_enforcer.validate_action(
                agent_id="jud-1",
                action=MACIAction.VALIDATE,
                target_agent_id="jud-2",
            )


# =============================================================================
# MACIEnforcer Tests - Unregistered Agents
# =============================================================================


class TestMACIEnforcerUnregisteredAgents:
    """Tests for handling unregistered agents."""

    @pytest.mark.asyncio
    async def test_strict_mode_rejects_unregistered(self, maci_enforcer):
        """Test strict mode rejects unregistered agents."""
        with pytest.raises(MACIRoleNotAssignedError) as exc_info:
            await maci_enforcer.validate_action(
                agent_id="unknown-agent",
                action=MACIAction.PROPOSE,
            )
        assert exc_info.value.agent_id == "unknown-agent"

    @pytest.mark.asyncio
    async def test_non_strict_mode_allows_unregistered(self, maci_enforcer_non_strict):
        """Test non-strict mode allows unregistered agents."""
        result = await maci_enforcer_non_strict.validate_action(
            agent_id="unknown-agent",
            action=MACIAction.PROPOSE,
        )
        assert result.is_valid is True


# =============================================================================
# MACIValidationStrategy Tests
# =============================================================================


class TestMACIValidationStrategy:
    """Tests for MACI validation strategy."""

    @pytest.mark.asyncio
    async def test_validate_governance_request_from_executive(self, maci_strategy, maci_registry):
        """Test validating GOVERNANCE_REQUEST from Executive."""
        await maci_registry.register_agent("exec-1", MACIRole.EXECUTIVE)

        message = AgentMessage(
            message_id="msg-001",
            from_agent="exec-1",
            to_agent="jud-1",
            message_type=MessageType.GOVERNANCE_REQUEST,
            content={"action": "Test proposal"},
            constitutional_hash=CONSTITUTIONAL_HASH,
        )

        is_valid, error = await maci_strategy.validate(message)
        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_governance_request_from_judicial_fails(
        self, maci_strategy, maci_registry
    ):
        """Test GOVERNANCE_REQUEST from Judicial fails."""
        await maci_registry.register_agent("jud-1", MACIRole.JUDICIAL)

        message = AgentMessage(
            message_id="msg-001",
            from_agent="jud-1",
            to_agent="exec-1",
            message_type=MessageType.GOVERNANCE_REQUEST,
            content={"action": "Invalid proposal from judicial"},
            constitutional_hash=CONSTITUTIONAL_HASH,
        )

        is_valid, error = await maci_strategy.validate(message)
        assert is_valid is False
        assert "judicial" in error.lower()

    @pytest.mark.asyncio
    async def test_validate_validation_request_from_judicial(self, maci_strategy, maci_registry):
        """Test VALIDATION_REQUEST from Judicial."""
        await maci_registry.register_agent("jud-1", MACIRole.JUDICIAL)
        await maci_registry.register_agent("exec-1", MACIRole.EXECUTIVE)

        message = AgentMessage(
            message_id="msg-001",
            from_agent="jud-1",
            to_agent="exec-1",
            message_type=MessageType.CONSTITUTIONAL_VALIDATION,
            content={"action": "Validate this"},
            constitutional_hash=CONSTITUTIONAL_HASH,
        )

        is_valid, error = await maci_strategy.validate(message)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_query_from_any_role(self, maci_strategy, maci_registry):
        """Test QUERY messages from any role."""
        for role in MACIRole:
            agent_id = f"{role.value}-1"
            await maci_registry.register_agent(agent_id, role)

            message = AgentMessage(
                message_id=f"msg-{role.value}",
                from_agent=agent_id,
                to_agent="target",
                message_type=MessageType.QUERY,
                content={"action": "Query"},
                constitutional_hash=CONSTITUTIONAL_HASH,
            )

            is_valid, error = await maci_strategy.validate(message)
            assert is_valid is True, f"Role {role.value} should be able to query"


# =============================================================================
# Validation Log Tests
# =============================================================================


class TestMACIValidationLog:
    """Tests for validation logging."""

    @pytest.mark.asyncio
    async def test_successful_validations_logged(self, maci_enforcer, maci_registry):
        """Test successful validations are logged."""
        await maci_registry.register_agent("exec-1", MACIRole.EXECUTIVE)

        await maci_enforcer.validate_action("exec-1", MACIAction.PROPOSE)
        await maci_enforcer.validate_action("exec-1", MACIAction.QUERY)

        log = maci_enforcer.get_validation_log()
        assert len(log) == 2
        assert all(r.is_valid for r in log)

    @pytest.mark.asyncio
    async def test_failed_validations_logged(self, maci_enforcer, maci_registry):
        """Test failed validations are logged."""
        await maci_registry.register_agent("exec-1", MACIRole.EXECUTIVE)

        try:
            await maci_enforcer.validate_action("exec-1", MACIAction.VALIDATE)
        except MACIRoleViolationError:
            pass

        log = maci_enforcer.get_validation_log()
        assert len(log) == 1
        assert log[0].is_valid is False
        assert log[0].violation_type == "role_violation"

    @pytest.mark.asyncio
    async def test_clear_validation_log(self, maci_enforcer, maci_registry):
        """Test clearing the validation log."""
        await maci_registry.register_agent("exec-1", MACIRole.EXECUTIVE)
        await maci_enforcer.validate_action("exec-1", MACIAction.PROPOSE)

        assert len(maci_enforcer.get_validation_log()) == 1

        maci_enforcer.clear_validation_log()
        assert len(maci_enforcer.get_validation_log()) == 0


# =============================================================================
# Exception Tests
# =============================================================================


class TestMACIExceptions:
    """Tests for MACI exception behavior."""

    def test_role_violation_error_details(self):
        """Test MACIRoleViolationError contains proper details."""
        exc = MACIRoleViolationError(
            agent_id="agent-1",
            role="executive",
            action="validate",
            allowed_roles=["judicial"],
        )
        details = exc.to_dict()
        assert details["details"]["agent_id"] == "agent-1"
        assert details["details"]["role"] == "executive"
        assert details["details"]["action"] == "validate"
        assert "judicial" in details["details"]["allowed_roles"]

    def test_self_validation_error_details(self):
        """Test MACISelfValidationError contains proper details."""
        exc = MACISelfValidationError(
            agent_id="agent-1",
            action="validate",
            output_id="output-1",
        )
        details = exc.to_dict()
        assert details["details"]["prevention_type"] == "godel_bypass"
        assert "Gödel bypass" in str(exc)

    def test_cross_role_validation_error_details(self):
        """Test MACICrossRoleValidationError contains proper details."""
        exc = MACICrossRoleValidationError(
            validator_agent="jud-1",
            validator_role="judicial",
            target_agent="jud-2",
            target_role="judicial",
            reason="Cannot validate judicial outputs",
        )
        details = exc.to_dict()
        assert details["details"]["validator_agent"] == "jud-1"
        assert details["details"]["target_role"] == "judicial"


# =============================================================================
# Role Permissions Constant Tests
# =============================================================================


class TestRolePermissionsConstants:
    """Tests for role permission constants."""

    def test_executive_permissions(self):
        """Test Executive role permission constants."""
        perms = ROLE_PERMISSIONS[MACIRole.EXECUTIVE]
        assert MACIAction.PROPOSE in perms
        assert MACIAction.SYNTHESIZE in perms
        assert MACIAction.QUERY in perms
        assert MACIAction.VALIDATE not in perms

    def test_legislative_permissions(self):
        """Test Legislative role permission constants."""
        perms = ROLE_PERMISSIONS[MACIRole.LEGISLATIVE]
        assert MACIAction.EXTRACT_RULES in perms
        assert MACIAction.SYNTHESIZE in perms
        assert MACIAction.QUERY in perms
        assert MACIAction.PROPOSE not in perms

    def test_judicial_permissions(self):
        """Test Judicial role permission constants."""
        perms = ROLE_PERMISSIONS[MACIRole.JUDICIAL]
        assert MACIAction.VALIDATE in perms
        assert MACIAction.AUDIT in perms
        assert MACIAction.QUERY in perms
        assert MACIAction.PROPOSE not in perms

    def test_validation_constraints(self):
        """Test validation constraint constants."""
        judicial_can_validate = VALIDATION_CONSTRAINTS[MACIRole.JUDICIAL]
        assert MACIRole.EXECUTIVE in judicial_can_validate
        assert MACIRole.LEGISLATIVE in judicial_can_validate
        assert MACIRole.JUDICIAL not in judicial_can_validate


# =============================================================================
# Constitutional Hash Tests
# =============================================================================


class TestMACIConstitutionalHash:
    """Tests for constitutional hash enforcement."""

    def test_agent_record_has_hash(self):
        """Test agent records include constitutional hash."""
        record = MACIAgentRecord(agent_id="a1", role=MACIRole.EXECUTIVE)
        assert record.constitutional_hash == CONSTITUTIONAL_HASH

    def test_validation_result_has_hash(self):
        """Test validation results include constitutional hash."""
        context = MACIValidationContext(
            source_agent_id="a1",
            action=MACIAction.PROPOSE,
        )
        result = MACIValidationResult(
            is_valid=True,
            context=context,
        )
        assert result.constitutional_hash == CONSTITUTIONAL_HASH

    def test_registry_has_hash(self):
        """Test registry includes constitutional hash."""
        registry = MACIRoleRegistry()
        assert registry.constitutional_hash == CONSTITUTIONAL_HASH

    def test_enforcer_has_hash(self):
        """Test enforcer includes constitutional hash."""
        enforcer = MACIEnforcer()
        assert enforcer.constitutional_hash == CONSTITUTIONAL_HASH

    def test_strategy_has_hash(self):
        """Test validation strategy includes constitutional hash."""
        strategy = MACIValidationStrategy()
        assert strategy.constitutional_hash == CONSTITUTIONAL_HASH


# =============================================================================
# Middleware Factory Tests
# =============================================================================


class TestMACIMiddlewareFactory:
    """Tests for MACI enforcement middleware factory."""

    @pytest.mark.asyncio
    async def test_create_middleware_with_custom_enforcer(self, maci_enforcer, maci_registry):
        """Test creating middleware with custom enforcer."""
        middleware = create_maci_enforcement_middleware(enforcer=maci_enforcer)
        assert middleware is not None
        assert callable(middleware)

    @pytest.mark.asyncio
    async def test_create_middleware_default_enforcer(self):
        """Test creating middleware with default enforcer."""
        middleware = create_maci_enforcement_middleware()
        assert middleware is not None
        assert callable(middleware)

    @pytest.mark.asyncio
    async def test_middleware_passes_valid_message(self, maci_enforcer, maci_registry):
        """Test middleware passes valid messages to next handler."""
        await maci_registry.register_agent("exec-1", MACIRole.EXECUTIVE)

        middleware = create_maci_enforcement_middleware(enforcer=maci_enforcer)

        message = AgentMessage(
            message_id="msg-001",
            from_agent="exec-1",
            to_agent="target",
            message_type=MessageType.GOVERNANCE_REQUEST,
            content={"action": "Test"},
            constitutional_hash=CONSTITUTIONAL_HASH,
        )

        handler_called = False
        result_message = None

        async def next_handler(msg):
            nonlocal handler_called, result_message
            handler_called = True
            result_message = msg
            return "success"

        result = await middleware(message, next_handler)
        assert handler_called is True
        assert result_message is message
        assert result == "success"

    @pytest.mark.asyncio
    async def test_middleware_blocks_invalid_message(self, maci_enforcer, maci_registry):
        """Test middleware blocks messages from unregistered agents in strict mode."""
        # Don't register the agent
        middleware = create_maci_enforcement_middleware(enforcer=maci_enforcer)

        message = AgentMessage(
            message_id="msg-001",
            from_agent="unregistered-agent",
            to_agent="target",
            message_type=MessageType.GOVERNANCE_REQUEST,
            content={"action": "Test"},
            constitutional_hash=CONSTITUTIONAL_HASH,
        )

        handler_called = False

        async def next_handler(msg):
            nonlocal handler_called
            handler_called = True
            return "success"

        with pytest.raises(MACIRoleViolationError):
            await middleware(message, next_handler)

        assert handler_called is False

    @pytest.mark.asyncio
    async def test_middleware_blocks_role_violation(self, maci_enforcer, maci_registry):
        """Test middleware blocks messages that violate role permissions."""
        # Register as Executive, attempt to send validation message
        await maci_registry.register_agent("exec-1", MACIRole.EXECUTIVE)

        middleware = create_maci_enforcement_middleware(enforcer=maci_enforcer)

        message = AgentMessage(
            message_id="msg-001",
            from_agent="exec-1",
            to_agent="target",
            message_type=MessageType.CONSTITUTIONAL_VALIDATION,  # Exec can't validate
            content={"action": "Validate"},
            constitutional_hash=CONSTITUTIONAL_HASH,
        )

        handler_called = False

        async def next_handler(msg):
            nonlocal handler_called
            handler_called = True
            return "success"

        with pytest.raises(MACIRoleViolationError):
            await middleware(message, next_handler)

        assert handler_called is False


# =============================================================================
# Fail-Closed Target Agent Tests
# =============================================================================


class TestFailClosedTargetAgent:
    """Tests for fail-closed behavior on missing target agent."""

    @pytest.mark.asyncio
    async def test_validation_fails_on_missing_target_agent(self, maci_enforcer, maci_registry):
        """Test validation fails when target agent not registered."""
        # Register judicial agent
        await maci_registry.register_agent("jud-1", MACIRole.JUDICIAL)

        # Attempt to validate against unregistered target
        with pytest.raises(MACIRoleNotAssignedError) as exc_info:
            await maci_enforcer.validate_action(
                agent_id="jud-1",
                action=MACIAction.VALIDATE,
                target_agent_id="nonexistent-agent",
            )

        assert "nonexistent-agent" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validation_passes_with_registered_target(self, maci_enforcer, maci_registry):
        """Test validation passes when target agent is registered."""
        await maci_registry.register_agent("jud-1", MACIRole.JUDICIAL)
        await maci_registry.register_agent("exec-1", MACIRole.EXECUTIVE)

        result = await maci_enforcer.validate_action(
            agent_id="jud-1",
            action=MACIAction.VALIDATE,
            target_agent_id="exec-1",
        )

        assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_validation_log_records_target_not_found(self, maci_enforcer, maci_registry):
        """Test validation log records target_not_found violations."""
        await maci_registry.register_agent("jud-1", MACIRole.JUDICIAL)

        try:
            await maci_enforcer.validate_action(
                agent_id="jud-1",
                action=MACIAction.VALIDATE,
                target_agent_id="missing-target",
            )
        except MACIRoleNotAssignedError:
            pass

        log = maci_enforcer.get_validation_log()
        assert len(log) == 1
        assert log[0].violation_type == "target_not_found"
        assert "missing-target" in log[0].error_message


# =============================================================================
# Read Lock Concurrency Tests
# =============================================================================


class TestReadLockConcurrency:
    """Tests for thread-safety with read locks."""

    @pytest.mark.asyncio
    async def test_concurrent_register_and_get(self, maci_registry):
        """Test concurrent register and get operations are thread-safe."""
        import asyncio

        # Register agents concurrently
        async def register_agent(i):
            await maci_registry.register_agent(f"agent-{i}", MACIRole.EXECUTIVE)

        async def get_agent(i):
            await asyncio.sleep(0.001)  # Small delay to create race condition
            return await maci_registry.get_agent(f"agent-{i}")

        # Run register and get operations concurrently
        tasks = []
        for i in range(10):
            tasks.append(register_agent(i))
            tasks.append(get_agent(i))

        await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all agents were registered
        for i in range(10):
            record = await maci_registry.get_agent(f"agent-{i}")
            assert record is not None
            assert record.agent_id == f"agent-{i}"

    @pytest.mark.asyncio
    async def test_concurrent_get_agents_by_role(self, maci_registry):
        """Test concurrent get_agents_by_role is thread-safe."""
        import asyncio

        # Register agents of different roles
        for i in range(5):
            await maci_registry.register_agent(f"exec-{i}", MACIRole.EXECUTIVE)
            await maci_registry.register_agent(f"jud-{i}", MACIRole.JUDICIAL)

        # Get agents by role concurrently
        async def get_by_role(role):
            return await maci_registry.get_agents_by_role(role)

        results = await asyncio.gather(
            *[get_by_role(MACIRole.EXECUTIVE) for _ in range(10)],
            *[get_by_role(MACIRole.JUDICIAL) for _ in range(10)],
        )

        # All results should be consistent
        for result in results[:10]:  # Executive results
            assert len(result) == 5
        for result in results[10:]:  # Judicial results
            assert len(result) == 5

    @pytest.mark.asyncio
    async def test_concurrent_output_producer_lookup(self, maci_registry):
        """Test concurrent output producer lookups are thread-safe."""
        import asyncio

        await maci_registry.register_agent("exec-1", MACIRole.EXECUTIVE)

        # Record outputs and look them up concurrently
        async def record_and_lookup(i):
            await maci_registry.record_output("exec-1", f"output-{i}")
            await asyncio.sleep(0.001)
            return await maci_registry.get_output_producer(f"output-{i}")

        results = await asyncio.gather(*[record_and_lookup(i) for i in range(10)])

        # All lookups should return the correct producer
        assert all(r == "exec-1" for r in results)
