"""
ACGS Code Analysis Engine - Constitutional Utilities Tests
Unit tests for constitutional compliance utilities.

Constitutional Hash: cdd01ef066bc6cf2
"""

from datetime import datetime, timezone

import pytest
from code_analysis_service.app.utils.constitutional import (
    CONSTITUTIONAL_HASH,
    ConstitutionalValidator,
    create_constitutional_metadata,
    ensure_constitutional_compliance,
    generate_content_hash,
    validate_constitutional_hash,
    verify_constitutional_compliance,
)


class TestConstitutionalHash:
    """Tests for constitutional hash constant and validation."""

    def test_constitutional_hash_value(self, constitutional_hash: str) -> None:
        """Test that constitutional hash matches expected value."""
        assert CONSTITUTIONAL_HASH == constitutional_hash
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"

    def test_constitutional_hash_length(self) -> None:
        """Test constitutional hash has correct length."""
        assert len(CONSTITUTIONAL_HASH) == 16

    @pytest.mark.constitutional
    def test_validate_constitutional_hash_valid(self) -> None:
        """Test validation with correct hash."""
        assert validate_constitutional_hash(CONSTITUTIONAL_HASH) is True

    @pytest.mark.constitutional
    def test_validate_constitutional_hash_invalid(self) -> None:
        """Test validation with incorrect hash."""
        assert validate_constitutional_hash("invalid_hash") is False
        assert validate_constitutional_hash("") is False
        assert validate_constitutional_hash("cdd01ef066bc6cf3") is False


class TestEnsureConstitutionalCompliance:
    """Tests for ensure_constitutional_compliance function."""

    @pytest.mark.constitutional
    def test_adds_hash_to_empty_dict(self) -> None:
        """Test adding hash to empty dictionary."""
        data: dict = {}
        result = ensure_constitutional_compliance(data)
        assert result["constitutional_hash"] == CONSTITUTIONAL_HASH

    @pytest.mark.constitutional
    def test_adds_hash_to_existing_data(self, sample_non_compliant_data: dict) -> None:
        """Test adding hash to existing data."""
        result = ensure_constitutional_compliance(sample_non_compliant_data)
        assert result["constitutional_hash"] == CONSTITUTIONAL_HASH
        assert result["service_name"] == "test-service"

    @pytest.mark.constitutional
    def test_overwrites_incorrect_hash(self) -> None:
        """Test that incorrect hash is overwritten."""
        data = {"constitutional_hash": "wrong_hash"}
        result = ensure_constitutional_compliance(data)
        assert result["constitutional_hash"] == CONSTITUTIONAL_HASH


class TestCreateConstitutionalMetadata:
    """Tests for create_constitutional_metadata function."""

    @pytest.mark.constitutional
    def test_creates_valid_metadata(self) -> None:
        """Test metadata creation with all required fields."""
        metadata = create_constitutional_metadata()

        assert "constitutional_hash" in metadata
        assert metadata["constitutional_hash"] == CONSTITUTIONAL_HASH
        assert "compliance_validated_at" in metadata
        assert "service" in metadata
        assert metadata["service"] == "acgs-code-analysis-engine"

    @pytest.mark.constitutional
    def test_metadata_timestamp_is_utc(self) -> None:
        """Test that metadata timestamp is in UTC."""
        metadata = create_constitutional_metadata()
        timestamp_str = metadata["compliance_validated_at"]

        # Parse timestamp and verify it's recent
        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)

        # Should be within last 5 seconds
        assert (now - timestamp).total_seconds() < 5


