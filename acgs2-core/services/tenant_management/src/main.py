#!/usr/bin/env python3
"""
ACGS-2 Tenant Management Service
Constitutional Hash: cdd01ef066bc6cf2

A dedicated service for multi-tenant isolation, resource management,
and access control in the ACGS-2 platform.
"""

import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from shared.logging import (
    create_correlation_middleware,
    init_service_logging,
)
from shared.metrics import (
    create_metrics_endpoint,
    set_service_info,
    track_request_metrics,
)

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

# Configure CORS based on environment for security
cors_origins = os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
if not cors_origins or cors_origins == [""]:
    # Default secure configuration - no external origins allowed
    cors_origins = []

# Allow localhost for development (but not in production)
if os.getenv("ENVIRONMENT", "").lower() == "development":
    cors_origins.extend(
        [
            "http://localhost:3000",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080",
        ]
    )

# Add middleware with secure CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
)

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
