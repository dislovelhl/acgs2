"""Constitutional Hash: cdd01ef066bc6cf2
Temporary File Cleanup Module for Compliance Documentation Service

Provides background cleanup of temporary files generated during report export.
Files older than COMPLIANCE_CLEANUP_INTERVAL (default: 3600 seconds) are deleted
to prevent disk space bloat.

Security requirement: Clean up temporary files within 1 hour of generation.
"""

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Configuration from environment variables
COMPLIANCE_OUTPUT_PATH = os.getenv("COMPLIANCE_OUTPUT_PATH", "/tmp/compliance-reports")
COMPLIANCE_CLEANUP_INTERVAL = int(os.getenv("COMPLIANCE_CLEANUP_INTERVAL", "3600"))

# How often to run the cleanup check (in seconds)
CLEANUP_CHECK_INTERVAL = int(os.getenv("CLEANUP_CHECK_INTERVAL", "300"))  # 5 minutes


def cleanup_old_files(
    directory: Optional[str] = None,
    max_age_seconds: Optional[int] = None,
) -> dict[str, int]:
    """
    Delete files older than the specified age from the given directory.

    This function is safe to call multiple times concurrently.
    It handles permission errors and missing directories gracefully.

    Args:
        directory: Path to the directory containing temporary files.
                   Defaults to COMPLIANCE_OUTPUT_PATH.
        max_age_seconds: Maximum age of files to keep in seconds.
                         Files older than this will be deleted.
                         Defaults to COMPLIANCE_CLEANUP_INTERVAL.

    Returns:
        dict with cleanup statistics:
        - files_deleted: Number of files successfully deleted
        - files_failed: Number of files that failed to delete
        - bytes_freed: Approximate bytes freed
        - errors: List of error messages (if any)

    Example:
        >>> result = cleanup_old_files()
        >>> print(f"Deleted {result['files_deleted']} files, freed {result['bytes_freed']} bytes")
    """
    if directory is None:
        directory = COMPLIANCE_OUTPUT_PATH

    if max_age_seconds is None:
        max_age_seconds = COMPLIANCE_CLEANUP_INTERVAL

    result = {
        "files_deleted": 0,
        "files_failed": 0,
        "bytes_freed": 0,
        "errors": [],
    }

    dir_path = Path(directory)

    # Create directory if it doesn't exist (nothing to clean up)
    if not dir_path.exists():
        logger.debug(f"Cleanup directory does not exist: {directory}")
        return result

    if not dir_path.is_dir():
        error_msg = f"Cleanup path is not a directory: {directory}"
        logger.error(error_msg)
        result["errors"].append(error_msg)
        return result

    current_time = time.time()
    cutoff_time = current_time - max_age_seconds

    logger.debug(
        f"Running cleanup for files older than {max_age_seconds}s "
        f"in {directory}"
    )

    try:
        for file_path in dir_path.iterdir():
            if file_path.is_file():
                try:
                    file_stat = file_path.stat()
                    file_mtime = file_stat.st_mtime

                    if file_mtime < cutoff_time:
                        file_size = file_stat.st_size
                        file_path.unlink()
                        result["files_deleted"] += 1
                        result["bytes_freed"] += file_size
                        logger.debug(
                            f"Deleted old file: {file_path.name} "
                            f"(age: {int(current_time - file_mtime)}s, "
                            f"size: {file_size} bytes)"
                        )
                except PermissionError as e:
                    result["files_failed"] += 1
                    error_msg = f"Permission denied deleting {file_path.name}: {e}"
                    result["errors"].append(error_msg)
                    logger.warning(error_msg)
                except OSError as e:
                    result["files_failed"] += 1
                    error_msg = f"OS error deleting {file_path.name}: {e}"
                    result["errors"].append(error_msg)
                    logger.warning(error_msg)
    except PermissionError as e:
        error_msg = f"Permission denied reading directory {directory}: {e}"
        result["errors"].append(error_msg)
        logger.error(error_msg)
    except OSError as e:
        error_msg = f"OS error reading directory {directory}: {e}"
        result["errors"].append(error_msg)
        logger.error(error_msg)

    if result["files_deleted"] > 0:
        logger.info(
            f"Cleanup completed: deleted {result['files_deleted']} files, "
            f"freed {result['bytes_freed']} bytes"
        )

    return result