class TestVerifyConstitutionalCompliance:
    """Tests for verify_constitutional_compliance function."""

    @pytest.mark.constitutional
    def test_verify_compliant_data(self, sample_compliant_data: dict) -> None:
        """Test verification of compliant data."""
        is_compliant, message = verify_constitutional_compliance(sample_compliant_data)
        assert is_compliant is True
        assert "verified" in message.lower()

    @pytest.mark.constitutional
    def test_verify_missing_hash(self, sample_non_compliant_data: dict) -> None:
        """Test verification of data without hash."""
        is_compliant, message = verify_constitutional_compliance(sample_non_compliant_data)
        assert is_compliant is False
        assert "missing" in message.lower()

    @pytest.mark.constitutional
    def test_verify_wrong_hash(self) -> None:
        """Test verification with incorrect hash."""
        data = {"constitutional_hash": "wrong_hash"}
        is_compliant, message = verify_constitutional_compliance(data)
        assert is_compliant is False
        assert "invalid" in message.lower()


class TestGenerateContentHash:
    """Tests for generate_content_hash function."""

    @pytest.mark.constitutional
    def test_generates_prefixed_hash(self) -> None:
        """Test that generated hash includes constitutional prefix."""
        content = "test content"
        result = generate_content_hash(content)

        assert result.startswith(CONSTITUTIONAL_HASH + ":")
        assert len(result) == 16 + 1 + 16  # prefix + colon + content hash

    @pytest.mark.constitutional
    def test_consistent_hash_for_same_content(self) -> None:
        """Test that same content produces same hash."""
        content = "consistent content"
        hash1 = generate_content_hash(content)
        hash2 = generate_content_hash(content)

        assert hash1 == hash2

    @pytest.mark.constitutional
    def test_different_hash_for_different_content(self) -> None:
        """Test that different content produces different hash."""
        hash1 = generate_content_hash("content1")
        hash2 = generate_content_hash("content2")

        assert hash1 != hash2


class TestConstitutionalValidator:
    """Tests for ConstitutionalValidator class."""

    @pytest.fixture
    def validator(self) -> ConstitutionalValidator:
        """Create validator instance for tests."""
        return ConstitutionalValidator()

    @pytest.mark.constitutional
    def test_validator_has_correct_hash(self, validator: ConstitutionalValidator) -> None:
        """Test validator initialized with correct hash."""
        assert validator.hash == CONSTITUTIONAL_HASH

    @pytest.mark.constitutional
    def test_validator_initial_stats(self, validator: ConstitutionalValidator) -> None:
        """Test validator initial statistics are zero."""
        assert validator.validations_performed == 0
        assert validator.validations_passed == 0
        assert validator.validations_failed == 0

    @pytest.mark.constitutional
    def test_validate_compliant_data(
        self, validator: ConstitutionalValidator, sample_compliant_data: dict
    ) -> None:
        """Test validation of compliant data."""
        result = validator.validate(sample_compliant_data)

        assert result is True
        assert validator.validations_performed == 1
        assert validator.validations_passed == 1
        assert validator.validations_failed == 0

    @pytest.mark.constitutional
    def test_validate_non_compliant_data(
        self, validator: ConstitutionalValidator, sample_non_compliant_data: dict
    ) -> None:
        """Test validation of non-compliant data."""
        result = validator.validate(sample_non_compliant_data)

        assert result is False
        assert validator.validations_performed == 1
        assert validator.validations_passed == 0
        assert validator.validations_failed == 1

    @pytest.mark.constitutional
    def test_get_stats(self, validator: ConstitutionalValidator) -> None:
        """Test getting validation statistics."""
        # Perform some validations
        validator.validate({"constitutional_hash": CONSTITUTIONAL_HASH})
        validator.validate({})
        validator.validate({"constitutional_hash": CONSTITUTIONAL_HASH})

        stats = validator.get_stats()

        assert stats["constitutional_hash"] == CONSTITUTIONAL_HASH
        assert stats["validations_performed"] == 3
        assert stats["validations_passed"] == 2
        assert stats["validations_failed"] == 1
        assert stats["compliance_rate"] == pytest.approx(2 / 3, rel=0.01)

    @pytest.mark.constitutional
    def test_compliance_rate_no_validations(self, validator: ConstitutionalValidator) -> None:
        """Test compliance rate with no validations returns 1.0."""
        stats = validator.get_stats()
        assert stats["compliance_rate"] == 1.0
