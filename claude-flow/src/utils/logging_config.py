#!/usr/bin/env python3
"""
Logging configuration for Claude Flow components.

Provides structured logging to replace print statements throughout the codebase.
"""

import json
import logging
import sys
from typing import Any, Dict, Optional


def setup_logging(
    name: str, level: str = "INFO", format_string: Optional[str] = None, json_format: bool = False
) -> logging.Logger:
    """
    Setup structured logging for a component.

    Args:
        name: Logger name (typically __name__)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string, or None for default
        json_format: Whether to use JSON formatting

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logger.level)

    if json_format:
        # JSON formatter for structured logging
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": self.formatTime(record),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }

                # Add exception info if present
                if record.exc_info:
                    log_entry["exception"] = self.formatException(record.exc_info)

                # Add extra fields
                if hasattr(record, "extra_fields"):
                    log_entry.update(record.extra_fields)

                return json.dumps(log_entry, default=str)

        formatter = JSONFormatter()
    else:
        # Human-readable formatter
        if format_string is None:
            format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        formatter = logging.Formatter(format_string)

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def log_error_result(logger: logging.Logger, error_message: str, **extra_fields) -> None:
    """
    Log an error result in JSON format.

    Replaces: print(json.dumps({"success": False, "error": ...}))

    Args:
        logger: Logger instance
        error_message: Error message
        **extra_fields: Additional fields to include
    """
    log_data = {"success": False, "error": error_message, **extra_fields}
    logger.error(json.dumps(log_data))


def log_success_result(logger: logging.Logger, result_data: Dict[str, Any]) -> None:
    """
    Log a success result in JSON format (replaces print(json.dumps(result))).

    Args:
        logger: Logger instance
        result_data: Result data dictionary
    """
    logger.info(json.dumps(result_data))


def log_warning(logger: logging.Logger, message: str, **extra_fields) -> None:
    """
    Log a warning message (replaces print(f"Warning: ...", file=sys.stderr)).

    Args:
        logger: Logger instance
        message: Warning message
        **extra_fields: Additional fields to include
    """
    if extra_fields:
        # Use extra parameter for structured logging
        logger.warning(message, extra={"extra_fields": extra_fields})
    else:
        logger.warning(message)


# Global logger instances for backward compatibility
coordination_logger = setup_logging("claude_flow.coordination", json_format=True)
task_logger = setup_logging("claude_flow.task", json_format=True)
swarm_logger = setup_logging("claude_flow.swarm", json_format=True)
agent_logger = setup_logging("claude_flow.agent", json_format=True)
