#!/usr/bin/env python3
"""
ACGS-2 Tenant Management Service
Constitutional Hash: cdd01ef066bc6cf2

A dedicated service for multi-tenant isolation, resource management,
and access control in the ACGS-2 platform.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from src.core.shared.acgs_logging import create_correlation_middleware, init_service_logging
from src.core.shared.metrics import create_metrics_endpoint, set_service_info, track_request_metrics
from src.core.shared.security.cors_config import get_cors_config

from .api import router
from .service import TenantManagementService

# Initialize structured logging
logger = init_service_logging("tenant-management")

# Create FastAPI application
app = FastAPI(
    title="ACGS-2 Tenant Management Service",
    description="Multi-tenant isolation and resource management for ACGS-2",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add middleware with secure CORS configuration from shared module
app.add_middleware(CORSMiddleware, **get_cors_config())

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"],  # In production, specify allowed hosts
)

# Add correlation ID middleware
app.middleware("http")(create_correlation_middleware())

# Initialize metrics
set_service_info("tenant-management", "2.0.0")

# Add metrics endpoint
app.add_api_route("/metrics", create_metrics_endpoint())

# Initialize service
tenant_service = TenantManagementService()

# Add service to app state for dependency injection
app.state.tenant_service = tenant_service

# Include API routes
app.include_router(router)


@app.on_event("startup")
async def startup_event():
    """Service startup event"""
    logger.info("🚀 Starting ACGS-2 Tenant Management Service")
    logger.info("Constitutional Hash: cdd01ef066bc6cf2")


@app.on_event("shutdown")
async def shutdown_event():
    """Service shutdown event"""
    logger.info("🛑 Shutting down ACGS-2 Tenant Management Service")


@app.get("/")
@track_request_metrics("tenant-management", "/")
async def root():
    """Root endpoint"""
    return {
        "service": "ACGS-2 Tenant Management",
        "version": "2.0.0",
        "constitutional_hash": "cdd01ef066bc6cf2",
        "docs": "/docs",
    }


@app.get("/health")
@track_request_metrics("tenant-management", "/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "tenant-management",
        "version": "2.0.0",
        "constitutional_hash": "cdd01ef066bc6cf2",
    }


if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8500,  # Tenant Management service port
        reload=True,
        log_level="info",
    )
