"""
ACGS-2 Adaptive Learning Engine - Main Application
Constitutional Hash: cdd01ef066bc6cf2

FastAPI application for the Adaptive Learning Engine with real-time online learning,
drift detection, model versioning, and safety bounds checking.

Entry Point:
    poetry run uvicorn src.main:app --reload --port 8001

API Documentation:
    http://localhost:8001/docs (Swagger UI)
    http://localhost:8001/redoc (ReDoc)
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.endpoints import initialize_services, router
from src.config import AdaptiveLearningConfig
from src.models.model_manager import ModelManager
from src.models.online_learner import OnlineLearner
from src.monitoring.drift_detector import DriftDetector
from src.monitoring.metrics import MetricsRegistry, get_metrics_registry
from src.safety.bounds_checker import SafetyBoundsChecker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Environment configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "development"))

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
    origins = [origin.strip() for origin in origins_str.split(",") if origin.strip()]

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

    logger.info(f"CORS configured for {ENVIRONMENT}: {len(origins)} origins allowed")
    return origins

# Global state for service instances
_model_manager: Optional[ModelManager] = None
_drift_detector: Optional[DriftDetector] = None
_safety_checker: Optional[SafetyBoundsChecker] = None
_metrics_registry: Optional[MetricsRegistry] = None
_config: Optional[AdaptiveLearningConfig] = None
_drift_check_task: Optional[asyncio.Task] = None

async def _start_drift_check_loop(
    detector: DriftDetector,
    interval_seconds: int,
) -> None:
    """Background task for periodic drift checking.

    Args:
        detector: The DriftDetector instance.
        interval_seconds: Interval between drift checks in seconds.
    """
    logger.info(f"Starting drift check loop (interval: {interval_seconds}s)")
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            if detector.is_enabled():
                result = await detector.check_drift_async()
                if result.drift_detected:
                    logger.warning(
                        f"Drift detected! Score: {result.drift_score:.4f}, "
                        f"Threshold: {result.drift_threshold:.4f}"
                    )
                else:

        except asyncio.CancelledError:
            logger.info("Drift check loop cancelled")
            break
        except Exception as e:
            logger.error(f"Error in drift check loop: {e}", exc_info=True)
            # Continue loop despite errors - graceful degradation

async def _initialize_services(config: AdaptiveLearningConfig) -> None:
    """Initialize all service components.

    Args:
        config: The application configuration.
    """
    global _model_manager, _drift_detector, _safety_checker, _metrics_registry, _drift_check_task

    logger.info("Initializing Adaptive Learning Engine services...")

    # Initialize metrics registry first (for dependency injection)
    _metrics_registry = get_metrics_registry()
    logger.info("Metrics registry initialized")

    # Initialize online learner
    online_learner = OnlineLearner(
        min_samples_for_active=config.min_training_samples,
    )
    logger.info("Online learner created")

    # Initialize model manager with the online learner
    _model_manager = ModelManager(initial_model=online_learner)
    logger.info("Model manager initialized")

    # Initialize drift detector
    _drift_detector = DriftDetector(
        drift_threshold=config.drift_threshold,
        min_samples_for_drift=config.min_predictions_for_drift,
        reference_window_size=config.drift_window_size,
        current_window_size=config.drift_window_size,
    )
    if not config.enable_drift_detection:
        _drift_detector.disable()
        logger.info("Drift detection disabled by configuration")
    else:
        logger.info("Drift detector initialized")

    # Initialize safety bounds checker
    _safety_checker = SafetyBoundsChecker(
        accuracy_threshold=config.safety_accuracy_threshold,
        consecutive_failures_limit=config.safety_consecutive_failures_limit,
    )
    if not config.enable_safety_bounds:
        # Safety bounds are always initialized but we log the config status
        logger.info("Safety bounds initialized (disabled by configuration)")
    else:
        logger.info("Safety bounds checker initialized")

    # Initialize endpoint services (inject dependencies)
    initialize_services(
        model_manager=_model_manager,
        drift_detector=_drift_detector,
        safety_checker=_safety_checker,
        metrics_registry=_metrics_registry,
    )
    logger.info("Endpoint services initialized with dependencies")

    # Start background drift check loop if enabled
    if config.enable_drift_detection:
        _drift_check_task = asyncio.create_task(
            _start_drift_check_loop(
                detector=_drift_detector,
                interval_seconds=config.drift_check_interval_seconds,
            )
        )
        logger.info("Background drift check loop started")

    # Update service info metrics
    _metrics_registry.set_service_info(
        service_name="adaptive-learning-engine",
        version="1.0.0",
        constitutional_hash=config.constitutional_hash,
    )

    logger.info("Adaptive Learning Engine initialization complete")

async def _shutdown_services() -> None:
    """Clean up all service components."""
    global _drift_check_task

    logger.info("Shutting down Adaptive Learning Engine services...")

    # Cancel drift check loop
    if _drift_check_task is not None and not _drift_check_task.done():
        _drift_check_task.cancel()
        try:
            await _drift_check_task
        except asyncio.CancelledError:
            pass
        logger.info("Drift check loop stopped")

    # Log final metrics
    if _metrics_registry is not None:
        snapshot = _metrics_registry.get_snapshot()
        logger.info(
            f"Final metrics - Predictions: {snapshot.predictions_total}, "
            f"Training samples: {snapshot.training_samples_total}, "
            f"Errors: {snapshot.errors_total}"
        )

    logger.info("Adaptive Learning Engine shutdown complete")

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown events.

    This replaces the deprecated @app.on_event decorators.
    """
    global _config

    # Startup
    try:
        _config = AdaptiveLearningConfig.from_environment()
        logger.info(f"Configuration loaded: {_config.to_dict()}")

        await _initialize_services(_config)
        logger.info("Adaptive Learning Engine started successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Adaptive Learning Engine: {e}")
        raise

    yield

    # Shutdown
    await _shutdown_services()

# Create FastAPI application
app = FastAPI(
    title="Adaptive Learning Engine",
    description=(
        "ACGS-2 Adaptive Learning Engine API for real-time online learning, "
        "drift detection, model versioning, and safety bounds checking. "
        "Provides ML-enhanced governance decisions with zero-downtime model updates."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add CORS middleware with environment-aware security
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the API router
app.include_router(router)

# For running with uvicorn directly
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info",
    )
