"""
ACGS Code Analysis Engine - File Watcher Service
Monitor code changes using watchdog library with constitutional compliance.

Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import logging
from collections.abc import Callable
from pathlib import Path
from typing import List

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class ConstitutionalFileEventHandler(FileSystemEventHandler):
    """File system event handler with constitutional compliance."""

    def __init__(
        self,
        patterns: List[str] | None = None,
        ignore_patterns: List[str] | None = None,
        callback: Callable[[FileSystemEvent], None] | None = None,
    ):
        super().__init__()
        self.patterns = patterns or ["*.py"]
        self.ignore_patterns = ignore_patterns or ["__pycache__", ".git"]
        self.callback = callback
        self.event_queue: asyncio.Queue = asyncio.Queue()

    def on_any_event(self, event: FileSystemEvent) -> None:
        """Handle any file system event."""
        if event.is_directory:
            return

        # Check against patterns
        src_path = Path(event.src_path)

        # Skip ignored patterns
        for pattern in self.ignore_patterns:
            if pattern in str(src_path):
                return

        # Check if matches watched patterns
        matches = False
        for pattern in self.patterns:
            if src_path.match(pattern):
                matches = True
                break

        if not matches:
            return

        logger.debug(
            f"File event: {event.event_type} - {event.src_path}",
            extra={"constitutional_hash": CONSTITUTIONAL_HASH},
        )

        if self.callback:
            self.callback(event)


class FileWatcher:
    """Watch directories for file changes with constitutional compliance."""

    def __init__(
        self,
        paths: List[str],
        patterns: List[str] | None = None,
        ignore_patterns: List[str] | None = None,
        callback: Callable[[FileSystemEvent], None] | None = None,
    ):
        self.paths = paths
        self.patterns = patterns or ["*.py"]
        self.ignore_patterns = ignore_patterns or ["__pycache__", ".git", "*.pyc"]
        self.callback = callback
        self.observer: Observer | None = None
        self.is_running = False

    def start(self) -> None:
        """Start watching for file changes."""
        if self.is_running:
            return

        self.observer = Observer()
        handler = ConstitutionalFileEventHandler(
            patterns=self.patterns,
            ignore_patterns=self.ignore_patterns,
            callback=self.callback,
        )

        for path in self.paths:
            if Path(path).exists():
                self.observer.schedule(handler, path, recursive=True)
                logger.info(
                    f"Watching: {path}",
                    extra={"constitutional_hash": CONSTITUTIONAL_HASH},
                )

        self.observer.start()
        self.is_running = True
        logger.info(
            "File watcher started",
            extra={"constitutional_hash": CONSTITUTIONAL_HASH},
        )

    def stop(self) -> None:
        """Stop watching for file changes."""
        if not self.is_running or self.observer is None:
            return

        self.observer.stop()
        self.observer.join()
        self.is_running = False
        logger.info(
            "File watcher stopped",
            extra={"constitutional_hash": CONSTITUTIONAL_HASH},
        )

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
