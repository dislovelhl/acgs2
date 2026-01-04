-- ACGS-2 Example 04: Audit Trail Database Schema
-- Constitutional Hash: cdd01ef066bc6cf2
--
-- This schema creates the audit_logs table for recording all governance decisions.
-- The table is designed to be append-only and immutable for compliance purposes.
--
-- Features:
-- - UUID primary keys for unique identification
-- - Timestamp tracking with timezone support
-- - JSONB columns for flexible metadata storage
-- - Indexes optimized for common query patterns
-- - CHECK constraints for data integrity

-- Create extension for UUID generation if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Main audit log table (append-only, immutable)
CREATE TABLE IF NOT EXISTS audit_logs (
    -- Unique identifier for this audit entry
    audit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- When the decision was made (from the workflow, not database insert time)
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Action details
    action_type VARCHAR(100) NOT NULL,
    environment VARCHAR(50),

    -- Who requested the action
    requester_id VARCHAR(100) NOT NULL,
    requester_type VARCHAR(50),

    -- What resource was targeted
    resource VARCHAR(500) NOT NULL,
    resource_type VARCHAR(100),

    -- Final decision
    decision VARCHAR(20) NOT NULL CHECK (decision IN ('allow', 'deny')),

    -- Risk assessment
    risk_score DECIMAL(4,3) CHECK (risk_score >= 0.0 AND risk_score <= 1.0),
    risk_category VARCHAR(20),

    -- Constitutional validation
    constitutional_valid BOOLEAN,
    constitutional_violations JSONB,

    -- HITL workflow tracking
    hitl_required BOOLEAN DEFAULT FALSE,
    hitl_decision JSONB,

    -- Denial information
    denial_reasons JSONB,

    -- Compliance and metadata
    compliance_tags JSONB,
    retention_days INTEGER,
    log_level VARCHAR(20),

    -- Additional metadata (flexible JSON storage)
    metadata JSONB,

    -- Immutability tracking
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Prevent updates with a trigger (defined below)
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_audit_timestamp
    ON audit_logs(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_audit_created_at
    ON audit_logs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_requester
    ON audit_logs(requester_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_audit_decision
    ON audit_logs(decision, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_audit_action_type
    ON audit_logs(action_type, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_audit_environment
    ON audit_logs(environment, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_audit_hitl
    ON audit_logs(hitl_required, timestamp DESC)
    WHERE hitl_required = TRUE;

-- JSONB indexes for compliance tags (GIN index for efficient JSON queries)
CREATE INDEX IF NOT EXISTS idx_audit_compliance_tags
    ON audit_logs USING GIN (compliance_tags);

CREATE INDEX IF NOT EXISTS idx_audit_metadata
    ON audit_logs USING GIN (metadata);

-- Function to prevent updates (immutability enforcement)
CREATE OR REPLACE FUNCTION prevent_audit_updates()
RETURNS TRIGGER AS $$
BEGIN
    -- Allow INSERT but prevent UPDATE and DELETE
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'Audit logs are immutable and cannot be updated';
    END IF;
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Audit logs are immutable and cannot be deleted';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to enforce immutability
DROP TRIGGER IF EXISTS audit_immutability_trigger ON audit_logs;
CREATE TRIGGER audit_immutability_trigger
    BEFORE UPDATE OR DELETE ON audit_logs
    FOR EACH ROW
    EXECUTE FUNCTION prevent_audit_updates();

-- View for easy querying of recent decisions
CREATE OR REPLACE VIEW recent_decisions AS
SELECT
    audit_id,
    timestamp,
    action_type,
    requester_id,
    resource,
    decision,
    risk_score,
    risk_category,
    hitl_required,
    CASE
        WHEN decision = 'deny' THEN denial_reasons
        ELSE NULL
    END AS denial_reasons,
    created_at
FROM audit_logs
ORDER BY timestamp DESC
LIMIT 100;

-- View for compliance reporting
CREATE OR REPLACE VIEW compliance_summary AS
SELECT
    DATE(timestamp) as date,
    environment,
    decision,
    COUNT(*) as count,
    AVG(risk_score) as avg_risk_score,
    SUM(CASE WHEN hitl_required THEN 1 ELSE 0 END) as hitl_count,
    compliance_tags
FROM audit_logs
WHERE timestamp >= NOW() - INTERVAL '30 days'
GROUP BY DATE(timestamp), environment, decision, compliance_tags
ORDER BY date DESC, environment, decision;

-- Grant permissions (adjust as needed for your security requirements)
-- In production, you would use a dedicated audit_writer role with limited privileges
GRANT SELECT, INSERT ON audit_logs TO PUBLIC;
GRANT SELECT ON recent_decisions TO PUBLIC;
GRANT SELECT ON compliance_summary TO PUBLIC;

-- Add a comment to document the table
COMMENT ON TABLE audit_logs IS
'Immutable audit trail for all governance decisions in ACGS-2. This table is append-only and cannot be modified or deleted once written.';

COMMENT ON COLUMN audit_logs.audit_id IS
'Unique identifier for this audit entry (UUID v4)';

COMMENT ON COLUMN audit_logs.timestamp IS
'When the governance decision was made (from workflow timestamp, not DB insert time)';

COMMENT ON COLUMN audit_logs.decision IS
'Final decision: allow or deny';

COMMENT ON COLUMN audit_logs.risk_score IS
'Calculated risk score (0.0 to 1.0) from agent_actions policy';

COMMENT ON COLUMN audit_logs.hitl_decision IS
'Human approval decision details (JSON): {approved, reviewer_id, reviewer_role, decision_note, reviewed_at}';

COMMENT ON COLUMN audit_logs.compliance_tags IS
'Array of applicable compliance frameworks (JSON): ["SOC2", "GDPR", "HIPAA", etc.]';

COMMENT ON COLUMN audit_logs.metadata IS
'Additional metadata for observability and debugging (JSON)';

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Audit trail database schema initialized successfully';
    RAISE NOTICE 'Constitutional Hash: cdd01ef066bc6cf2';
END $$;
