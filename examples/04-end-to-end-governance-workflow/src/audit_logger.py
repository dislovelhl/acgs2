#!/usr/bin/env python3
"""
Audit Logger Module for ACGS-2 Governance Workflow

Provides structured audit logging to PostgreSQL with immutable, append-only
storage and comprehensive query capabilities for compliance and analysis.

Usage:
    from src.audit_logger import AuditLogger, AuditEntry, DatabaseConfig

    config = DatabaseConfig(
        host="localhost",
        port=5432,
        database="governance_audit",
        user="postgres",
        password="your_password"
    )
    logger = AuditLogger(config)

    # Log a decision
    entry = AuditEntry(
        timestamp=datetime.now(timezone.utc),
        action_type="read_data",
        requester_id="agent-001",
        resource="customer_data",
        decision="allow",
        risk_score=0.25
    )
    audit_id = logger.log_decision(entry)

    # Query recent decisions
    recent = logger.query_recent(limit=10)

Constitutional Hash: cdd01ef066bc6cf2
"""

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import psycopg2
from psycopg2 import extras

# Configure logging
logger = logging.getLogger(__name__)


# Custom exceptions for audit logger errors
class AuditLoggerError(Exception):
    """Base exception for audit logger errors"""

    pass


class AuditDatabaseError(AuditLoggerError):
    """Raised when database operations fail"""

    pass


class AuditConnectionError(AuditLoggerError):
    """Raised when database connection fails"""

    pass


@dataclass
class DatabaseConfig:
    """Configuration for PostgreSQL database connection"""

    host: str = "localhost"
    port: int = 5432
    database: str = "governance_audit"
    user: str = "postgres"
    password: str = ""
    min_connections: int = 1
    max_connections: int = 10


@dataclass
class AuditEntry:
    """
    Structured audit log entry for governance decisions.

    This dataclass represents a single governance decision to be logged.
    All fields are designed to match the audit_logs database schema.
    """

    # Required fields
    timestamp: datetime
    action_type: str
    requester_id: str
    resource: str
    decision: str  # "allow" or "deny"

    # Optional fields with defaults
    audit_id: UUID | None = None
    environment: str | None = None
    requester_type: str | None = None
    resource_type: str | None = None
    risk_score: float | None = None
    risk_category: str | None = None
    constitutional_valid: bool | None = None
    constitutional_violations: list | None = None
    hitl_required: bool = False
    hitl_decision: dict | None = None
    denial_reasons: list | None = None
    compliance_tags: list | None = None
    retention_days: int | None = None
    log_level: str | None = None
    metadata: dict | None = None

    def __post_init__(self):
        """Validate and normalize the audit entry"""
        # Generate UUID if not provided
        if self.audit_id is None:
            self.audit_id = uuid4()

        # Ensure timestamp has timezone
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=UTC)

        # Validate decision value
        if self.decision not in ("allow", "deny"):
            raise ValueError(f"Invalid decision: {self.decision}. Must be 'allow' or 'deny'")

        # Validate risk score if provided
        if self.risk_score is not None and not 0.0 <= self.risk_score <= 1.0:
            raise ValueError(f"Invalid risk_score: {self.risk_score}. Must be between 0.0 and 1.0")


