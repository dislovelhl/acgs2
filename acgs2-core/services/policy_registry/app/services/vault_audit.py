"""
ACGS-2 Vault Crypto Service - Audit Operations
Constitutional Hash: cdd01ef066bc6cf2

Audit logging for Vault cryptographic operations with
constitutional compliance tracking.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .vault_models import CONSTITUTIONAL_HASH, VaultAuditEntry, VaultOperation

logger = logging.getLogger(__name__)


class VaultAuditLogger:
    """
    Audit logger for Vault operations.

    Provides comprehensive audit logging for all cryptographic
    operations with constitutional hash tracking.
    """

    def __init__(
        self,
        enabled: bool = True,
        max_entries: int = 10000,
        external_handler: Optional[Any] = None,
    ):
        """
        Initialize audit logger.

        Args:
            enabled: Whether audit logging is enabled
            max_entries: Maximum audit entries to retain in memory
            external_handler: Optional external audit handler
        """
        self._enabled = enabled
        self._max_entries = max_entries
        self._external_handler = external_handler
        self._audit_log: List[VaultAuditEntry] = []
        self._constitutional_hash = CONSTITUTIONAL_HASH

    def log(
        self,
        operation: VaultOperation,
        key_name: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[VaultAuditEntry]:
        """
        Add audit log entry.

        Args:
            operation: Type of vault operation
            key_name: Name of key involved (if any)
            success: Whether operation succeeded
            error_message: Error message if failed
            metadata: Additional operation metadata

        Returns:
            Created audit entry (or None if disabled)
        """
        if not self._enabled:
            return None

        entry = VaultAuditEntry(
            operation=operation,
            key_name=key_name,
            success=success,
            error_message=error_message,
            constitutional_hash=self._constitutional_hash,
            metadata=metadata or {},
        )

        # Add to in-memory log
        self._audit_log.append(entry)

        # Trim if exceeds max entries
        if len(self._audit_log) > self._max_entries:
            self._audit_log = self._audit_log[-self._max_entries :]

        # Log to standard logger
        level = logging.INFO if success else logging.WARNING
        logger.log(level, f"Vault audit: {operation.value} key={key_name} success={success}")

        # Send to external handler if configured
        if self._external_handler:
            try:
                self._external_handler(entry)
            except Exception as e:
                logger.error(f"External audit handler failed: {e}")

        return entry

    def get_entries(
        self,
        limit: int = 100,
        operation: Optional[VaultOperation] = None,
        key_name: Optional[str] = None,
        success_only: Optional[bool] = None,
        since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get audit log entries with filtering.

        Args:
            limit: Maximum entries to return
            operation: Filter by operation type
            key_name: Filter by key name
            success_only: Filter by success status (None = all)
            since: Filter entries after this timestamp

        Returns:
            List of audit entry dictionaries
        """
        entries = self._audit_log

        if operation:
            entries = [e for e in entries if e.operation == operation]
        if key_name:
            entries = [e for e in entries if e.key_name == key_name]
        if success_only is not None:
            entries = [e for e in entries if e.success == success_only]
        if since:
            entries = [e for e in entries if e.timestamp >= since]

        return [e.to_dict() for e in entries[-limit:]]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get audit log statistics.

        Returns:
            Statistics dictionary
        """
        total = len(self._audit_log)
        success_count = sum(1 for e in self._audit_log if e.success)
        failure_count = total - success_count

        # Count by operation
        operation_counts: Dict[str, int] = {}
        for entry in self._audit_log:
            op_name = entry.operation.value
            operation_counts[op_name] = operation_counts.get(op_name, 0) + 1

        # Recent failures
        recent_failures = [e.to_dict() for e in self._audit_log[-10:] if not e.success]

        return {
            "total_entries": total,
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": success_count / max(1, total),
            "operations_by_type": operation_counts,
            "recent_failures": recent_failures,
            "constitutional_hash": self._constitutional_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def clear(self) -> int:
        """
        Clear audit log and return count of cleared entries.

        Returns:
            Number of entries cleared
        """
        count = len(self._audit_log)
        self._audit_log.clear()
        logger.info(f"Cleared {count} audit entries")
        return count

    def export(self, format: str = "json") -> Any:
        """
        Export audit log in specified format.

        Args:
            format: Export format ("json", "csv", "dict")

        Returns:
            Exported data in requested format
        """
        entries = [e.to_dict() for e in self._audit_log]

        if format == "dict":
            return entries
        elif format == "json":
            import json

            return json.dumps(entries, indent=2, default=str)
        elif format == "csv":
            if not entries:
                return ""
            import csv
            import io

            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=entries[0].keys())
            writer.writeheader()
            for entry in entries:
                # Flatten metadata for CSV
                flat_entry = {**entry}
                flat_entry["metadata"] = str(entry.get("metadata", {}))
                writer.writerow(flat_entry)
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format}")

    @property
    def enabled(self) -> bool:
        """Check if audit logging is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Enable or disable audit logging."""
        self._enabled = value

    @property
    def entry_count(self) -> int:
        """Get current number of audit entries."""
        return len(self._audit_log)


__all__ = ["VaultAuditLogger"]
