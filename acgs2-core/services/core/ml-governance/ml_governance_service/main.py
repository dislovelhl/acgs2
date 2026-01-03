"""
ACGS-2 ML Governance Service
Adaptive ML models with feedback loops and drift detection
Constitutional Hash: cdd01ef066bc6cf2
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

app = FastAPI(
    title="ACGS-2 ML Governance Service",
    version="1.0.0",
    description="Adaptive ML models with feedback loops and drift detection",
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

# Middleware with secure CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ml-governance"}


@app.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe"""
    return {"status": "ready"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "ACGS-2 ML Governance Service", "version": "1.0.0"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8400)
