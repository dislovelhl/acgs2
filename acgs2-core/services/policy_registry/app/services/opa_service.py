"""
OPA Service for Policy Registry
Constitutional Hash: cdd01ef066bc6cf2
"""

import hashlib
import logging
import httpx
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

try:
    from shared.config import settings
except ImportError:
    # Fallback for local development or testing
    try:
        from ....shared.config import settings
    except ImportError:
        settings = None

logger = logging.getLogger(__name__)

# In-memory cache for authorization decisions
# Key: (user_role, action, resource) -> (result, expiry_timestamp)
_auth_cache: Dict[str, Tuple[bool, float]] = {}
AUTH_CACHE_TTL_SECONDS = 900  # 15 minutes

class OPAService:
    """
    Service for interacting with Open Policy Agent (OPA).
    Used for RBAC and granular authorization.
    """
    
    def __init__(self):
        if settings:
            self.opa_url = settings.opa.url
            self.fail_closed = settings.opa.fail_closed
        else:
            self.opa_url = "http://localhost:8181"
            self.fail_closed = True
        
    def _get_cache_key(self, user: Dict[str, Any], action: str, resource: str) -> str:
        """Generate cache key from authorization parameters."""
        # Use role for caching (role-based, not user-specific)
        role = user.get("role", "unknown")
        key_str = f"{role}:{action}:{resource}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _check_cache(self, cache_key: str) -> Optional[bool]:
        """Check if authorization result is cached and valid."""
        if cache_key in _auth_cache:
            result, expiry = _auth_cache[cache_key]
            if datetime.now(timezone.utc).timestamp() < expiry:
                logger.debug(f"Authorization cache hit for key {cache_key[:8]}...")
                return result
            else:
                # Expired entry
                del _auth_cache[cache_key]
        return None

    def _cache_result(self, cache_key: str, result: bool) -> None:
        """Cache authorization result with TTL."""
        expiry = datetime.now(timezone.utc).timestamp() + AUTH_CACHE_TTL_SECONDS
        _auth_cache[cache_key] = (result, expiry)

        # Clean up expired entries periodically (every 100 entries)
        if len(_auth_cache) > 100:
            self._cleanup_expired_cache()

    def _cleanup_expired_cache(self) -> None:
        """Remove expired cache entries."""
        now = datetime.now(timezone.utc).timestamp()
        expired_keys = [k for k, (_, expiry) in _auth_cache.items() if expiry < now]
        for key in expired_keys:
            del _auth_cache[key]

    async def check_authorization(
        self,
        user: Dict[str, Any],
        action: str,
        resource: str
    ) -> bool:
        """
        Check if a user is authorized for an action on a resource.
        Queries the 'acgs.rbac.allow' rule in OPA with caching.

        Cache TTL: 15 minutes for role-based authorization decisions.
        """
        # Check cache first
        cache_key = self._get_cache_key(user, action, resource)
        cached_result = self._check_cache(cache_key)
        if cached_result is not None:
            return cached_result

        input_data = {
            "input": {
                "user": user,
                "action": action,
                "resource": resource
            }
        }

        # OPA data API path for the rbac policy
        policy_path = "acgs/rbac/allow"
        url = f"{self.opa_url}/v1/data/{policy_path}"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, json=input_data)

                if response.status_code == 200:
                    data = response.json()
                    # OPA returns {"result": true/false}
                    result = data.get("result", False)
                    logger.info(f"OPA RBAC check: user={user.get('agent_id')}, role={user.get('role')}, action={action}, resource={resource}, result={result}")

                    # Cache the result
                    self._cache_result(cache_key, result)
                    return result
                else:
                    logger.error(f"OPA returned non-200 status: {response.status_code} - {response.text}")
                    return False if self.fail_closed else True

        except Exception as e:
            logger.error(f"Error connecting to OPA: {e}")
            return False if self.fail_closed else True

    def invalidate_cache(self, role: Optional[str] = None) -> int:
        """
        Invalidate authorization cache.

        Args:
            role: If specified, only invalidate entries for this role.
                  If None, clear entire cache.

        Returns:
            Number of cache entries invalidated.
        """
        global _auth_cache
        if role is None:
            count = len(_auth_cache)
            _auth_cache = {}
            logger.info(f"Invalidated entire authorization cache ({count} entries)")
            return count
        else:
            # Selective invalidation would require different key structure
            # For now, clear all if role specified
            count = len(_auth_cache)
            _auth_cache = {}
            logger.info(f"Invalidated authorization cache for role changes ({count} entries)")
            return count
