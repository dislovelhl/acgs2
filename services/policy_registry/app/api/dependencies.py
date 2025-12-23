"""
API Dependencies for Policy Registry
Constitutional Hash: cdd01ef066bc6cf2

Provides dependency injection factories for FastAPI routes.
"""

from typing import Optional

from ..services import PolicyService, CacheService, NotificationService, CryptoService


# Singleton instances for service caching
_policy_service: Optional[PolicyService] = None
_cache_service: Optional[CacheService] = None
_notification_service: Optional[NotificationService] = None
_crypto_service: Optional[CryptoService] = None


async def get_crypto_service():
    """Get or create CryptoService instance."""
    global _crypto_service
    if _crypto_service is None:
        _crypto_service = CryptoService()
    return _crypto_service


async def get_cache_service():
    """Get or create CacheService instance."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


async def get_notification_service():
    """Get or create NotificationService instance."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service


async def get_policy_service():
    """Get or create PolicyService instance with dependencies."""
    global _policy_service
    if _policy_service is None:
        crypto_service = await get_crypto_service()
        cache_service = await get_cache_service()
        notification_service = await get_notification_service()

        _policy_service = PolicyService(
            crypto_service=crypto_service,
            cache_service=cache_service,
            notification_service=notification_service
        )
    return _policy_service


def reset_services():
    """Reset all service instances. Useful for testing."""
    global _policy_service, _cache_service, _notification_service, _crypto_service
    _policy_service = None
    _cache_service = None
    _notification_service = None
    _crypto_service = None
