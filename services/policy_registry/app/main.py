"""
Policy Registry Service - Main FastAPI Application
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .services import CryptoService, CacheService, NotificationService, PolicyService
from shared.audit_client import AuditClient

# Import secure CORS configuration
try:
    from shared.security.cors_config import get_cors_config
    SECURE_CORS_AVAILABLE = True
except ImportError:
    SECURE_CORS_AVAILABLE = False

# Import rate limiting middleware
try:
    from shared.security.rate_limiter import RateLimitMiddleware, RateLimitConfig
    RATE_LIMIT_AVAILABLE = True
except ImportError:
    RATE_LIMIT_AVAILABLE = False
from .api.v1 import router as v1_router

# Centralized settings
try:
    from shared.config import settings
except ImportError:
    # Fallback if shared not in path
    from ...shared.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global service instances
crypto_service = CryptoService()
cache_service = CacheService()
notification_service = NotificationService()
audit_client = AuditClient(service_url=settings.audit.url)
policy_service = PolicyService(
    crypto_service, 
    cache_service, 
    notification_service,
    audit_client=audit_client
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Policy Registry Service")
    
    await cache_service.initialize()
    await notification_service.initialize()
    
    logger.info("Policy Registry Service started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Policy Registry Service")
    
    await notification_service.shutdown()
    await cache_service.close()
    
    logger.info("Policy Registry Service stopped")


# Create FastAPI app
app = FastAPI(
    title="Policy Registry Service",
    description="Dynamic Constitution Policy Management with Ed25519 Signatures",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware with secure configuration
if SECURE_CORS_AVAILABLE:
    # Use secure CORS configuration from shared module
    cors_config = get_cors_config()
    logger.info(f"Using secure CORS configuration with {len(cors_config.get('allow_origins', []))} origins")
else:
    # Fallback to settings-based configuration
    cors_config = {
        "allow_origins": settings.security.cors_origins,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        "allow_headers": ["Authorization", "Content-Type", "X-Request-ID", "X-Constitutional-Hash"],
    }
    logger.warning("Using fallback CORS configuration - shared.security module not available")

app.add_middleware(CORSMiddleware, **cors_config)

# Add Rate Limiting middleware
if RATE_LIMIT_AVAILABLE:
    rate_limit_config = RateLimitConfig.from_env()
    if rate_limit_config.enabled:
        app.add_middleware(RateLimitMiddleware, config=rate_limit_config)
        logger.info(
            f"Rate limiting enabled with {len(rate_limit_config.rules)} rules"
        )
    else:
        logger.info("Rate limiting is disabled via configuration")
else:
    logger.warning("Rate limiting not available - shared.security.rate_limiter not found")


@app.middleware("http")
async def internal_auth_middleware(request, call_next):
    """Check for internal API key if configured"""
    internal_key = settings.security.api_key_internal
    if internal_key:
        # Get key from header
        provided_key = request.headers.get("X-Internal-API-Key")
        if provided_key != internal_key.get_secret_value():
            # Only restrict certain paths or all? Let's restrict /api/v1 for now
            if request.url.path.startswith("/api/v1"):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Unauthorized: Invalid internal API key"}
                )
    
    return await call_next(request)


# Dependency injection
def get_policy_service() -> PolicyService:
    """Get policy service instance"""
    return policy_service


def get_crypto_service() -> CryptoService:
    """Get crypto service instance"""
    return crypto_service


def get_cache_service() -> CacheService:
    """Get cache service instance"""
    return cache_service


def get_notification_service() -> NotificationService:
    """Get notification service instance"""
    return notification_service


# Include API routers
app.include_router(v1_router, prefix="/api/v1")


# Health check endpoints
@app.get("/health/live", response_model=Dict[str, Any])
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive", "service": "policy-registry"}


@app.get("/health/ready", response_model=Dict[str, Any])
async def readiness_check(
    cache_svc: CacheService = Depends(get_cache_service),
    notification_svc: NotificationService = Depends(get_notification_service)
):
    """Kubernetes readiness probe"""
    cache_stats = await cache_svc.get_cache_stats()
    connection_stats = await notification_svc.get_connection_count()
    
    return {
        "status": "ready",
        "service": "policy-registry",
        "cache": cache_stats,
        "connections": connection_stats
    }


@app.get("/health/details", response_model=Dict[str, Any])
async def detailed_health_check(
    policy_svc: PolicyService = Depends(get_policy_service),
    cache_svc: CacheService = Depends(get_cache_service),
    notification_svc: NotificationService = Depends(get_notification_service)
):
    """Detailed health check for monitoring"""
    policies = await policy_svc.list_policies()
    
    return {
        "status": "healthy",
        "service": "policy-registry",
        "policies_count": len(policies),
        "cache_stats": await cache_svc.get_cache_stats(),
        "connection_stats": await notification_svc.get_connection_count()
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
