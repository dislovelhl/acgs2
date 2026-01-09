"""
Governance Analytics Routes
Constitutional Hash: cdd01ef066bc6cf2

Proxies stability metrics from the Manifold-Constrained HyperConnections (mHC) layer.
"""

import logging
import os
from typing import Any, Dict

import httpx
from fastapi import APIRouter, Depends, HTTPException

from src.core.shared.security.tenant_context import get_tenant_id

router = APIRouter(prefix="/governance", tags=["Governance"])
logger = logging.getLogger(__name__)

# Governance service URL (Agent Bus)
AGENT_BUS_URL = os.getenv("AGENT_BUS_URL", "http://agent-bus:8000")


@router.get("/stability/metrics", response_model=Dict[str, Any])
async def get_stability_metrics(tenant_id: str = Depends(get_tenant_id)):
    """
    Fetch real-time stability metrics from the Governance Service (Agent Bus).

    This proxies the request to the mHC layer to provide a unified analytics view.
    """
    metrics_url = f"{AGENT_BUS_URL}/governance/stability/metrics"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(metrics_url, headers={"X-Tenant-ID": tenant_id})

            if response.status_code != 200:
                logger.error(f"Failed to fetch stability metrics: {response.status_code}")
                raise HTTPException(
                    status_code=response.status_code, detail="Governance service returned an error"
                )

            return response.json()

    except httpx.RequestError as e:
        logger.error(f"Connection error to governance service: {e}")
        raise HTTPException(status_code=503, detail="Governance service is unreachable") from e
    except Exception as e:
        logger.error(f"Unexpected error fetching stability metrics: {e}")
        raise HTTPException(
            status_code=500, detail="Internal error processing stability metrics"
        ) from e
