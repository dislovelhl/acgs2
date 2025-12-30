"""
Health check API endpoints
Constitutional Hash: cdd01ef066bc6cf2
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends

from ..dependencies import get_cache_service, get_notification_service, get_policy_service

router = APIRouter()


@router.get("/policies", response_model=Dict[str, Any])
async def policy_health(policy_service=Depends(get_policy_service)):
    """Policy-specific health metrics"""
    policies = await policy_service.list_policies()
    active_policies = [p for p in policies if p.status.name == "ACTIVE"]

    return {
        "total_policies": len(policies),
        "active_policies": len(active_policies),
        "policies": [
            {"id": p.policy_id, "name": p.name, "status": p.status.value} for p in policies
        ],
    }


@router.get("/cache", response_model=Dict[str, Any])
async def cache_health(cache_service=Depends(get_cache_service)):
    """Cache health metrics"""
    return await cache_service.get_cache_stats()


@router.get("/connections", response_model=Dict[str, Any])
async def connection_health(notification_service=Depends(get_notification_service)):
    """Connection health metrics"""
    return await notification_service.get_connection_count()
