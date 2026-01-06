"""
Base document generator class
Constitutional Hash: cdd01ef066bc6cf2
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path

try:
    from src.core.shared.types import DocumentData
except ImportError:
    from typing import Any, Dict

    DocumentData = Dict[str, Any]

logger = logging.getLogger(__name__)


class BaseGenerator(ABC):
    """Base class for document generators"""

    def __init__(self, output_dir: str = "/app/documents"):
        """
        Initialize generator.

        Args:
            output_dir: Directory for generated documents
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def generate(self, data: DocumentData, filename: str) -> Path:
        """
        Generate a document from data.

        Args:
            data: Document data dictionary
            filename: Output filename (without extension)

        Returns:
            Path to generated file
        """
        pass

    def _get_output_path(self, filename: str, extension: str) -> Path:
        """Get full output path for a filename."""
        return self.output_dir / f"{filename}.{extension}"
