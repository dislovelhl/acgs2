"""Constitutional Hash: cdd01ef066bc6cf2
ACGS-2 CLI OPA Service

Provides OPA (Open Policy Agent) integration for CLI policy validation and testing.
Follows patterns from src.core.enhanced_agent_bus/opa_client.py but simplified for CLI use cases.
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class PolicyValidationResult:
    """Result of policy validation."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_error(self, error: str) -> None:
        """Add an error to the result."""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """Add a warning to the result."""
        self.warnings.append(warning)


@dataclass
class PolicyEvaluationResult:
    """Result of policy evaluation."""

    success: bool
    result: Any = None
    allowed: Optional[bool] = None
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class OPAServiceError(Exception):
    """Base exception for OPA service errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class OPAConnectionError(OPAServiceError):
    """Raised when connection to OPA server fails."""

    def __init__(self, opa_url: str, reason: str) -> None:
        self.opa_url = opa_url
        self.reason = reason
        super().__init__(
            message=f"Failed to connect to OPA at '{opa_url}': {reason}",
            details={"opa_url": opa_url, "reason": reason},
        )


class OPAService:
    """
    OPA Service for CLI policy operations.

    Provides simplified OPA integration for:
    - Policy syntax validation
    - Policy evaluation against input data
    - Health checks

    Follows the patterns from src.core.enhanced_agent_bus/opa_client.py
    but focused on CLI use cases without caching or embedded mode.
    """

    DEFAULT_OPA_URL = "http://localhost:8181"

    def __init__(
        self,
        opa_url: Optional[str] = None,
        timeout: float = 10.0,
    ):
        """
        Initialize OPA service.

        Args:
            opa_url: OPA server URL. Defaults to OPA_URL env var or http://localhost:8181
            timeout: Request timeout in seconds
        """
        self.opa_url = (opa_url or os.getenv("OPA_URL", self.DEFAULT_OPA_URL)).rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None
        self._async_client: Optional[httpx.AsyncClient] = None

    def __enter__(self) -> "OPAService":
        """Context manager entry - initialize sync client."""
        self._ensure_client()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - close sync client."""
        self.close()

    async def __aenter__(self) -> "OPAService":
        """Async context manager entry - initialize async client."""
        await self._ensure_async_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - close async client."""
        await self.aclose()

    def _ensure_client(self) -> httpx.Client:
        """Ensure sync HTTP client is initialized."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.timeout,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )
        return self._client

    async def _ensure_async_client(self) -> httpx.AsyncClient:
        """Ensure async HTTP client is initialized."""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )
        return self._async_client

    def close(self) -> None:
        """Close sync HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    async def aclose(self) -> None:
        """Close async HTTP client."""
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None

    def _sanitize_error(self, error: Exception) -> str:
        """Strip sensitive metadata from error messages."""
        error_msg = str(error)
        error_msg = re.sub(r"key=[^&\s]+", "key=REDACTED", error_msg)
        error_msg = re.sub(r"token=[^&\s]+", "token=REDACTED", error_msg)
        error_msg = re.sub(r"https?://[^:\s]+:[^@\s]+@", "http://REDACTED@", error_msg)
        return error_msg

    def _parse_opa_error(self, response: httpx.Response) -> List[str]:
        """Parse OPA error response into user-friendly error messages."""
        errors = []
        try:
            data = response.json()
            if "errors" in data:
                for error in data["errors"]:
                    msg = error.get("message", str(error))
                    location = error.get("location", {})
                    if location:
                        line = location.get("row", "?")
                        col = location.get("col", "?")
                        msg = f"Line {line}, Col {col}: {msg}"
                    errors.append(msg)
            elif "error" in data:
                errors.append(data["error"])
            elif "code" in data and "message" in data:
                errors.append(f"{data['code']}: {data['message']}")
        except json.JSONDecodeError:
            errors.append(response.text or f"HTTP {response.status_code}")
        return errors if errors else [f"OPA error: HTTP {response.status_code}"]

    def health_check(self) -> Dict[str, Any]:
        """
        Check OPA server health (sync).

        Returns:
            Dict with status and details
        """
        try:
            client = self._ensure_client()
            response = client.get(f"{self.opa_url}/health", timeout=2.0)
            if response.status_code == 200:
                return {"status": "healthy", "opa_url": self.opa_url}
            return {
                "status": "unhealthy",
                "opa_url": self.opa_url,
                "http_status": response.status_code,
            }
        except httpx.ConnectError as e:
            return {
                "status": "unreachable",
                "opa_url": self.opa_url,
                "error": self._sanitize_error(e),
            }
        except Exception as e:
            return {
                "status": "error",
                "opa_url": self.opa_url,
                "error": self._sanitize_error(e),
            }

    async def async_health_check(self) -> Dict[str, Any]:
        """
        Check OPA server health (async).

        Returns:
            Dict with status and details
        """
        try:
            client = await self._ensure_async_client()
            response = await client.get(f"{self.opa_url}/health", timeout=2.0)
            if response.status_code == 200:
                return {"status": "healthy", "opa_url": self.opa_url}
            return {
                "status": "unhealthy",
                "opa_url": self.opa_url,
                "http_status": response.status_code,
            }
        except httpx.ConnectError as e:
            return {
                "status": "unreachable",
                "opa_url": self.opa_url,
                "error": self._sanitize_error(e),
            }
        except Exception as e:
            return {
                "status": "error",
                "opa_url": self.opa_url,
                "error": self._sanitize_error(e),
            }

    def validate_policy(self, policy_content: str) -> PolicyValidationResult:
        """
        Validate Rego policy syntax (sync).

        Uses OPA's /v1/compile endpoint to check policy syntax without
        actually deploying the policy.

        Args:
            policy_content: Rego policy content as string

        Returns:
            PolicyValidationResult with validation status and any errors
        """
        result = PolicyValidationResult(is_valid=True)

        if not policy_content.strip():
            result.add_error("Policy content is empty")
            return result

        try:
            client = self._ensure_client()

            # Upload policy to a temporary location for full validation
            temp_policy_id = "_cli_validation_temp"
            put_response = client.put(
                f"{self.opa_url}/v1/policies/{temp_policy_id}",
                content=policy_content,
                headers={"Content-Type": "text/plain"},
            )

            if put_response.status_code == 200:
                result.is_valid = True
                result.metadata["validated_via"] = "policy_upload"

                # Clean up temporary policy
                try:
                    client.delete(f"{self.opa_url}/v1/policies/{temp_policy_id}")
                except Exception:
                    pass  # Ignore cleanup errors
            else:
                result.is_valid = False
                result.errors = self._parse_opa_error(put_response)
                result.metadata["validated_via"] = "policy_upload"

        except httpx.ConnectError as e:
            raise OPAConnectionError(
                self.opa_url,
                "OPA server not reachable. Start with: "
                "docker run -p 8181:8181 openpolicyagent/opa run --server",
            ) from e
        except Exception as e:
            result.add_error(f"Validation failed: {self._sanitize_error(e)}")
            result.metadata["error_type"] = type(e).__name__

        return result

    async def async_validate_policy(self, policy_content: str) -> PolicyValidationResult:
        """
        Validate Rego policy syntax (async).

        Uses OPA's /v1/compile endpoint to check policy syntax without
        actually deploying the policy.

        Args:
            policy_content: Rego policy content as string

        Returns:
            PolicyValidationResult with validation status and any errors
        """
        result = PolicyValidationResult(is_valid=True)

        if not policy_content.strip():
            result.add_error("Policy content is empty")
            return result

        try:
            client = await self._ensure_async_client()

            # Try uploading policy to a temporary location for full validation
            temp_policy_id = "_cli_validation_temp"
            put_response = await client.put(
                f"{self.opa_url}/v1/policies/{temp_policy_id}",
                content=policy_content,
                headers={"Content-Type": "text/plain"},
            )

            if put_response.status_code == 200:
                result.is_valid = True
                result.metadata["validated_via"] = "policy_upload"

                # Clean up temporary policy
                try:
                    await client.delete(f"{self.opa_url}/v1/policies/{temp_policy_id}")
                except Exception:
                    pass  # Ignore cleanup errors
            else:
                result.is_valid = False
                result.errors = self._parse_opa_error(put_response)
                result.metadata["validated_via"] = "policy_upload"

        except httpx.ConnectError as e:
            raise OPAConnectionError(
                self.opa_url,
                "OPA server not reachable. Start with: "
                "docker run -p 8181:8181 openpolicyagent/opa run --server",
            ) from e
        except Exception as e:
            result.add_error(f"Validation failed: {self._sanitize_error(e)}")
            result.metadata["error_type"] = type(e).__name__

        return result

    def evaluate_policy(
        self,
        policy_content: str,
        input_data: Dict[str, Any],
        policy_path: str = "data",
    ) -> PolicyEvaluationResult:
        """
        Evaluate policy against input data (sync).

        Temporarily uploads the policy, evaluates it, then removes it.

        Args:
            policy_content: Rego policy content as string
            input_data: Input data for policy evaluation
            policy_path: Policy data path to query (default: "data")

        Returns:
            PolicyEvaluationResult with evaluation results
        """
        result = PolicyEvaluationResult(success=False)

        try:
            client = self._ensure_client()
            temp_policy_id = "_cli_eval_temp"

            # Upload policy
            put_response = client.put(
                f"{self.opa_url}/v1/policies/{temp_policy_id}",
                content=policy_content,
                headers={"Content-Type": "text/plain"},
            )

            if put_response.status_code != 200:
                result.reason = "Policy upload failed"
                result.metadata["errors"] = self._parse_opa_error(put_response)
                return result

            try:
                # Evaluate policy - wrap input in "input" key as per OPA API
                path_parts = policy_path.replace("data.", "").replace(".", "/")
                eval_url = (
                    f"{self.opa_url}/v1/data/{path_parts}"
                    if path_parts
                    else f"{self.opa_url}/v1/data"
                )

                eval_response = client.post(
                    eval_url,
                    json={"input": input_data},
                    headers={"Content-Type": "application/json"},
                )

                if eval_response.status_code == 200:
                    data = eval_response.json()
                    opa_result = data.get("result", {})

                    result.success = True
                    result.result = opa_result
                    result.reason = "Policy evaluated successfully"

                    # Extract 'allow' if present
                    if isinstance(opa_result, dict) and "allow" in opa_result:
                        result.allowed = opa_result.get("allow", False)
                    elif isinstance(opa_result, bool):
                        result.allowed = opa_result

                    result.metadata["policy_path"] = policy_path
                else:
                    result.reason = "Evaluation failed"
                    result.metadata["errors"] = self._parse_opa_error(eval_response)

            finally:
                # Clean up policy
                try:
                    client.delete(f"{self.opa_url}/v1/policies/{temp_policy_id}")
                except Exception:
                    pass

        except httpx.ConnectError as e:
            raise OPAConnectionError(
                self.opa_url,
                "OPA server not reachable. Start with: "
                "docker run -p 8181:8181 openpolicyagent/opa run --server",
            ) from e
        except Exception as e:
            result.reason = f"Evaluation error: {self._sanitize_error(e)}"
            result.metadata["error_type"] = type(e).__name__

        return result

    async def async_evaluate_policy(
        self,
        policy_content: str,
        input_data: Dict[str, Any],
        policy_path: str = "data",
    ) -> PolicyEvaluationResult:
        """
        Evaluate policy against input data (async).

        Temporarily uploads the policy, evaluates it, then removes it.

        Args:
            policy_content: Rego policy content as string
            input_data: Input data for policy evaluation
            policy_path: Policy data path to query (default: "data")

        Returns:
            PolicyEvaluationResult with evaluation results
        """
        result = PolicyEvaluationResult(success=False)

        try:
            client = await self._ensure_async_client()
            temp_policy_id = "_cli_eval_temp"

            # Upload policy
            put_response = await client.put(
                f"{self.opa_url}/v1/policies/{temp_policy_id}",
                content=policy_content,
                headers={"Content-Type": "text/plain"},
            )

            if put_response.status_code != 200:
                result.reason = "Policy upload failed"
                result.metadata["errors"] = self._parse_opa_error(put_response)
                return result

            try:
                # Evaluate policy - wrap input in "input" key as per OPA API
                path_parts = policy_path.replace("data.", "").replace(".", "/")
                eval_url = (
                    f"{self.opa_url}/v1/data/{path_parts}"
                    if path_parts
                    else f"{self.opa_url}/v1/data"
                )

                eval_response = await client.post(
                    eval_url,
                    json={"input": input_data},
                    headers={"Content-Type": "application/json"},
                )

                if eval_response.status_code == 200:
                    data = eval_response.json()
                    opa_result = data.get("result", {})

                    result.success = True
                    result.result = opa_result
                    result.reason = "Policy evaluated successfully"

                    # Extract 'allow' if present
                    if isinstance(opa_result, dict) and "allow" in opa_result:
                        result.allowed = opa_result.get("allow", False)
                    elif isinstance(opa_result, bool):
                        result.allowed = opa_result

                    result.metadata["policy_path"] = policy_path
                else:
                    result.reason = "Evaluation failed"
                    result.metadata["errors"] = self._parse_opa_error(eval_response)

            finally:
                # Clean up policy
                try:
                    await client.delete(f"{self.opa_url}/v1/policies/{temp_policy_id}")
                except Exception:
                    pass

        except httpx.ConnectError as e:
            raise OPAConnectionError(
                self.opa_url,
                "OPA server not reachable. Start with: "
                "docker run -p 8181:8181 openpolicyagent/opa run --server",
            ) from e
        except Exception as e:
            result.reason = f"Evaluation error: {self._sanitize_error(e)}"
            result.metadata["error_type"] = type(e).__name__

        return result

    def get_connection_info(self) -> Dict[str, Any]:
        """Get OPA connection information."""
        return {
            "opa_url": self.opa_url,
            "timeout": self.timeout,
            "client_initialized": self._client is not None,
            "async_client_initialized": self._async_client is not None,
        }


__all__ = [
    "OPAService",
    "OPAServiceError",
    "OPAConnectionError",
    "PolicyValidationResult",
    "PolicyEvaluationResult",
]