def cleanup_specific_file(file_path: str) -> bool:
    """
    Delete a specific temporary file.

    Useful for immediate cleanup after file download is complete.

    Args:
        file_path: Path to the file to delete

    Returns:
        True if file was deleted, False otherwise
    """
    try:
        path = Path(file_path)
        if path.exists() and path.is_file():
            path.unlink()
            logger.debug(f"Deleted file: {file_path}")
            return True
        return False
    except Exception as e:
        logger.warning(f"Failed to delete file {file_path}: {e}")
        return False


async def cleanup_task_async(
    directory: Optional[str] = None,
    max_age_seconds: Optional[int] = None,
) -> dict[str, int]:
    """
    Async wrapper for cleanup_old_files.

    Runs the cleanup in a thread pool to avoid blocking the event loop.

    Args:
        directory: Path to the directory containing temporary files.
        max_age_seconds: Maximum age of files to keep in seconds.

    Returns:
        dict with cleanup statistics (same as cleanup_old_files)
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        cleanup_old_files,
        directory,
        max_age_seconds,
    )


class BackgroundCleanupTask:
    """
    Background task manager for periodic cleanup of temporary files.

    This class manages an asyncio task that periodically runs the cleanup
    function. It's designed to be integrated with FastAPI's lifespan context.

    Example usage with FastAPI:
        cleanup_task = BackgroundCleanupTask()

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            await cleanup_task.start()
            yield
            await cleanup_task.stop()
    """

    def __init__(
        self,
        directory: Optional[str] = None,
        max_age_seconds: Optional[int] = None,
        check_interval_seconds: Optional[int] = None,
    ):
        """
        Initialize the background cleanup task.

        Args:
            directory: Path to the directory to clean.
                       Defaults to COMPLIANCE_OUTPUT_PATH.
            max_age_seconds: Maximum age of files to keep.
                             Defaults to COMPLIANCE_CLEANUP_INTERVAL.
            check_interval_seconds: How often to run cleanup.
                                    Defaults to CLEANUP_CHECK_INTERVAL.
        """
        self.directory = directory or COMPLIANCE_OUTPUT_PATH
        self.max_age_seconds = max_age_seconds or COMPLIANCE_CLEANUP_INTERVAL
        self.check_interval = check_interval_seconds or CLEANUP_CHECK_INTERVAL
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the background cleanup task."""
        if self._running:
            logger.warning("Cleanup task is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_periodic_cleanup())
        logger.info(
            f"Started background cleanup task "
            f"(interval: {self.check_interval}s, max_age: {self.max_age_seconds}s)"
        )

    async def stop(self) -> None:
        """Stop the background cleanup task gracefully."""
        if not self._running:
            return

        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("Stopped background cleanup task")

    async def _run_periodic_cleanup(self) -> None:
        """Internal method that runs the cleanup loop."""
        # Run initial cleanup on startup
        await self._do_cleanup()

        while self._running:
            try:
                await asyncio.sleep(self.check_interval)
                if self._running:  # Check again after sleep
                    await self._do_cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}", exc_info=True)
                # Continue running even if there's an error
                await asyncio.sleep(self.check_interval)

    async def _do_cleanup(self) -> None:
        """Run a single cleanup cycle."""
        try:
            result = await cleanup_task_async(
                directory=self.directory,
                max_age_seconds=self.max_age_seconds,
            )
            if result["files_deleted"] > 0 or result["files_failed"] > 0:
                logger.info(
                    f"Cleanup cycle: deleted={result['files_deleted']}, "
                    f"failed={result['files_failed']}, "
                    f"bytes_freed={result['bytes_freed']}"
                )
        except Exception as e:
            logger.error(f"Cleanup cycle failed: {e}", exc_info=True)

    def is_running(self) -> bool:
        """Check if the cleanup task is currently running."""
        return self._running and self._task is not None


# Global instance for use in FastAPI lifespan
background_cleanup = BackgroundCleanupTask()


def get_cleanup_status() -> dict:
    """
    Get the current status of the cleanup system.

    Returns:
        dict with status information
    """
    return {
        "running": background_cleanup.is_running(),
        "directory": background_cleanup.directory,
        "max_age_seconds": background_cleanup.max_age_seconds,
        "check_interval_seconds": background_cleanup.check_interval,
    }


def ensure_output_directory() -> Path:
    """
    Ensure the output directory exists and return its path.

    Creates the directory if it doesn't exist.

    Returns:
        Path to the output directory
    """
    dir_path = Path(COMPLIANCE_OUTPUT_PATH)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path
