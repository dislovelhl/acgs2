"""
Health check API endpoints
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends

from ...services import PolicyService, CacheService, NotificationService

router = APIRouter()


@router.get("/policies", response_model=Dict[str, Any])
async def policy_health(
    policy_service: PolicyService = Depends()
):
    """Policy-specific health metrics"""
    policies = await policy_service.list_policies()
    active_policies = [p for p in policies if p.status.name == "ACTIVE"]
    
    return {
        "total_policies": len(policies),
        "active_policies": len(active_policies),
        "policies": [{"id": p.policy_id, "name": p.name, "status": p.status.value} 
                    for p in policies]
    }


@router.get("/cache", response_model=Dict[str, Any])
async def cache_health(
    cache_service: CacheService = Depends()
):
    """Cache health metrics"""
    return await cache_service.get_cache_stats()


@router.get("/connections", response_model=Dict[str, Any])
async def connection_health(
    notification_service: NotificationService = Depends()
):
    """Connection health metrics"""
    return await notification_service.get_connection_count()
