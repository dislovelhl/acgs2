"""
ACGS-2 Integration Service
Third-party integration ecosystem for enterprise tool connectivity
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.health import configure_health_router
from .api.health import router as health_router
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

# CORS configuration
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
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

    yield

    # Shutdown
    logger.info(f"Shutting down {SERVICE_NAME}")


app = FastAPI(
    title="ACGS-2 Integration Service",
    description="Third-party integration ecosystem for connecting ACGS-2 with enterprise tools",
    version=SERVICE_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    # OpenAPI security scheme configuration
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True,
    },
    openapi_tags=[
        {
            "name": "Health",
            "description": "Health check endpoints for service monitoring",
        },
        {
            "name": "Policy Validation",
            "description": (
                "Policy validation endpoints for CI/CD integration. "
                "**Requires JWT authentication.**"
            ),
        },
        {
            "name": "Webhooks",
            "description": "Webhook management endpoints for event notifications",
        },
    ],
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Customize OpenAPI schema to include security scheme
def custom_openapi():
    """Customize OpenAPI schema with security definitions."""
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )

    # Add security scheme for JWT Bearer authentication
    openapi_schema["components"] = openapi_schema.get("components", {})
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "JWT authentication token. "
                "Include the token in the Authorization header as: `Bearer <token>`"
            ),
        }
    }

    # Add security requirement to all policy validation endpoints
    for path, path_item in openapi_schema.get("paths", {}).items():
        if path.startswith("/api/policy"):
            for operation in path_item.values():
                # Check if this is an operation dict (not tags, summary, etc.)
                is_operation = isinstance(operation, dict) and (
                    "parameters" in operation
                    or "requestBody" in operation
                    or "responses" in operation
                )
                if is_operation:
                    # Add security requirement
                    operation["security"] = [{"BearerAuth": []}]

                    # Add 401 response if not present
                    operation.setdefault("responses", {})
                    if "401" not in operation["responses"]:
                        operation["responses"]["401"] = {
                            "description": "Unauthorized - Invalid or missing authentication token",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "detail": {
                                                "type": "string",
                                                "example": "Authentication required"
                                            }
                                        }
                                    }
                                }
                            }
                        }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Include routers
app.include_router(health_router)
app.include_router(policy_check_router)
app.include_router(webhooks_router)


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
