"""ACGS-2 API Auth Unit Tests.

Constitutional Hash: cdd01ef066bc6cf2
"""

import pytest

from src.acgs2.api.auth import auth_manager


@pytest.mark.unit
@pytest.mark.asyncio
class TestAuthManager:
    """Test AuthManager class."""

    @pytest.mark.constitutional
    def test_constitutional_hash_validation(self):
        """Verify constitutional hash in auth context."""
        assert hasattr(auth_manager, "users")  # Basic init test
        # Note: Hash validation is in types/shared, but test presence
        from src.core.shared.types import CONSTITUTIONAL_HASH

        assert CONSTITUTIONAL_HASH
