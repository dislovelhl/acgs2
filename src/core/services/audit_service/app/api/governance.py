"""
Governance KPI and Trend Analysis API Endpoints

Provides executive dashboard endpoints for governance metrics,
compliance scores, and trend analysis.

Constitutional Hash: cdd01ef066bc6cf2
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query

from ..models.governance_metrics import (
    GovernanceKPIs,
    GovernanceTrendPoint,
    GovernanceTrends,
    TrendDirection,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# Constants for data freshness check
DATA_STALE_THRESHOLD_DAYS = 7


async def _calculate_kpis_from_ledger(tenant_id: str) -> Dict[str, Any]:
    """
    Calculate governance KPIs from audit ledger data.

    This is a placeholder implementation that returns sample data.
    In production, this would query the audit ledger or metrics database.
    """
    # TODO: Integrate with audit_ledger to calculate real metrics
    # For now, return sample data for API verification
    return {
        "compliance_score": 87.5,
        "controls_passing": 42,
        "controls_failing": 6,
        "controls_total": 48,
        "recent_audits": 12,
        "high_risk_incidents": 2,
        "last_updated": datetime.now(timezone.utc),
        "data_stale": False,
    }


async def _calculate_trend(
    current_score: float, previous_score: float, threshold: float = 2.0
) -> tuple[TrendDirection, float]:
    """
    Calculate trend direction based on score change.

    Args:
        current_score: Current compliance score
        previous_score: Previous period compliance score
        threshold: Minimum change to be considered improving/declining

    Returns:
        Tuple of (trend_direction, change_percent)
    """
    if previous_score == 0:
        return TrendDirection.STABLE, 0.0

    change_percent = ((current_score - previous_score) / previous_score) * 100

    if change_percent > threshold:
        return TrendDirection.IMPROVING, change_percent
    elif change_percent < -threshold:
        return TrendDirection.DECLINING, change_percent
    else:
        return TrendDirection.STABLE, change_percent


@router.get("/kpis", response_model=Dict[str, Any])
async def get_governance_kpis(
    tenant_id: Optional[str] = Query(
        default="default",
        description="Tenant identifier for multi-tenant deployments",
    ),
) -> Dict[str, Any]:
    """
    Get current governance KPIs for executive dashboard.

    Returns real-time compliance metrics including:
    - Overall compliance score (0-100)
    - Number of passing and failing controls
    - Recent audit count (last 30 days)
    - High-risk incident count
    - Trend direction (improving, stable, declining)
    - Data freshness warning if data is stale

    Executive and Compliance Officer roles have access to this endpoint.
    """
    try:
        # Calculate KPIs from ledger data
        kpi_data = await _calculate_kpis_from_ledger(tenant_id)

        # Calculate trend from historical data
        # For now, assume previous score was 85.0 for trend calculation
        previous_score = 85.0
        trend_direction, trend_change = await _calculate_trend(
            kpi_data["compliance_score"], previous_score
        )

        # Check data freshness
        data_stale = kpi_data.get("data_stale", False)
        last_updated = kpi_data.get("last_updated", datetime.now(timezone.utc))

        # Build KPIs response using the model
        kpis = GovernanceKPIs(
            tenant_id=tenant_id,
            compliance_score=kpi_data["compliance_score"],
            controls_passing=kpi_data["controls_passing"],
            controls_failing=kpi_data["controls_failing"],
            controls_total=kpi_data["controls_total"],
            recent_audits=kpi_data["recent_audits"],
            high_risk_incidents=kpi_data["high_risk_incidents"],
            trend_direction=trend_direction,
            trend_change_percent=round(trend_change, 2),
            last_updated=last_updated,
            data_stale_warning=data_stale,
        )

        return kpis.to_dict()

    except Exception as e:
        logger.error(f"Failed to calculate governance KPIs: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve governance KPIs. Please try again later.",
        ) from None


@router.get("/trends", response_model=Dict[str, Any])
async def get_governance_trends(
    days: int = Query(
        default=90,
        ge=1,
        le=365,
        description="Number of days of trend data to retrieve",
    ),
    tenant_id: Optional[str] = Query(
        default="default",
        description="Tenant identifier for multi-tenant deployments",
    ),
) -> Dict[str, Any]:
    """
    Get historical trend data for governance dashboard charts.

    Returns time-series data for specified period including:
    - Daily compliance scores
    - Control counts (passing/failing/total)
    - Period statistics (min, max, average)
    - Trend direction and slope

    Supports 30, 60, 90 day analysis periods.
    Executive and Compliance Officer roles have access to this endpoint.
    """
    try:
        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # TODO: Integrate with audit_ledger/metrics database for real data
        # For now, generate sample trend data for API verification
        data_points = []
        base_score = 82.0
        score_increment = 0.1  # Slight improvement trend

        for i in range(days):
            point_date = start_date + timedelta(days=i)
            # Simulate some variance in scores
            variance = (i % 7) * 0.3 - 1.0
            score = min(100.0, max(0.0, base_score + (i * score_increment) + variance))

            data_points.append(
                GovernanceTrendPoint(
                    date=point_date,
                    compliance_score=round(score, 2),
                    controls_passing=40 + (i // 10),
                    controls_failing=8 - (i // 15),
                    controls_total=48 + (i // 10) - (i // 15),
                    audit_count=i // 7,  # Roughly weekly audits
                )
            )

        # Calculate aggregate statistics
        scores = [dp.compliance_score for dp in data_points]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        min_score = min(scores) if scores else 0.0
        max_score = max(scores) if scores else 0.0

        # Calculate trend slope (simple linear approximation)
        if len(scores) >= 2:
            slope = (scores[-1] - scores[0]) / len(scores)
        else:
            slope = 0.0

        # Determine trend direction based on slope
        if slope > 0.05:
            trend_direction = TrendDirection.IMPROVING
        elif slope < -0.05:
            trend_direction = TrendDirection.DECLINING
        else:
            trend_direction = TrendDirection.STABLE

        # Build trends response using the model
        trends = GovernanceTrends(
            tenant_id=tenant_id,
            days=days,
            data_points=data_points,
            period_start=start_date,
            period_end=end_date,
            avg_compliance_score=round(avg_score, 2),
            min_compliance_score=round(min_score, 2),
            max_compliance_score=round(max_score, 2),
            trend_direction=trend_direction,
            trend_slope=round(slope, 4),
        )

        return trends.to_dict()

    except Exception as e:
        logger.error(f"Failed to calculate governance trends: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve governance trends. Please try again later.",
        ) from None


@router.get("/health", response_model=Dict[str, Any])
async def governance_health() -> Dict[str, Any]:
    """
    Health check for governance API.

    Returns service status and data availability information.
    """
    return {
        "status": "healthy",
        "api": "governance",
        "version": "1.0.0",
        "endpoints": ["/kpis", "/trends", "/health"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
