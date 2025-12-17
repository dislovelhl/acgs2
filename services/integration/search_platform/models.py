"""
Search Platform Integration Models

Data models for communication with the Universal Search Platform API.
These models mirror the Rust API structures for seamless integration.

Constitutional Hash: cdd01ef066bc6cf2
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class SearchDomain(str, Enum):
    """Search domain types matching the Search Platform API."""
    CODE = "code"
    LOGS = "logs"
    DOCUMENTS = "documents"
    ALL = "all"


class SearchEventType(str, Enum):
    """Event types for streaming search results."""
    STARTED = "started"
    MATCH = "match"
    PROGRESS = "progress"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class TimeRange:
    """Time range filter for searches."""
    start: Optional[datetime] = None
    end: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        if self.start:
            result["start"] = self.start.isoformat()
        if self.end:
            result["end"] = self.end.isoformat()
        return result


@dataclass
class SearchScope:
    """Defines the scope of a search operation."""
    repos: List[str] = field(default_factory=list)
    paths: List[str] = field(default_factory=list)
    file_types: List[str] = field(default_factory=list)
    include_globs: List[str] = field(default_factory=list)
    exclude_globs: List[str] = field(default_factory=list)
    time_range: Optional[TimeRange] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "repos": self.repos,
            "paths": self.paths,
            "file_types": self.file_types,
            "include_globs": self.include_globs,
            "exclude_globs": self.exclude_globs,
        }
        if self.time_range:
            result["time_range"] = self.time_range.to_dict()
        return result


@dataclass
class SearchOptions:
    """Search options and configuration."""
    case_sensitive: bool = False
    whole_word: bool = False
    regex: bool = True
    multiline: bool = False
    max_results: int = 1000
    context_lines: int = 0
    include_hidden: bool = False
    follow_symlinks: bool = False
    timeout_ms: int = 30000

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_sensitive": self.case_sensitive,
            "whole_word": self.whole_word,
            "regex": self.regex,
            "multiline": self.multiline,
            "max_results": self.max_results,
            "context_lines": self.context_lines,
            "include_hidden": self.include_hidden,
            "follow_symlinks": self.follow_symlinks,
            "timeout_ms": self.timeout_ms,
        }


@dataclass
class SearchRequest:
    """Search request to send to the Search Platform API."""
    pattern: str
    domain: SearchDomain = SearchDomain.CODE
    scope: SearchScope = field(default_factory=SearchScope)
    options: SearchOptions = field(default_factory=SearchOptions)
    id: UUID = field(default_factory=uuid4)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "pattern": self.pattern,
            "domain": self.domain.value,
            "scope": self.scope.to_dict(),
            "options": self.options.to_dict(),
        }


@dataclass
class MatchMetadata:
    """Additional metadata for a search match."""
    language: Optional[str] = None
    encoding: Optional[str] = None
    binary: bool = False

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> Optional["MatchMetadata"]:
        if not data:
            return None
        return cls(
            language=data.get("language"),
            encoding=data.get("encoding"),
            binary=data.get("binary", False),
        )


@dataclass
class SearchMatch:
    """A single search match result."""
    file: str
    line_number: int
    column: int
    line_content: str
    match_text: str
    match_start: int = 0
    match_end: int = 0
    context_before: List[str] = field(default_factory=list)
    context_after: List[str] = field(default_factory=list)
    metadata: Optional[MatchMetadata] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchMatch":
        return cls(
            file=data["file"],
            line_number=data["line_number"],
            column=data.get("column", 0),
            line_content=data["line_content"],
            match_text=data["match_text"],
            match_start=data.get("match_start", 0),
            match_end=data.get("match_end", 0),
            context_before=data.get("context_before", []),
            context_after=data.get("context_after", []),
            metadata=MatchMetadata.from_dict(data.get("metadata")),
        )


@dataclass
class SearchStats:
    """Statistics about a search operation."""
    total_matches: int = 0
    files_matched: int = 0
    files_searched: int = 0
    bytes_searched: int = 0
    duration_ms: int = 0
    truncated: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchStats":
        return cls(
            total_matches=data.get("total_matches", 0),
            files_matched=data.get("files_matched", 0),
            files_searched=data.get("files_searched", 0),
            bytes_searched=data.get("bytes_searched", 0),
            duration_ms=data.get("duration_ms", 0),
            truncated=data.get("truncated", False),
        )


@dataclass
class SearchResponse:
    """Complete search response from the Search Platform API."""
    id: UUID
    results: List[SearchMatch]
    stats: SearchStats
    error: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchResponse":
        return cls(
            id=UUID(data["id"]),
            results=[SearchMatch.from_dict(m) for m in data.get("results", [])],
            stats=SearchStats.from_dict(data.get("stats", {})),
            error=data.get("error"),
        )


@dataclass
class SearchEvent:
    """Streaming search event for real-time results."""
    event_type: SearchEventType
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_sse(cls, event_type: str, data: Dict[str, Any]) -> "SearchEvent":
        return cls(
            event_type=SearchEventType(event_type),
            data=data,
        )


@dataclass
class HealthStatus:
    """Health status of the Search Platform."""
    status: str
    version: str
    workers: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HealthStatus":
        return cls(
            status=data.get("status", "unknown"),
            version=data.get("version", "unknown"),
            workers=data.get("workers", {}),
        )

    @property
    def is_healthy(self) -> bool:
        return self.status == "healthy"


@dataclass
class PlatformStats:
    """Statistics about the Search Platform."""
    total_workers: int
    healthy_workers: int
    active_searches: int
    total_searches: int
    avg_latency_ms: float

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlatformStats":
        return cls(
            total_workers=data.get("total_workers", 0),
            healthy_workers=data.get("healthy_workers", 0),
            active_searches=data.get("active_searches", 0),
            total_searches=data.get("total_searches", 0),
            avg_latency_ms=data.get("avg_latency_ms", 0.0),
        )
