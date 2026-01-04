"""
ACGS-2 Integration Service
Third-party integration ecosystem for enterprise tool connectivity
"""

import logging
import os
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.health import configure_health_router
from .api.health import router as health_router
from .api.import_router import router as import_router
from .api.linear import router as linear_router
from .api.linear_webhooks import router as linear_webhooks_router
from .api.policy_check import router as policy_check_router
from .api.webhooks import router as webhooks_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment configuration
ENVIRONMENT = os.getenv("APP_ENV", "development")
SERVICE_NAME = "integration-service"
SERVICE_VERSION = "1.0.0"
SERVICE_PORT = int(os.getenv("INTEGRATION_SERVICE_PORT", "8100"))

# Service URLs from environment
AGENT_BUS_URL = os.getenv("AGENT_BUS_URL", "http://localhost:8000")
OPA_URL = os.getenv("OPA_URL", "http://localhost:8181")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

# CORS configuration - environment-aware security
def get_cors_origins() -> list[str]:
    """
    Get CORS origins with environment-aware security defaults.

    Development: Uses localhost origins
    Production/Staging: Requires explicit CORS_ORIGINS env var, no wildcards allowed

    Returns:
        List of allowed CORS origins

    Raises:
        ValueError: If production environment uses wildcard or missing CORS_ORIGINS
    """
    cors_env_var = os.getenv("CORS_ORIGINS")

    # Development environment defaults
    if ENVIRONMENT.lower() in ("development", "dev"):
        default_origins = (
            "http://localhost:3000,http://localhost:8080,http://localhost:5173,"
            "http://127.0.0.1:3000,http://127.0.0.1:8080,http://127.0.0.1:5173"
        )
        origins_str = cors_env_var or default_origins
    else:
        # Production/Staging: require explicit configuration
        if not cors_env_var:
            raise ValueError(
                f"SECURITY ERROR: CORS_ORIGINS environment variable must be "
                f"explicitly set in {ENVIRONMENT} environment. "
                "Wildcard origins are not allowed in production."
            )
        origins_str = cors_env_var

    # Parse and validate origins
    origins = [
        origin.strip()
        for origin in origins_str.split(",")
        if origin.strip()
    ]

    # Production wildcard validation
    if ENVIRONMENT.lower() in ("production", "prod", "staging", "stage"):
        if "*" in origins:
            raise ValueError(
                f"SECURITY ERROR: Wildcard CORS origins not allowed in "
                f"{ENVIRONMENT} environment. This is a critical security "
                "vulnerability. Specify explicit allowed origins."
            )
        # Validate HTTPS in production
        for origin in origins:
            is_production = ENVIRONMENT.lower() in ("production", "prod")
            if is_production and not origin.startswith("https://"):
                logger.warning(
                    f"WARNING: Non-HTTPS origin '{origin}' in production "
                    "environment. This may pose security risks."
                )

    logger.info(
        f"CORS configured for {ENVIRONMENT}: {len(origins)} origins allowed"
    )
    return origins


CORS_ORIGINS = get_cors_origins()

# Redis client for job tracking
redis_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global redis_client

    # Startup
    logger.info(f"Starting {SERVICE_NAME} v{SERVICE_VERSION}")
    logger.info(f"Environment: {ENVIRONMENT}")
    logger.info(f"Agent Bus URL: {AGENT_BUS_URL}")
    logger.info(f"OPA URL: {OPA_URL}")
    logger.info(f"Listening on port {SERVICE_PORT}")

    # Configure health router with service settings
    configure_health_router(
        service_name=SERVICE_NAME,
        service_version=SERVICE_VERSION,
        environment=ENVIRONMENT,
        service_port=SERVICE_PORT,
        agent_bus_url=AGENT_BUS_URL,
        opa_url=OPA_URL,
    )

    # Initialize Redis for job tracking
    try:
        redis_client = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        await redis_client.ping()
        logger.info(f"Redis connected for job tracking: {REDIS_URL}")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Job tracking will use in-memory storage.")
        redis_client = None

    yield

    # Shutdown
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")
    logger.info(f"Shutting down {SERVICE_NAME}")


app = FastAPI(
    title="ACGS-2 Integration Service",
    description="Third-party integration ecosystem for connecting ACGS-2 with enterprise tools",
    version=SERVICE_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(import_router)
app.include_router(policy_check_router)
app.include_router(webhooks_router)
app.include_router(linear_router)
app.include_router(linear_webhooks_router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "description": "ACGS-2 Third-Party Integration Service",
        "documentation": "/docs",
        "health": "/health",
        "environment": ENVIRONMENT,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=SERVICE_PORT,
        reload=True,
        log_level="info",
    )