class AuditLogger:
    """
    PostgreSQL-backed audit logger with query capabilities.

    This class provides immutable, append-only audit logging with comprehensive
    query methods for compliance reporting and analysis. Uses connection pooling
    for efficient database access.

    Attributes:
        config: DatabaseConfig instance
        pool: psycopg2 connection pool
    """

    def __init__(self, config: DatabaseConfig):
        """
        Initialize audit logger with database configuration.

        Args:
            config: DatabaseConfig instance with connection settings

        Raises:
            AuditConnectionError: If database connection fails
        """
        self.config = config
        self.pool = None

        try:
            # Create connection pool
            self.pool = psycopg2.pool.SimpleConnectionPool(
                config.min_connections,
                config.max_connections,
                host=config.host,
                port=config.port,
                database=config.database,
                user=config.user,
                password=config.password,
                options="-c statement_timeout=30000",  # 30 second timeout
            )
            logger.info(
                f"Audit logger initialized with connection pool "
                f"(min={config.min_connections}, max={config.max_connections})"
            )

            # Verify connection
            if not self.health_check():
                raise AuditConnectionError("Database health check failed")

        except psycopg2.Error as e:
            logger.error(f"Failed to initialize audit logger: {e}")
            raise AuditConnectionError(
                f"Cannot connect to database at {config.host}:{config.port}. Error: {e}"
            ) from e

    def health_check(self) -> bool:
        """
        Check database connectivity and health.

        Returns:
            True if database is healthy and accessible, False otherwise
        """
        try:
            conn = self.pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    result = cur.fetchone()
                    is_healthy = result == (1,)

                    if is_healthy:
                        logger.debug("Database health check passed")
                    else:
                        logger.warning("Database health check returned unexpected result")

                    return is_healthy
            finally:
                self.pool.putconn(conn)

        except psycopg2.Error as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def log_decision(self, entry: AuditEntry) -> UUID:
        """
        Log a governance decision to the audit trail (append-only).

        This method inserts a new audit entry into the database. The entry
        is immutable once written and cannot be modified or deleted.

        Args:
            entry: AuditEntry instance containing the decision details

        Returns:
            UUID of the logged audit entry

        Raises:
            AuditDatabaseError: If logging fails
        """
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                # Prepare the insert statement
                insert_sql = """
                INSERT INTO audit_logs (
                    audit_id, timestamp, action_type, environment,
                    requester_id, requester_type, resource, resource_type,
                    decision, risk_score, risk_category,
                    constitutional_valid, constitutional_violations,
                    hitl_required, hitl_decision, denial_reasons,
                    compliance_tags, retention_days, log_level, metadata
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING audit_id;
                """

                # Convert lists and dicts to JSON
                constitutional_violations_json = (
                    json.dumps(entry.constitutional_violations)
                    if entry.constitutional_violations
                    else None
                )
                hitl_decision_json = (
                    json.dumps(entry.hitl_decision) if entry.hitl_decision else None
                )
                denial_reasons_json = (
                    json.dumps(entry.denial_reasons) if entry.denial_reasons else None
                )
                compliance_tags_json = (
                    json.dumps(entry.compliance_tags) if entry.compliance_tags else None
                )
                metadata_json = json.dumps(entry.metadata) if entry.metadata else None

                # Execute insert
                cur.execute(
                    insert_sql,
                    (
                        entry.audit_id,
                        entry.timestamp,
                        entry.action_type,
                        entry.environment,
                        entry.requester_id,
                        entry.requester_type,
                        entry.resource,
                        entry.resource_type,
                        entry.decision,
                        entry.risk_score,
                        entry.risk_category,
                        entry.constitutional_valid,
                        constitutional_violations_json,
                        entry.hitl_required,
                        hitl_decision_json,
                        denial_reasons_json,
                        compliance_tags_json,
                        entry.retention_days,
                        entry.log_level,
                        metadata_json,
                    ),
                )

                # Get the returned audit_id
                result = cur.fetchone()
                audit_id = result[0]

                # Commit the transaction
                conn.commit()

                logger.info(
                    f"Logged audit entry {audit_id}: "
                    f"{entry.action_type} on {entry.resource} -> {entry.decision}"
                )

                return audit_id

        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"Failed to log audit entry: {e}")
            raise AuditDatabaseError(f"Failed to log decision: {e}") from e
        finally:
            self.pool.putconn(conn)

    def query_by_id(self, audit_id: UUID) -> AuditEntry | None:
        """
        Retrieve audit entry by UUID.

        Args:
            audit_id: UUID of the audit entry to retrieve

        Returns:
            AuditEntry if found, None otherwise
        """
        conn = self.pool.getconn()
        try:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM audit_logs WHERE audit_id = %s", (audit_id,))
                row = cur.fetchone()

                if row:
                    return self._row_to_entry(dict(row))
                return None

        except psycopg2.Error as e:
            logger.error(f"Failed to query audit entry by ID: {e}")
            raise AuditDatabaseError(f"Query failed: {e}") from e
        finally:
            self.pool.putconn(conn)

    def query_by_requester(self, requester_id: str, limit: int = 100) -> list[AuditEntry]:
        """
        Retrieve audit entries for a specific requester.

        Args:
            requester_id: ID of the requester to search for
            limit: Maximum number of entries to return (default: 100)

        Returns:
            List of AuditEntry instances, ordered by timestamp descending
        """
        conn = self.pool.getconn()
        try:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT * FROM audit_logs
                    WHERE requester_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                    """,
                    (requester_id, limit),
                )
                rows = cur.fetchall()

                return [self._row_to_entry(dict(row)) for row in rows]

        except psycopg2.Error as e:
            logger.error(f"Failed to query audit entries by requester: {e}")
            raise AuditDatabaseError(f"Query failed: {e}") from e
        finally:
            self.pool.putconn(conn)

    def query_by_decision(
        self,
        decision: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """
        Retrieve audit entries by decision type.

        Args:
            decision: Decision type to filter ("allow" or "deny")
            start_time: Optional start timestamp for filtering
            end_time: Optional end timestamp for filtering
            limit: Maximum number of entries to return (default: 100)

        Returns:
            List of AuditEntry instances, ordered by timestamp descending
        """
        conn = self.pool.getconn()
        try:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                # Build query dynamically based on time filters
                query = "SELECT * FROM audit_logs WHERE decision = %s"
                params = [decision]

                if start_time:
                    query += " AND timestamp >= %s"
                    params.append(start_time)

                if end_time:
                    query += " AND timestamp <= %s"
                    params.append(end_time)

                query += " ORDER BY timestamp DESC LIMIT %s"
                params.append(limit)

                cur.execute(query, params)
                rows = cur.fetchall()

                return [self._row_to_entry(dict(row)) for row in rows]

        except psycopg2.Error as e:
            logger.error(f"Failed to query audit entries by decision: {e}")
            raise AuditDatabaseError(f"Query failed: {e}") from e
        finally:
            self.pool.putconn(conn)

    def query_recent(self, limit: int = 50) -> list[AuditEntry]:
        """
        Retrieve the most recent audit entries.

        Args:
            limit: Maximum number of entries to return (default: 50)

        Returns:
            List of AuditEntry instances, ordered by timestamp descending
        """
        conn = self.pool.getconn()
        try:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT * FROM audit_logs
                    ORDER BY timestamp DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = cur.fetchall()

                return [self._row_to_entry(dict(row)) for row in rows]

        except psycopg2.Error as e:
            logger.error(f"Failed to query recent audit entries: {e}")
            raise AuditDatabaseError(f"Query failed: {e}") from e
        finally:
            self.pool.putconn(conn)

    def get_statistics(
        self, start_time: datetime | None = None, end_time: datetime | None = None
    ) -> dict:
        """
        Get audit statistics for compliance reporting and analysis.

        Args:
            start_time: Optional start timestamp for filtering
            end_time: Optional end timestamp for filtering

        Returns:
            Dictionary containing statistics:
            - total_decisions: Total number of decisions
            - allow_count: Number of allowed decisions
            - deny_count: Number of denied decisions
            - allow_rate: Percentage of allowed decisions
            - avg_risk_score: Average risk score
            - hitl_count: Number of decisions requiring HITL
            - hitl_rate: Percentage requiring HITL
            - top_requesters: List of top requesters
            - top_actions: List of most common action types
        """
        conn = self.pool.getconn()
        try:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                # Build time filter
                time_filter = ""
                params = []

                if start_time:
                    time_filter += " WHERE timestamp >= %s"
                    params.append(start_time)

                    if end_time:
                        time_filter += " AND timestamp <= %s"
                        params.append(end_time)
                elif end_time:
                    time_filter += " WHERE timestamp <= %s"
                    params.append(end_time)

                # Get overall statistics
                cur.execute(
                    f"""
                    SELECT
                        COUNT(*) as total_decisions,
                        SUM(CASE WHEN decision = 'allow' THEN 1 ELSE 0 END) as allow_count,
                        SUM(CASE WHEN decision = 'deny' THEN 1 ELSE 0 END) as deny_count,
                        AVG(risk_score) as avg_risk_score,
                        SUM(CASE WHEN hitl_required THEN 1 ELSE 0 END) as hitl_count
                    FROM audit_logs
                    {time_filter}
                    """,
                    params,
                )
                stats = dict(cur.fetchone())

                # Calculate rates
                total = stats["total_decisions"] or 0
                stats["allow_rate"] = (stats["allow_count"] / total * 100) if total > 0 else 0
                stats["deny_rate"] = (stats["deny_count"] / total * 100) if total > 0 else 0
                stats["hitl_rate"] = (stats["hitl_count"] / total * 100) if total > 0 else 0

                # Get top requesters
                cur.execute(
                    f"""
                    SELECT requester_id, COUNT(*) as count
                    FROM audit_logs
                    {time_filter}
                    GROUP BY requester_id
                    ORDER BY count DESC
                    LIMIT 10
                    """,
                    params,
                )
                stats["top_requesters"] = [dict(row) for row in cur.fetchall()]

                # Get top action types
                cur.execute(
                    f"""
                    SELECT action_type, COUNT(*) as count
                    FROM audit_logs
                    {time_filter}
                    GROUP BY action_type
                    ORDER BY count DESC
                    LIMIT 10
                    """,
                    params,
                )
                stats["top_actions"] = [dict(row) for row in cur.fetchall()]

                return stats

        except psycopg2.Error as e:
            logger.error(f"Failed to get audit statistics: {e}")
            raise AuditDatabaseError(f"Statistics query failed: {e}") from e
        finally:
            self.pool.putconn(conn)

    def _row_to_entry(self, row: dict) -> AuditEntry:
        """
        Convert a database row to an AuditEntry instance.

        Args:
            row: Dictionary representing a database row

        Returns:
            AuditEntry instance
        """
        # Parse JSON fields
        if isinstance(row.get("constitutional_violations"), str):
            row["constitutional_violations"] = json.loads(row["constitutional_violations"])
        if isinstance(row.get("hitl_decision"), str):
            row["hitl_decision"] = json.loads(row["hitl_decision"])
        if isinstance(row.get("denial_reasons"), str):
            row["denial_reasons"] = json.loads(row["denial_reasons"])
        if isinstance(row.get("compliance_tags"), str):
            row["compliance_tags"] = json.loads(row["compliance_tags"])
        if isinstance(row.get("metadata"), str):
            row["metadata"] = json.loads(row["metadata"])

        # Remove database-specific fields
        row.pop("created_at", None)
        row.pop("updated_at", None)

        return AuditEntry(**row)

    def close(self) -> None:
        """
        Close all database connections and release resources.

        Call this when you're done using the audit logger to ensure
        proper cleanup of the connection pool.
        """
        if self.pool:
            self.pool.closeall()
            logger.info("Audit logger connection pool closed")

    def __enter__(self) -> "AuditLogger":
        """Support for context manager (with statement)"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Cleanup when exiting context manager"""
        self.close()
