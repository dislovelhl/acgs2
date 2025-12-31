
"""Advanced ACL Adapters Tests - Coverage Enhancement

Constitutional Hash: cdd01ef066bc6cf2

Tests for HTTP/Z3 integration paths, error handling, caching, circuit breaker to improve coverage from 28-33% to >90%.

Uses pytest-mock for external deps."""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Dict, Any

from ...acl_adapters.base import (
    AdapterConfig,
    AdapterResult,
)

from ...acl_adapters.opa_adapter import (
    OPAAdapter,
    OPAAdapterConfig,
    OPARequest,
    OPAResponse,
)

from ...acl_adapters.z3_adapter import (
    Z3Adapter