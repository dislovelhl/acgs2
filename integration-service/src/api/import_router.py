"""
Import API endpoints for managing data import operations.

Provides endpoints for previewing, executing, and monitoring data imports
from external sources like JIRA, ServiceNow, GitHub, and GitLab.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..models.import_models import (
    ImportListResponse,
    ImportRequest,
    ImportResponse,
    ImportStatus,
    PreviewResponse,
    SourceConfig,
    SourceType,
)

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/imports", tags=["Imports"])


# In-memory storage for import jobs (for development)
# In production, this would be replaced with a database repository
_import_jobs: Dict[str, ImportResponse] = {}


# Dependency for getting import storage
def get_import_storage() -> Dict[str, ImportResponse]:
    """Get import job storage."""
    return _import_jobs


# Request/Response models for test connection
class TestConnectionRequest(BaseModel):
    """Request to test connection to an external source."""

    source: SourceType = Field(..., description="Type of source to connect to")
    source_config: SourceConfig = Field(..., description="Connection configuration")


class TestConnectionResponse(BaseModel):
    """Response from test connection attempt."""

    success: bool = Field(..., description="Whether connection was successful")
    message: str = Field(..., description="Success or error message")
    source_name: Optional[str] = Field(None, description="Name/identifier from the source")


# API Endpoints
@router.post(
    "/test-connection",
    response_model=TestConnectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Test connection to external source",
    description="Verify credentials and connectivity to an external data source",
)
async def test_connection(
    request: TestConnectionRequest,
) -> TestConnectionResponse:
    """
    Test connection to an external source.

    This endpoint verifies that the provided credentials can successfully
    authenticate with the external source. It does not fetch or modify any data.
    """
    try:
        logger.info(f"Testing connection to source_type={request.source}")

        # Import service modules dynamically to avoid circular imports
        if request.source == SourceType.JIRA:
            from ..services.jira_import_service import create_jira_import_service

            # Create import service
            try:
                service = await create_jira_import_service(request.source_config)
            except ValueError as e:
                logger.warning(f"JIRA configuration validation failed: {e}")
                return TestConnectionResponse(
                    success=False,
                    message=str(e),
                    source_name=None,
                )

            success, error_msg = await service.test_connection()

            if success:
                logger.info("JIRA connection test successful")
                return TestConnectionResponse(
                    success=True,
                    message="Connection successful",
                    source_name=f"JIRA ({request.source_config.base_url})",
                )
            else:
                logger.warning(f"JIRA connection test failed: {error_msg}")
                return TestConnectionResponse(
                    success=False,
                    message=error_msg or "Connection failed",
                    source_name=None,
                )

        elif request.source == SourceType.SERVICENOW:
            from ..services.servicenow_import_service import create_servicenow_import_service

            try:
                service = await create_servicenow_import_service(request.source_config)
            except ValueError as e:
                logger.warning(f"ServiceNow configuration validation failed: {e}")
                return TestConnectionResponse(
                    success=False,
                    message=str(e),
                    source_name=None,
                )

            success, error_msg = await service.test_connection()

            if success:
                logger.info("ServiceNow connection test successful")
                return TestConnectionResponse(
                    success=True,
                    message="Connection successful",
                    source_name=f"ServiceNow ({request.source_config.instance})",
                )
            else:
                logger.warning(f"ServiceNow connection test failed: {error_msg}")
                return TestConnectionResponse(
                    success=False,
                    message=error_msg or "Connection failed",
                    source_name=None,
                )

        elif request.source == SourceType.GITHUB:
            from ..services.github_import_service import create_github_import_service

            try:
                service = await create_github_import_service(request.source_config)
            except ValueError as e:
                logger.warning(f"GitHub configuration validation failed: {e}")
                return TestConnectionResponse(
                    success=False,
                    message=str(e),
                    source_name=None,
                )

            success, error_msg = await service.test_connection()

            if success:
                logger.info("GitHub connection test successful")
                return TestConnectionResponse(
                    success=True,
                    message="Connection successful",
                    source_name="GitHub",
                )
            else:
                logger.warning(f"GitHub connection test failed: {error_msg}")
                return TestConnectionResponse(
                    success=False,
                    message=error_msg or "Connection failed",
                    source_name=None,
                )

        elif request.source == SourceType.GITLAB:
            from ..services.gitlab_import_service import create_gitlab_import_service

            try:
                service = await create_gitlab_import_service(request.source_config)
            except ValueError as e:
                logger.warning(f"GitLab configuration validation failed: {e}")
                return TestConnectionResponse(
                    success=False,
                    message=str(e),
                    source_name=None,
                )

            success, error_msg = await service.test_connection()

            if success:
                logger.info("GitLab connection test successful")
                return TestConnectionResponse(
                    success=True,
                    message="Connection successful",
                    source_name=f"GitLab ({request.source_config.base_url})",
                )
            else:
                logger.warning(f"GitLab connection test failed: {error_msg}")
                return TestConnectionResponse(
                    success=False,
                    message=error_msg or "Connection failed",
                    source_name=None,
                )

        else:
            raise ValueError(f"Unsupported source type: {request.source}")

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None
    except Exception as e:
        logger.exception(f"Error testing connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Connection test failed. Please verify your configuration and try again.",
        ) from None


@router.post(
    "/preview",
    response_model=PreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview data import",
    description="Preview what data would be imported without committing changes",
)
async def preview_import(
    request: ImportRequest,
) -> PreviewResponse:
    """
    Preview data from an external source before importing.

    This endpoint connects to the specified external source and retrieves
    a sample of items that would be imported based on the provided filters.
    No data is committed to the system.
    """
    try:
        logger.info(
            f"Preview requested for source_type={request.source_type}, "
            f"request_id={request.id}"
        )

        # TODO: Integrate with actual import services based on source_type
        # For now, return mock preview data

        preview = PreviewResponse(
            source_type=request.source_type,
            total_available=0,
            preview_items=[],
            preview_count=0,
            source_name=f"Mock {request.source_type.value} Source",
            item_type_counts={},
            status_counts={},
            warnings=["Preview functionality is under development"],
        )

        logger.info(
            f"Preview completed for request_id={request.id}, "
            f"found {preview.total_available} items"
        )

        return preview

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None
    except Exception as e:
        logger.exception(f"Error previewing import: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Preview failed. Please verify your configuration and try again.",
        ) from None


@router.post(
    "",
    response_model=ImportResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Execute data import",
    description="Start an asynchronous data import operation from an external source",
)
async def execute_import(
    request: ImportRequest,
    storage: Dict[str, ImportResponse] = Depends(get_import_storage),
) -> ImportResponse:
    """
    Execute a data import from an external source.

    This endpoint initiates an asynchronous import job. The job status
    can be monitored using the GET /api/imports/{job_id} endpoint.
    """
    try:
        # Create import job
        job_id = str(uuid4())
        job = ImportResponse(
            job_id=job_id,
            request_id=request.id,
            status=ImportStatus.PENDING,
            source_type=request.source_type,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            tenant_id=request.tenant_id,
            correlation_id=request.correlation_id,
        )

        # Store job
        storage[job_id] = job

        logger.info(
            f"Import job created: job_id={job_id}, "
            f"source_type={request.source_type}, "
            f"request_id={request.id}"
        )

        # TODO: Queue job for background processing
        # For now, job remains in PENDING state

        return job

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None
    except Exception as e:
        logger.exception(f"Error executing import: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Import execution failed. Please verify your request and try again.",
        ) from None


@router.get(
    "/{job_id}",
    response_model=ImportResponse,
    summary="Get import job status",
    description="Get the status and progress of a specific import job",
)
async def get_import_status(
    job_id: str,
    storage: Dict[str, ImportResponse] = Depends(get_import_storage),
) -> ImportResponse:
    """Get the status and progress of an import job."""
    job = storage.get(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Import job not found: {job_id}",
        )

    logger.debug(f"Retrieved status for job_id={job_id}, status={job.status}")

    return job


@router.get(
    "",
    response_model=ImportListResponse,
    summary="List import jobs",
    description="List all import jobs with optional filtering",
)
async def list_imports(
    source_type: Optional[SourceType] = Query(None, description="Filter by source type"),
    status_filter: Optional[ImportStatus] = Query(None, description="Filter by status"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of jobs to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    storage: Dict[str, ImportResponse] = Depends(get_import_storage),
) -> ImportListResponse:
    """
    List all import jobs.

    Supports filtering by source type, status, and tenant ID.
    Results are paginated and sorted by creation time (newest first).
    """
    # Filter jobs
    jobs = list(storage.values())

    if source_type:
        jobs = [j for j in jobs if j.source_type == source_type]

    if status_filter:
        jobs = [j for j in jobs if j.status == status_filter]

    if tenant_id:
        jobs = [j for j in jobs if j.tenant_id == tenant_id]

    # Sort by creation time (newest first)
    jobs.sort(key=lambda j: j.created_at, reverse=True)

    # Paginate
    total = len(jobs)
    paginated_jobs = jobs[offset : offset + limit]

    logger.debug(
        f"Listed {len(paginated_jobs)} jobs (total={total}, "
        f"limit={limit}, offset={offset})"
    )

    return ImportListResponse(
        jobs=paginated_jobs,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel import job",
    description="Cancel a pending or running import job",
)
async def cancel_import(
    job_id: str,
    storage: Dict[str, ImportResponse] = Depends(get_import_storage),
) -> None:
    """
    Cancel an import job.

    Only jobs in PENDING or PROCESSING status can be cancelled.
    Completed or failed jobs cannot be cancelled.
    """
    job = storage.get(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Import job not found: {job_id}",
        )

    # Check if job can be cancelled
    if job.status in (ImportStatus.COMPLETED, ImportStatus.FAILED, ImportStatus.CANCELLED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job in {job.status} status",
        )

    # Update job status
    job.status = ImportStatus.CANCELLED
    job.updated_at = datetime.now(timezone.utc)
    job.completed_at = datetime.now(timezone.utc)

    logger.info(f"Cancelled import job: {job_id}")
