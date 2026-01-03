"""Constitutional Hash: cdd01ef066bc6cf2
HITL Approvals Audit Module

This module provides an append-only audit trail persistence layer for
immutable logging of all approval workflow events.

Key Components:
- AuditLedger: Core append-only audit log with Redis persistence
- AuditQueryResult: Query result container with pagination info
- AuditStatistics: Aggregate statistics about the audit ledger

Key Features:
- Append-only operations (no updates or deletes)
- Cryptographic integrity verification (SHA-256 checksums)
- Chain linking for tamper detection
- Redis-backed persistence for production use
- In-memory fallback for development/testing
- Comprehensive query capabilities with filtering and pagination
"""

from app.audit.ledger import (
    AuditLedger,
    AuditLedgerError,
    AuditQueryResult,
    AuditStatistics,
    ImmutabilityError,
    IntegrityError,
    RedisNotAvailableError,
    close_audit_ledger,
    get_audit_ledger,
    initialize_audit_ledger,
    reset_audit_ledger,
)

__all__ = [
    # Core Classes
    "AuditLedger",
    "AuditQueryResult",
    "AuditStatistics",
    # Exceptions
    "AuditLedgerError",
    "IntegrityError",
    "ImmutabilityError",
    "RedisNotAvailableError",
    # Singleton Management
    "get_audit_ledger",
    "initialize_audit_ledger",
    "close_audit_ledger",
    "reset_audit_ledger",
]
