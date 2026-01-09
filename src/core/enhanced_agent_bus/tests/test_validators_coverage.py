"""
ACGS-2 Validators Coverage Tests
Constitutional Hash: cdd01ef066bc6cf2

Extended tests to increase validators.py coverage.
"""

try:
    from enhanced_agent_bus.validators import (
        CONSTITUTIONAL_HASH,
        ValidationResult,
        validate_constitutional_hash,
        validate_message_content,
    )
except ImportError:
    from validators import (
        CONSTITUTIONAL_HASH,
        ValidationResult,
        validate_constitutional_hash,
        validate_message_content,
    )


class TestValidationResultExtended:
    """Extended tests for ValidationResult dataclass."""

    def test_default_values(self):
        """ValidationResult has correct defaults."""
        result = ValidationResult()
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.metadata == {}
        assert result.decision == "ALLOW"
        assert result.constitutional_hash == CONSTITUTIONAL_HASH

    def test_add_error_makes_invalid(self):
        """Adding an error sets is_valid to False."""
        result = ValidationResult()
        assert result.is_valid is True
        result.add_error("test error")
        assert result.is_valid is False
        assert "test error" in result.errors

    def test_add_multiple_errors(self):
        """Multiple errors can be added."""
        result = ValidationResult()
        result.add_error("error 1")
        result.add_error("error 2")
        assert len(result.errors) == 2
        assert result.is_valid is False

    def test_add_warning_preserves_validity(self):
        """Adding warning does not change is_valid."""
        result = ValidationResult()
        result.add_warning("test warning")
        assert result.is_valid is True
        assert "test warning" in result.warnings

    def test_merge_combines_results(self):
        """Merge combines errors and warnings."""
        result1 = ValidationResult()
        result1.add_warning("warning 1")

        result2 = ValidationResult()
        result2.add_error("error from 2")
        result2.add_warning("warning 2")

        result1.merge(result2)
        assert result1.is_valid is False
        assert "error from 2" in result1.errors
        assert "warning 1" in result1.warnings
        assert "warning 2" in result1.warnings

    def test_merge_preserves_validity_when_both_valid(self):
        """Merge keeps valid if both are valid."""
        result1 = ValidationResult()
        result2 = ValidationResult()
        result1.merge(result2)
        assert result1.is_valid is True

    def test_to_dict_structure(self):
        """to_dict returns correct structure."""
        result = ValidationResult()
        result.add_error("test error")
        result.add_warning("test warning")
        result.metadata["key"] = "value"

        d = result.to_dict()
        assert d["is_valid"] is False
        assert d["errors"] == ["test error"]
        assert d["warnings"] == ["test warning"]
        assert d["metadata"] == {"key": "value"}
        assert d["decision"] == "ALLOW"
        assert d["constitutional_hash"] == CONSTITUTIONAL_HASH
        assert "timestamp" in d


class TestValidateConstitutionalHash:
    """Tests for validate_constitutional_hash function."""

    def test_valid_hash(self):
        """Valid constitutional hash passes."""
        result = validate_constitutional_hash(CONSTITUTIONAL_HASH)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_invalid_hash_string(self):
        """Invalid hash string fails with error."""
        result = validate_constitutional_hash("wrong_hash_value")
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "mismatch" in result.errors[0].lower()

    def test_non_string_hash(self):
        """Non-string hash type fails."""
        result = validate_constitutional_hash(12345)
        assert result.is_valid is False
        assert "string" in result.errors[0].lower()

    def test_none_hash(self):
        """None hash fails."""
        result = validate_constitutional_hash(None)
        assert result.is_valid is False

    def test_empty_string_hash(self):
        """Empty string hash fails."""
        result = validate_constitutional_hash("")
        assert result.is_valid is False

    def test_partial_hash_sanitized(self):
        """Error message shows only partial hash for security."""
        result = validate_constitutional_hash("1234567890abcdef")
        assert result.is_valid is False
        # Should only show first 8 chars + ...
        error_msg = result.errors[0]
        assert "12345678..." in error_msg


class TestValidateMessageContent:
    """Tests for validate_message_content function."""

    def test_valid_content(self):
        """Valid dict content passes."""
        result = validate_message_content({"action": "test"})
        assert result.is_valid is True

    def test_non_dict_content(self):
        """Non-dict content fails."""
        result = validate_message_content("string content")
        assert result.is_valid is False
        assert "dictionary" in result.errors[0].lower()

    def test_empty_action_warning(self):
        """Empty action field generates warning."""
        result = validate_message_content({"action": ""})
        assert result.is_valid is True  # Still valid, just warning
        assert len(result.warnings) == 1
        assert "action" in result.warnings[0].lower()

    def test_none_action_warning(self):
        """None action field generates warning."""
        result = validate_message_content({"action": None})
        assert result.is_valid is True
        assert len(result.warnings) == 1

    def test_content_without_action(self):
        """Content without action field passes."""
        result = validate_message_content({"data": "value"})
        assert result.is_valid is True
        assert len(result.warnings) == 0

    def test_list_content_fails(self):
        """List content fails validation."""
        result = validate_message_content([1, 2, 3])
        assert result.is_valid is False

    def test_empty_dict_passes(self):
        """Empty dict passes validation."""
        result = validate_message_content({})
        assert result.is_valid is True
