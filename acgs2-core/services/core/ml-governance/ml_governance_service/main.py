"""
ACGS-2 ML Governance Service
Adaptive ML models with feedback loops and drift detection
Constitutional Hash: cdd01ef066bc6cf2
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="ACGS-2 ML Governance Service",
    version="1.0.0",
    description="Adaptive ML models with feedback loops and drift detection",
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
