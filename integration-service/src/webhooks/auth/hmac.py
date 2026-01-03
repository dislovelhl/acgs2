"""
HMAC signature authentication handler for ACGS-2 Integration Service.

This module provides HMAC signature-based authentication for webhooks, verifying
payload integrity and authenticity using HMAC signatures. Supports SHA-256 and
SHA-512 algorithms with timestamp validation for replay protection. Implements
constant-time signature comparison to prevent timing attacks.
"""

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from pydantic import SecretStr

from ..models import WebhookAuthType
from .base import WebhookAuthHandler
from .models import AuthResult

logger = logging.getLogger(__name__)


class HmacAuthHandler(WebhookAuthHandler):
    """
    HMAC signature authentication handler.

    Verifies webhook requests using HMAC signatures for payload integrity
    and authenticity. Supports SHA-256 and SHA-512 algorithms.

    Security features:
    - Constant-time signature comparison to prevent timing attacks
    - Timestamp validation for replay protection
    - Multiple signature formats (sha256=xxx, t=xxx,v1=xxx)
    """

    # Supported algorithms
    ALGORITHMS = {
        "sha256": hashlib.sha256,
        "sha512": hashlib.sha512,
    }

    def __init__(
        self,
        secret: SecretStr,
        signature_header: str = "X-Webhook-Signature",
        timestamp_header: str = "X-Webhook-Timestamp",
        algorithm: str = "sha256",
        timestamp_tolerance_seconds: int = 300,
        require_timestamp: bool = True,
    ):
        """
        Initialize HMAC handler.

        Args:
            secret: HMAC secret key
            signature_header: Header name for signature
            timestamp_header: Header name for timestamp
            algorithm: Hash algorithm (sha256 or sha512)
            timestamp_tolerance_seconds: Maximum age of request in seconds
            require_timestamp: Whether to require and validate timestamp
        """
        self._secret = secret
        self._signature_header = signature_header
        self._timestamp_header = timestamp_header
        self._timestamp_tolerance = timestamp_tolerance_seconds
        self._require_timestamp = require_timestamp

        algorithm = algorithm.lower()
        if algorithm not in self.ALGORITHMS:
            raise ValueError(f"Unsupported algorithm: {algorithm}. Use 'sha256' or 'sha512'")
        self._algorithm = algorithm
        self._hash_func = self.ALGORITHMS[algorithm]

    @property
    def auth_type(self) -> WebhookAuthType:
        return WebhookAuthType.HMAC

    def _compute_signature(self, payload: bytes, timestamp: Optional[str] = None) -> str:
        """
        Compute HMAC signature for payload.

        Args:
            payload: Request body bytes
            timestamp: Optional timestamp to include in signed data

        Returns:
            Hex-encoded signature
        """
        secret = self._secret.get_secret_value().encode("utf-8")

        # If timestamp provided, prepend it to the payload (Stripe-style)
        if timestamp:
            signed_payload = f"{timestamp}.".encode("utf-8") + payload
        else:
            signed_payload = payload

        signature = hmac.new(secret, signed_payload, self._hash_func).hexdigest()
        return signature

    def _parse_signature_header(self, header_value: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse signature header value.

        Supports multiple formats:
        - "sha256=abcd1234..."  (simple format)
        - "t=1234567890,v1=abcd1234..."  (Stripe-style with timestamp)

        Args:
            header_value: Raw header value

        Returns:
            Tuple of (signature, timestamp) - timestamp may be None
        """
        header_value = header_value.strip()

        # Try Stripe-style format: t=timestamp,v1=signature
        if "," in header_value and "=" in header_value:
            parts = {}
            for part in header_value.split(","):
                if "=" in part:
                    key, value = part.split("=", 1)
                    parts[key.strip()] = value.strip()

            timestamp = parts.get("t")
            signature = parts.get("v1") or parts.get("v2")
            if signature:
                return signature, timestamp

        # Try simple format: algorithm=signature
        if "=" in header_value:
            prefix, signature = header_value.split("=", 1)
            prefix_lower = prefix.lower().strip()
            if prefix_lower in ("sha256", "sha512"):
                return signature.strip(), None
            # If prefix doesn't match known algorithm, treat whole value as signature
            return header_value, None

        # Plain signature
        return header_value, None

    def _validate_timestamp(self, timestamp_str: str) -> bool:
        """
        Validate timestamp is within acceptable range.

        Args:
            timestamp_str: Timestamp as string (epoch seconds or ISO format)

        Returns:
            True if timestamp is valid
        """
        try:
            # Try parsing as epoch seconds
            if timestamp_str.isdigit():
                timestamp = int(timestamp_str)
                request_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            else:
                # Try ISO format
                request_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

            now = datetime.now(timezone.utc)
            age = abs((now - request_time).total_seconds())

            return age <= self._timestamp_tolerance

        except (ValueError, OverflowError):
            return False

    async def verify_request(
        self,
        headers: Dict[str, str],
        body: bytes,
        method: str = "POST",
        url: Optional[str] = None,
    ) -> AuthResult:
        """Verify HMAC signature on request."""
        # Normalize headers
        normalized_headers = {k.lower(): v for k, v in headers.items()}

        # Get signature header
        sig_header_lower = self._signature_header.lower()
        signature_value = normalized_headers.get(sig_header_lower)

        if signature_value is None:
            return AuthResult.failure(
                auth_type=self.auth_type,
                error_code="MISSING_SIGNATURE",
                error_message=f"Missing {self._signature_header} header",
            )

        # Parse signature header
        provided_signature, header_timestamp = self._parse_signature_header(signature_value)

        if provided_signature is None:
            return AuthResult.failure(
                auth_type=self.auth_type,
                error_code="INVALID_SIGNATURE_FORMAT",
                error_message="Could not parse signature from header",
            )

        # Get timestamp from header or dedicated timestamp header
        timestamp = header_timestamp
        if timestamp is None:
            ts_header_lower = self._timestamp_header.lower()
            timestamp = normalized_headers.get(ts_header_lower)

        # Validate timestamp if required
        if self._require_timestamp:
            if timestamp is None:
                return AuthResult.failure(
                    auth_type=self.auth_type,
                    error_code="MISSING_TIMESTAMP",
                    error_message=f"Missing {self._timestamp_header} header",
                )

            if not self._validate_timestamp(timestamp):
                return AuthResult.failure(
                    auth_type=self.auth_type,
                    error_code="TIMESTAMP_EXPIRED",
                    error_message=(
                        f"Request timestamp is outside acceptable window "
                        f"({self._timestamp_tolerance}s)"
                    ),
                )

        # Compute expected signature
        expected_signature = self._compute_signature(body, timestamp if timestamp else None)

        # Constant-time comparison to prevent timing attacks
        if not secrets.compare_digest(provided_signature.lower(), expected_signature.lower()):
            logger.warning("HMAC signature verification failed")
            return AuthResult.failure(
                auth_type=self.auth_type,
                error_code="INVALID_SIGNATURE",
                error_message="Signature verification failed",
            )

        logger.debug("HMAC signature verified successfully")
        return AuthResult.success(
            auth_type=self.auth_type,
            principal="hmac_verified",
            metadata={
                "algorithm": self._algorithm,
                "timestamp": timestamp,
            },
        )

    async def prepare_headers(
        self,
        headers: Dict[str, str],
        body: bytes,
        method: str = "POST",
        url: Optional[str] = None,
    ) -> Dict[str, str]:
        """Add HMAC signature to outgoing request headers."""
        result = dict(headers)

        # Generate timestamp
        timestamp = str(int(datetime.now(timezone.utc).timestamp()))
        result[self._timestamp_header] = timestamp

        # Compute signature
        signature = self._compute_signature(body, timestamp)
        result[self._signature_header] = f"{self._algorithm}={signature}"

        return result


__all__ = [
    "HmacAuthHandler",
]
