"""
Linear webhook signature verification middleware.

Provides authentication for incoming Linear webhook requests using HMAC-SHA256
signature verification. Linear signs webhook payloads with a shared secret to
ensure authenticity and integrity.

References:
- https://developers.linear.app/docs/graphql/webhooks#verifying-webhook-signatures
"""

import logging
from typing import Optional

from fastapi import Header, HTTPException, Request, status
from pydantic import SecretStr

from ...config import get_linear_config
from ...webhooks.auth import AuthResult, HmacAuthHandler

logger = logging.getLogger(__name__)


# ============================================================================
# Linear Webhook Authentication
# ============================================================================


class LinearWebhookAuthError(Exception):
    """Base exception for Linear webhook authentication errors."""

    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def get_linear_webhook_handler() -> HmacAuthHandler:
    """
    Get configured HMAC handler for Linear webhook verification.

    Returns:
        HmacAuthHandler: Configured handler with Linear webhook secret

    Raises:
        RuntimeError: If LINEAR_WEBHOOK_SECRET is not configured
    """
    config = get_linear_config()

    if not config.linear_webhook_secret:
        raise RuntimeError(
            "LINEAR_WEBHOOK_SECRET is not configured. "
            "Cannot verify Linear webhook signatures."
        )

    # Linear uses HMAC-SHA256 with a simple signature format
    # The signature is sent in the X-Linear-Signature header
    return HmacAuthHandler(
        secret=config.linear_webhook_secret,
        signature_header="X-Linear-Signature",
        timestamp_header="X-Linear-Timestamp",
        algorithm="sha256",
        timestamp_tolerance_seconds=300,  # 5 minutes
        require_timestamp=False,  # Linear doesn't include timestamp in signature
    )


async def verify_linear_webhook_signature(
    request: Request,
    x_linear_signature: Optional[str] = Header(None, alias="X-Linear-Signature"),
) -> AuthResult:
    """
    FastAPI dependency for verifying Linear webhook signatures.

    This function can be used as a dependency in FastAPI routes to ensure that
    incoming webhook requests are authentically from Linear.

    Args:
        request: FastAPI request object
        x_linear_signature: Linear signature header value

    Returns:
        AuthResult: Authentication result with verification details

    Raises:
        HTTPException: If signature verification fails (401 Unauthorized)

    Example:
        @router.post("/webhooks/linear")
        async def handle_linear_webhook(
            request: Request,
            auth: AuthResult = Depends(verify_linear_webhook_signature),
        ):
            # Webhook is authenticated, process the event
            body = await request.json()
            ...
    """
    try:
        # Check for signature header
        if not x_linear_signature:
            logger.warning("Linear webhook received without signature header")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing X-Linear-Signature header",
                headers={"WWW-Authenticate": "Signature"},
            )

        # Get webhook handler
        try:
            handler = get_linear_webhook_handler()
        except RuntimeError as e:
            logger.error(f"Failed to initialize Linear webhook handler: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Webhook verification is not properly configured",
            ) from None

        # Read request body
        body = await request.body()

        # Get all headers as dict
        headers = dict(request.headers)

        # Verify signature
        result = await handler.verify_request(
            headers=headers,
            body=body,
            method=request.method,
            url=str(request.url),
        )

        if not result.authenticated:
            logger.warning(
                f"Linear webhook signature verification failed: "
                f"{result.error_code} - {result.error_message}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Signature verification failed: {result.error_message}",
                headers={"WWW-Authenticate": "Signature"},
            )

        logger.debug("Linear webhook signature verified successfully")
        return result

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.exception(f"Unexpected error during Linear webhook verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during signature verification",
        ) from None


async def verify_linear_webhook_signature_strict(
    request: Request,
    x_linear_signature: Optional[str] = Header(None, alias="X-Linear-Signature"),
) -> None:
    """
    Strict Linear webhook signature verification (no return value).

    This is a simpler version of verify_linear_webhook_signature that doesn't
    return the AuthResult, making it suitable for use cases where you just want
    to block unauthorized requests without needing the auth details.

    Args:
        request: FastAPI request object
        x_linear_signature: Linear signature header value

    Raises:
        HTTPException: If signature verification fails (401 Unauthorized)

    Example:
        @router.post(
            "/webhooks/linear",
            dependencies=[Depends(verify_linear_webhook_signature_strict)],
        )
        async def handle_linear_webhook(request: Request):
            # This handler will only be called if signature is valid
            body = await request.json()
            ...
    """
    await verify_linear_webhook_signature(request, x_linear_signature)


def verify_linear_signature_sync(
    body: bytes,
    signature: str,
    secret: Optional[SecretStr] = None,
) -> bool:
    """
    Synchronous Linear webhook signature verification (for testing or utilities).

    This function provides a synchronous way to verify Linear signatures without
    FastAPI dependencies, useful for testing or background processing.

    Args:
        body: Raw request body bytes
        signature: Signature from X-Linear-Signature header
        secret: Optional override for webhook secret (uses config if not provided)

    Returns:
        bool: True if signature is valid, False otherwise

    Example:
        >>> body = b'{"action": "create", "data": {...}}'
        >>> signature = "sha256=abc123..."
        >>> is_valid = verify_linear_signature_sync(body, signature)
        >>> if is_valid:
        ...     print("Signature verified!")
    """
    try:
        # Get secret from config if not provided
        if secret is None:
            config = get_linear_config()
            secret = config.linear_webhook_secret

        if not secret:
            logger.error("LINEAR_WEBHOOK_SECRET is not configured")
            return False

        # Create handler
        handler = HmacAuthHandler(
            secret=secret,
            signature_header="X-Linear-Signature",
            algorithm="sha256",
            require_timestamp=False,
        )

        # Prepare headers dict
        headers = {"X-Linear-Signature": signature}

        # Verify using sync execution (wrap async in sync context)
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = loop.run_until_complete(
            handler.verify_request(headers=headers, body=body)
        )

        return result.authenticated

    except Exception as e:
        logger.error(f"Error during synchronous signature verification: {e}")
        return False


# ============================================================================
# Utility Functions
# ============================================================================


def format_linear_signature_for_logging(signature: str) -> str:
    """
    Format Linear signature for safe logging (redact actual signature value).

    Args:
        signature: Full signature string (e.g., "sha256=abc123...")

    Returns:
        str: Redacted signature for logging (e.g., "sha256=abc...***")
    """
    if not signature:
        return "<empty>"

    # Show algorithm and first few chars, redact the rest
    if "=" in signature:
        algo, sig_value = signature.split("=", 1)
        if len(sig_value) > 6:
            return f"{algo}={sig_value[:6]}...***"
        return f"{algo}=***"

    # If no algorithm prefix, just show first few chars
    if len(signature) > 6:
        return f"{signature[:6]}...***"
    return "***"


def is_linear_webhook_configured() -> bool:
    """
    Check if Linear webhook authentication is properly configured.

    Returns:
        bool: True if LINEAR_WEBHOOK_SECRET is set, False otherwise
    """
    try:
        config = get_linear_config()
        return config.linear_webhook_secret is not None
    except Exception as e:
        logger.error(f"Error checking Linear webhook configuration: {e}")
        return False
