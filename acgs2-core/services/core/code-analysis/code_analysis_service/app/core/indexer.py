"""
ACGS Code Analysis Engine - Indexer Service
Indexes code symbols for semantic search with constitutional compliance.

Constitutional Hash: cdd01ef066bc6cf2
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class CodeSymbol:
    """Represents a code symbol (function, class, variable, etc.)."""

    def __init__(
        self,
        name: str,
        symbol_type: str,
        file_path: str,
        line_number: int,
        content: str = "",
        docstring: str = "",
    ):
        self.name = name
        self.symbol_type = symbol_type
        self.file_path = file_path
        self.line_number = line_number
        self.content = content
        self.docstring = docstring
        self.created_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "symbol_type": self.symbol_type,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "content": self.content,
            "docstring": self.docstring,
            "created_at": self.created_at.isoformat(),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }


class CodeIndexer:
    """Indexes code files for semantic search."""

    def __init__(self, base_path: str | Path):
        self.base_path = Path(base_path)
        self.symbols: List[CodeSymbol] = []
        self.indexed_files: Dict[str, datetime] = {}

    def index_file(self, file_path: str | Path) -> List[CodeSymbol]:
        """Index a single Python file."""
        file_path = Path(file_path)

        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return []

        if not file_path.suffix == ".py":
            return []

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(
                f"Error reading file: {file_path} - {e}",
                extra={"constitutional_hash": CONSTITUTIONAL_HASH},
            )
            return []

        symbols = self._extract_symbols(content, str(file_path))
        self.indexed_files[str(file_path)] = datetime.now(timezone.utc)

        logger.info(
            f"Indexed {len(symbols)} symbols from {file_path}",
            extra={"constitutional_hash": CONSTITUTIONAL_HASH},
        )

        return symbols

    def _extract_symbols(self, content: str, file_path: str) -> List[CodeSymbol]:
        """Extract code symbols from content."""
        symbols = []
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Extract function definitions
            if stripped.startswith("def "):
                name = stripped[4:].split("(")[0].strip()
                symbols.append(
                    CodeSymbol(
                        name=name,
                        symbol_type="function",
                        file_path=file_path,
                        line_number=i,
                        content=stripped,
                    )
                )

            # Extract class definitions
            elif stripped.startswith("class "):
                name = stripped[6:].split("(")[0].split(":")[0].strip()
                symbols.append(
                    CodeSymbol(
                        name=name,
                        symbol_type="class",
                        file_path=file_path,
                        line_number=i,
                        content=stripped,
                    )
                )

            # Extract async function definitions
            elif stripped.startswith("async def "):
                name = stripped[10:].split("(")[0].strip()
                symbols.append(
                    CodeSymbol(
                        name=name,
                        symbol_type="async_function",
                        file_path=file_path,
                        line_number=i,
                        content=stripped,
                    )
                )

        self.symbols.extend(symbols)
        return symbols

    def index_directory(self, directory: str | Path | None = None) -> int:
        """Index all Python files in a directory."""
        directory = Path(directory) if directory else self.base_path
        total_symbols = 0

        for py_file in directory.rglob("*.py"):
            # Skip pycache and hidden directories
            if "__pycache__" in str(py_file) or "/.git/" in str(py_file):
                continue

            symbols = self.index_file(py_file)
            total_symbols += len(symbols)

        logger.info(
            f"Total indexed: {total_symbols} symbols from {directory}",
            extra={"constitutional_hash": CONSTITUTIONAL_HASH},
        )

        return total_symbols

    def search(self, query: str, limit: int = 10) -> List[CodeSymbol]:
        """Simple text-based search in indexed symbols."""
        query_lower = query.lower()
        results = []

        for symbol in self.symbols:
            if query_lower in symbol.name.lower():
                results.append(symbol)
                if len(results) >= limit:
                    break

        return results
