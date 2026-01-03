"""
ACGS-2 API Gateway
Simple development API gateway for routing requests to services
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.gzip import GZipMiddleware

from shared.config import settings
from shared.metrics import (
    create_metrics_endpoint,
    set_service_info,
    track_request_metrics,
    HTTP_REQUESTS_TOTAL,
    HTTP_REQUEST_DURATION,
)
from shared.logging import (
    init_service_logging,
    create_correlation_middleware,
    log_request_start,
    log_request_end,
    log_error,
    get_logger,
)
from shared.security.auth import (
    AuthenticationMiddleware,
    get_current_user_optional,
    UserClaims,
)
from shared.security.rate_limiter import (
    create_rate_limit_middleware,
    add_rate_limit_headers,
)

# Initialize structured logging
logger = init_service_logging("api-gateway")

app = FastAPI(
    title="ACGS-2 API Gateway",
    description="Development API Gateway for ACGS-2 services",
    version="1.0.0",
    default_response_class=ORJSONResponse,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.security.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add GZip middleware for response compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add correlation ID middleware
app.middleware("http")(create_correlation_middleware())

# Add rate limiting middleware
app.middleware("http")(
    create_rate_limit_middleware(
        requests_per_minute=100,  # 100 requests per minute
        burst_limit=20,  # Burst up to 20 requests
    )
)

# Add authentication middleware
app.add_middleware(AuthenticationMiddleware)

# Add rate limit headers
app.add_middleware(add_rate_limit_headers())

# Initialize metrics
set_service_info("api-gateway", "1.0.0")

# Add metrics endpoint
app.add_api_route("/metrics", create_metrics_endpoint())

# Service URLs from centralized config
AGENT_BUS_URL = settings.services.agent_bus_url
ENVIRONMENT = settings.env

# Feedback storage
FEEDBACK_DIR = Path("/tmp/feedback")  # In production, use proper database
FEEDBACK_DIR.mkdir(exist_ok=True)


# Feedback Models
class FeedbackRequest(BaseModel):
    """User feedback request model"""

    user_id: str = Field(..., description="User identifier")
    category: str = Field(..., description="Feedback category (bug, feature, general)")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    title: str = Field(..., description="Feedback title")
    description: str = Field(..., description="Detailed feedback description")
    user_agent: str = Field(default="", description="User agent string")
    url: str = Field(default="", description="Current URL when feedback was given")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


class FeedbackResponse(BaseModel):
    """Feedback submission response"""

    feedback_id: str
    status: str
    timestamp: str
    message: str


# Health check
@app.get("/health")
@track_request_metrics("api-gateway", "/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "api-gateway", "environment": ENVIRONMENT}


# User Feedback Collection
@app.post("/feedback", response_model=FeedbackResponse)
@track_request_metrics("api-gateway", "/feedback")
async def submit_feedback(
    feedback: FeedbackRequest, request: Request, background_tasks: BackgroundTasks
):
    """Submit user feedback for ACGS-2"""
    try:
        # Generate feedback ID
        import uuid

        feedback_id = str(uuid.uuid4())

        # Create feedback record
        feedback_record = {
            "feedback_id": feedback_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": feedback.user_id,
            "category": feedback.category,
            "rating": feedback.rating,
            "title": feedback.title,
            "description": feedback.description,
            "user_agent": feedback.user_agent or request.headers.get("user-agent", ""),
            "url": feedback.url,
            "ip_address": request.client.host if request.client else "unknown",
            "metadata": feedback.metadata,
            "environment": ENVIRONMENT,
        }

        # Save feedback asynchronously
        background_tasks.add_task(save_feedback_to_file, feedback_record)

        logger.info(f"Feedback submitted: {feedback_id} - {feedback.category}")

        return FeedbackResponse(
            feedback_id=feedback_id,
            status="submitted",
            timestamp=feedback_record["timestamp"],
            message="Thank you for your feedback! We'll review it shortly.",
        )

    except Exception as e:
        log_error(
            logger,
            e,
            context={"operation": "feedback_submission", "user_id": feedback.user_id},
            category=feedback.category,
        )
        raise HTTPException(status_code=500, detail="Failed to process feedback") from e


@app.get("/feedback/stats")
@track_request_metrics("api-gateway", "/feedback/stats")
async def get_feedback_stats(user: UserClaims = Depends(get_current_user_optional)):
    """Get feedback statistics (admin endpoint)"""
    try:
        # Log access for audit purposes
        if user:
            logger.info(
                "Feedback stats accessed",
                user_id=user.sub,
                tenant_id=user.tenant_id,
                roles=user.roles,
            )
        # Count feedback files
        feedback_files = list(FEEDBACK_DIR.glob("*.json"))
        total_feedback = len(feedback_files)

        # Basic stats
        categories = {}
        ratings = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

        for file_path in feedback_files[:100]:  # Limit to avoid performance issues
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    cat = data.get("category", "unknown")
                    rating = data.get("rating", 0)

                    categories[cat] = categories.get(cat, 0) + 1
                    if rating in ratings:
                        ratings[rating] += 1
            except Exception:
                continue

        return {
            "total_feedback": total_feedback,
            "categories": categories,
            "ratings": ratings,
            "average_rating": (
                sum(k * v for k, v in ratings.items()) / sum(ratings.values())
                if sum(ratings.values()) > 0
                else 0
            ),
        }

    except Exception as e:
        logger.error(f"Error getting feedback stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve feedback statistics") from e


# Service discovery endpoint
@app.get("/services")
@track_request_metrics("api-gateway", "/services")
async def list_services():
    """List available services"""
    services = {
        "agent-bus": {"url": AGENT_BUS_URL, "status": "configured"},
        "api-gateway": {"url": "http://localhost:8080", "status": "running"},
    }

    # Check service health
    for service_name, service_info in services.items():
        if service_name != "api-gateway":
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{service_info['url']}/health")
                    service_info["health"] = (
                        "healthy" if response.status_code == 200 else "unhealthy"
                    )
            except (httpx.RequestError, httpx.TimeoutException, Exception) as e:
                logger.warning(f"Health check failed for {service_name}: {e}")
                service_info["health"] = "unreachable"

    return services


# Proxy to Agent Bus (catch-all route - must be last)
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_to_agent_bus(request: Request, path: str):
    """Proxy requests to the Agent Bus service"""

    # Construct target URL
    target_url = f"{AGENT_BUS_URL}/{path}"

    # Add query parameters
    if request.url.query:
        target_url += f"?{request.url.query}"

    import time

    start_time = time.perf_counter()
    status_code = 200

    try:
        # Get request body
        body = await request.body()

        # Forward the request
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=dict(request.headers),
                content=body,
                params=request.query_params,
            )

            status_code = response.status_code

            # Return the response
            return ORJSONResponse(
                status_code=response.status_code,
                content=(
                    response.json()
                    if response.headers.get("content-type", "").startswith("application/json")
                    else response.text
                ),
            )

    except httpx.RequestError as e:
        logger.error(f"Request error: {e}")
        status_code = 502
        raise HTTPException(status_code=502, detail="Service unavailable") from e
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        status_code = 500
        raise HTTPException(status_code=500, detail="Internal server error") from e
    finally:
        # Track proxy request metrics
        duration = time.perf_counter() - start_time
        HTTP_REQUEST_DURATION.labels(
            method=request.method, endpoint=f"/proxy/{path}", service="api-gateway"
        ).observe(duration)
        HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            endpoint=f"/proxy/{path}",
            service="api-gateway",
            status=str(status_code),
        ).inc()


async def save_feedback_to_file(feedback_record: dict):
    """Save feedback to file asynchronously"""
    try:
        feedback_id = feedback_record["feedback_id"]
        file_path = FEEDBACK_DIR / f"{feedback_id}.json"

        with open(file_path, "w") as f:
            json.dump(feedback_record, f, indent=2)

        logger.info(f"Feedback saved: {feedback_id}")
    except Exception as e:
        logger.error(f"Error saving feedback {feedback_record.get('feedback_id')}: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True, log_level="info")
