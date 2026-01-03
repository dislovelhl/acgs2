"""
ML Governance Service - Main Application
"""

import logging

from fastapi import FastAPI
from src.api.router import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}',
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ACGS-2 ML Governance Service",
    description="ML-powered adaptive governance and impact scoring",
    version="1.0.0",
)

# Include API router
app.include_router(router)


@app.get("/")
async def root():
    return {
        "service": "ml-governance-service",
        "status": "running",
        "endpoints": ["/predict", "/feedback", "/health"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8100)
