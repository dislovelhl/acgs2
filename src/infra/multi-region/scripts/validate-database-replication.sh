#!/bin/bash
# =============================================================================
# PostgreSQL Database Replication Validation Script
# =============================================================================
# This script validates PostgreSQL streaming replication between primary and
# standby instances across multi-region deployments.
#
# Usage:
#   ./validate-database-replication.sh [OPTIONS] <primary-context> <standby-context>
#
# Options:
#   --namespace       Database namespace (default: acgs-database)
#   --primary-pod     Primary PostgreSQL pod name (default: auto-detect)
#   --standby-pod     Standby PostgreSQL pod name (default: auto-detect)
#   --lag-threshold   Maximum acceptable replication lag in seconds (default: 60)
#   --dry-run         Show validation steps without executing
#   --json            Output results in JSON format
#   --verbose         Show detailed output including SQL queries
#   --skip-write      Skip write test (only check replication status)
#   --cleanup         Clean up test data after validation
#   --timeout         Timeout for operations in seconds (default: 60)
#   --help            Show this help message
#
# Examples:
#   ./validate-database-replication.sh region1 region2
#   ./validate-database-replication.sh --verbose --json us-east-1 eu-west-1
#   ./validate-database-replication.sh --lag-threshold 30 --cleanup region1 region2
#
# Requirements:
#   - kubectl with contexts for all specified clusters
#   - PostgreSQL deployed in both regions (Bitnami Helm chart)
#   - Primary configured for streaming replication
#   - Standby connected and receiving WAL
#
# Validation Steps:
#   1. Connect to primary PostgreSQL and verify pg_stat_replication shows streaming
#   2. Check replication slot exists and is active
#   3. Write test data to primary
#   4. Verify data appears on standby within lag threshold
#   5. Validate replication lag is within acceptable range
#
# References:
#   - https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STAT-REPLICATION-VIEW
#   - https://github.com/bitnami/charts/tree/main/bitnami/postgresql
# =============================================================================

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================
NAMESPACE="acgs-database"
PRIMARY_POD=""
STANDBY_POD=""
LAG_THRESHOLD=60
DRY_RUN=false
JSON_OUTPUT=false
VERBOSE=false
SKIP_WRITE=false
CLEANUP=false
TIMEOUT=60
PRIMARY_CONTEXT=""
STANDBY_CONTEXT=""

# Primary and standby service/release names
PRIMARY_RELEASE="postgresql-primary"
STANDBY_RELEASE="postgresql-standby"

# Test data identifiers
TEST_TABLE="replication_test"
TEST_SCHEMA="public"
TEST_ID_PREFIX="reptest_"

# Results tracking
VALIDATION_PASSED=true
RESULTS=()
ERRORS=()

# Timing
START_TIME=0
END_TIME=0

# Color output for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# =============================================================================
# Logging Functions
# =============================================================================
log_info() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${BLUE}[INFO]${NC} $(date '+%H:%M:%S') $1"
    fi
}

log_success() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${GREEN}[PASS]${NC} $(date '+%H:%M:%S') $1"
    fi
}

log_warn() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${YELLOW}[WARN]${NC} $(date '+%H:%M:%S') $1"
    fi
}

log_error() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${RED}[FAIL]${NC} $(date '+%H:%M:%S') $1" >&2
    fi
}

log_step() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${CYAN}[STEP]${NC} $1"
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    fi
}

log_verbose() {
    if [[ "$VERBOSE" == "true" && "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${MAGENTA}[VERBOSE]${NC} $1"
    fi
}

log_sql() {
    if [[ "$VERBOSE" == "true" && "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${MAGENTA}[SQL]${NC} $1"
    fi
}

# =============================================================================
# Helper Functions
# =============================================================================
usage() {
    head -55 "$0" | grep -E '^#' | sed 's/^# *//' | tail -n +2
    exit 0
}

add_result() {
    local test_name="$1"
    local status="$2"
    local message="$3"
    local details="${4:-}"

    # Escape quotes in message and details for JSON
    local escaped_message
    local escaped_details
    escaped_message=$(echo "$message" | sed 's/"/\\"/g')
    escaped_details=$(echo "$details" | sed 's/"/\\"/g')

    RESULTS+=("{\"test\": \"$test_name\", \"status\": \"$status\", \"message\": \"$escaped_message\", \"details\": \"$escaped_details\"}")

    if [[ "$status" == "PASS" ]]; then
        log_success "$test_name: $message"
    elif [[ "$status" == "FAIL" ]]; then
        log_error "$test_name: $message"
        VALIDATION_PASSED=false
        ERRORS+=("$test_name: $message")
    else
        log_warn "$test_name: $message"
    fi
}

get_timestamp_ms() {
    if [[ "$(uname)" == "Darwin" ]]; then
        python3 -c 'import time; print(int(time.time() * 1000))' 2>/dev/null || \
        echo $(($(date +%s) * 1000))
    else
        date +%s%3N 2>/dev/null || echo $(($(date +%s) * 1000))
    fi
}

# =============================================================================
# Prerequisite Checks
# =============================================================================
check_prerequisites() {
    log_step "Checking prerequisites"

    local missing_tools=()

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        missing_tools+=("kubectl")
    else
        log_verbose "kubectl found: $(kubectl version --client --short 2>/dev/null || kubectl version --client -o yaml | grep gitVersion | head -1)"
    fi

    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        add_result "Prerequisites" "FAIL" "Missing required tools: ${missing_tools[*]}"
        return 1
    fi

    add_result "Prerequisites" "PASS" "All required tools available (kubectl)"
    return 0
}

check_cluster_access() {
    log_step "Verifying cluster access"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "DRY RUN: Would check cluster access for context $PRIMARY_CONTEXT"
        log_verbose "DRY RUN: Would check cluster access for context $STANDBY_CONTEXT"
        add_result "Cluster Access" "SKIP" "Dry run mode - skipping cluster access check"
        return 0
    fi

    # Check Primary access
    if ! kubectl --context="$PRIMARY_CONTEXT" cluster-info &> /dev/null; then
        add_result "Cluster Access (Primary)" "FAIL" "Cannot access cluster with context: $PRIMARY_CONTEXT"
        return 1
    fi
    log_verbose "Primary cluster accessible: $PRIMARY_CONTEXT"

    # Check Standby access
    if ! kubectl --context="$STANDBY_CONTEXT" cluster-info &> /dev/null; then
        add_result "Cluster Access (Standby)" "FAIL" "Cannot access cluster with context: $STANDBY_CONTEXT"
        return 1
    fi
    log_verbose "Standby cluster accessible: $STANDBY_CONTEXT"

    add_result "Cluster Access" "PASS" "Both cluster contexts accessible"
    return 0
}

# =============================================================================
# Pod Discovery
# =============================================================================
discover_postgresql_pods() {
    log_step "Discovering PostgreSQL pods"

    if [[ "$DRY_RUN" == "true" ]]; then
        PRIMARY_POD="${PRIMARY_RELEASE}-postgresql-0"
        STANDBY_POD="${STANDBY_RELEASE}-postgresql-0"
        log_verbose "DRY RUN: Using simulated pod names"
        add_result "Pod Discovery" "SKIP" "Dry run mode - using default pod names"
        return 0
    fi

    # Discover primary pod
    if [[ -z "$PRIMARY_POD" ]]; then
        PRIMARY_POD=$(kubectl --context="$PRIMARY_CONTEXT" get pods -n "$NAMESPACE" \
            -l "app.kubernetes.io/name=postgresql,app.kubernetes.io/instance=${PRIMARY_RELEASE}" \
            -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

        if [[ -z "$PRIMARY_POD" ]]; then
            # Try alternative label selector
            PRIMARY_POD=$(kubectl --context="$PRIMARY_CONTEXT" get pods -n "$NAMESPACE" \
                -l "app.kubernetes.io/name=postgresql" \
                -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
        fi
    fi

    if [[ -z "$PRIMARY_POD" ]]; then
        add_result "Primary Pod Discovery" "FAIL" "Could not find primary PostgreSQL pod in namespace $NAMESPACE"
        return 1
    fi
    log_verbose "Primary pod: $PRIMARY_POD"

    # Discover standby pod
    if [[ -z "$STANDBY_POD" ]]; then
        STANDBY_POD=$(kubectl --context="$STANDBY_CONTEXT" get pods -n "$NAMESPACE" \
            -l "app.kubernetes.io/name=postgresql,app.kubernetes.io/instance=${STANDBY_RELEASE}" \
            -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

        if [[ -z "$STANDBY_POD" ]]; then
            # Try alternative label selector
            STANDBY_POD=$(kubectl --context="$STANDBY_CONTEXT" get pods -n "$NAMESPACE" \
                -l "app.kubernetes.io/name=postgresql" \
                -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
        fi
    fi

    if [[ -z "$STANDBY_POD" ]]; then
        add_result "Standby Pod Discovery" "FAIL" "Could not find standby PostgreSQL pod in namespace $NAMESPACE"
        return 1
    fi
    log_verbose "Standby pod: $STANDBY_POD"

    # Verify pods are running
    local primary_status
    primary_status=$(kubectl --context="$PRIMARY_CONTEXT" get pod "$PRIMARY_POD" -n "$NAMESPACE" \
        -o jsonpath='{.status.phase}' 2>/dev/null || echo "Unknown")

    local standby_status
    standby_status=$(kubectl --context="$STANDBY_CONTEXT" get pod "$STANDBY_POD" -n "$NAMESPACE" \
        -o jsonpath='{.status.phase}' 2>/dev/null || echo "Unknown")

    if [[ "$primary_status" != "Running" ]]; then
        add_result "Primary Pod Status" "FAIL" "Primary pod is not running (status: $primary_status)"
        return 1
    fi

    if [[ "$standby_status" != "Running" ]]; then
        add_result "Standby Pod Status" "FAIL" "Standby pod is not running (status: $standby_status)"
        return 1
    fi

    add_result "Pod Discovery" "PASS" "Primary: $PRIMARY_POD, Standby: $STANDBY_POD (both Running)"
    return 0
}

# =============================================================================
# SQL Execution Helper
# =============================================================================
exec_sql_primary() {
    local sql="$1"
    local database="${2:-postgres}"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_sql "DRY RUN: Would execute on primary: $sql"
        return 0
    fi

    log_sql "Executing on primary: $sql"
    kubectl --context="$PRIMARY_CONTEXT" exec -n "$NAMESPACE" "$PRIMARY_POD" -- \
        psql -U postgres -d "$database" -t -A -c "$sql" 2>/dev/null
}

exec_sql_standby() {
    local sql="$1"
    local database="${2:-postgres}"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_sql "DRY RUN: Would execute on standby: $sql"
        return 0
    fi

    log_sql "Executing on standby: $sql"
    kubectl --context="$STANDBY_CONTEXT" exec -n "$NAMESPACE" "$STANDBY_POD" -- \
        psql -U postgres -d "$database" -t -A -c "$sql" 2>/dev/null
}

# =============================================================================
# Validation Step 1: Verify pg_stat_replication shows streaming
# =============================================================================
validate_replication_streaming() {
    log_step "Step 1: Verifying pg_stat_replication shows streaming state"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "DRY RUN: Would query pg_stat_replication on primary"
        add_result "Replication Streaming" "SKIP" "Dry run mode - skipping streaming check"
        return 0
    fi

    # Query pg_stat_replication on primary
    local repl_status
    repl_status=$(exec_sql_primary "
        SELECT
            application_name,
            client_addr,
            state,
            sync_state,
            COALESCE(EXTRACT(EPOCH FROM replay_lag)::int, 0) as replay_lag_seconds
        FROM pg_stat_replication
        WHERE state = 'streaming'
        LIMIT 5;
    " || echo "ERROR")

    if [[ "$repl_status" == "ERROR" || -z "$repl_status" ]]; then
        add_result "Replication Streaming" "FAIL" "No streaming replicas found in pg_stat_replication"
        return 1
    fi

    # Count streaming replicas
    local streaming_count
    streaming_count=$(exec_sql_primary "
        SELECT COUNT(*) FROM pg_stat_replication WHERE state = 'streaming';
    " || echo "0")

    if [[ "$streaming_count" -eq 0 ]]; then
        add_result "Replication Streaming" "FAIL" "No replicas in streaming state"
        return 1
    fi

    log_verbose "Streaming replicas found: $streaming_count"
    log_verbose "Replication status:\n$repl_status"

    # Get details for the result
    local first_replica
    first_replica=$(echo "$repl_status" | head -1)

    add_result "Replication Streaming" "PASS" "$streaming_count replica(s) in streaming state" "$first_replica"
    return 0
}

# =============================================================================
# Validation Step 2: Check replication slot exists and is active
# =============================================================================
validate_replication_slots() {
    log_step "Step 2: Checking replication slot exists and is active"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "DRY RUN: Would query pg_replication_slots on primary"
        add_result "Replication Slots" "SKIP" "Dry run mode - skipping slot check"
        return 0
    fi

    # Query replication slots
    local slots_info
    slots_info=$(exec_sql_primary "
        SELECT
            slot_name,
            slot_type,
            active,
            pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) as retained_wal
        FROM pg_replication_slots
        WHERE slot_type = 'physical';
    " || echo "ERROR")

    if [[ "$slots_info" == "ERROR" ]]; then
        add_result "Replication Slots Query" "FAIL" "Failed to query replication slots"
        return 1
    fi

    # Count total slots
    local total_slots
    total_slots=$(exec_sql_primary "
        SELECT COUNT(*) FROM pg_replication_slots WHERE slot_type = 'physical';
    " || echo "0")

    if [[ "$total_slots" -eq 0 ]]; then
        add_result "Replication Slots" "WARN" "No physical replication slots found (replication may use WAL retention instead)"
        return 0
    fi

    # Count active slots
    local active_slots
    active_slots=$(exec_sql_primary "
        SELECT COUNT(*) FROM pg_replication_slots WHERE slot_type = 'physical' AND active = true;
    " || echo "0")

    log_verbose "Replication slots:\n$slots_info"

    if [[ "$active_slots" -gt 0 ]]; then
        add_result "Replication Slots" "PASS" "$active_slots of $total_slots physical slot(s) active"
    else
        add_result "Replication Slots" "WARN" "No active replication slots (all $total_slots slots inactive)"
    fi

    # Check for WAL retention size (warning if too large)
    local max_retained
    max_retained=$(exec_sql_primary "
        SELECT COALESCE(MAX(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)), 0)::bigint
        FROM pg_replication_slots
        WHERE slot_type = 'physical';
    " || echo "0")

    # Warn if retained WAL exceeds 1GB (1073741824 bytes)
    if [[ "$max_retained" -gt 1073741824 ]]; then
        local retained_human
        retained_human=$(exec_sql_primary "
            SELECT pg_size_pretty(${max_retained}::bigint);
        " || echo "${max_retained} bytes")
        add_result "WAL Retention" "WARN" "Replication slot retaining $retained_human of WAL (monitor disk usage)"
    fi

    return 0
}

# =============================================================================
# Validation Step 3: Write test data to primary
# =============================================================================
write_test_data() {
    log_step "Step 3: Writing test data to primary"

    if [[ "$SKIP_WRITE" == "true" ]]; then
        add_result "Write Test Data" "SKIP" "Skipped by --skip-write flag"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "DRY RUN: Would create test table and insert test data"
        add_result "Write Test Data" "SKIP" "Dry run mode - skipping write test"
        return 0
    fi

    local test_id="${TEST_ID_PREFIX}$(date +%s)_$$"
    local test_value="Replication test at $(date -u +"%Y-%m-%dT%H:%M:%SZ")"

    log_info "Creating test table if not exists..."
    exec_sql_primary "
        CREATE TABLE IF NOT EXISTS ${TEST_SCHEMA}.${TEST_TABLE} (
            id SERIAL PRIMARY KEY,
            test_id VARCHAR(100) UNIQUE NOT NULL,
            test_value TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    " "acgs" 2>/dev/null || exec_sql_primary "
        CREATE TABLE IF NOT EXISTS ${TEST_SCHEMA}.${TEST_TABLE} (
            id SERIAL PRIMARY KEY,
            test_id VARCHAR(100) UNIQUE NOT NULL,
            test_value TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    " "postgres" 2>/dev/null || true

    log_info "Inserting test data: $test_id"
    local insert_result
    insert_result=$(exec_sql_primary "
        INSERT INTO ${TEST_SCHEMA}.${TEST_TABLE} (test_id, test_value)
        VALUES ('${test_id}', '${test_value}')
        ON CONFLICT (test_id) DO UPDATE SET test_value = EXCLUDED.test_value
        RETURNING id, test_id;
    " "acgs" 2>/dev/null || exec_sql_primary "
        INSERT INTO ${TEST_SCHEMA}.${TEST_TABLE} (test_id, test_value)
        VALUES ('${test_id}', '${test_value}')
        ON CONFLICT (test_id) DO UPDATE SET test_value = EXCLUDED.test_value
        RETURNING id, test_id;
    " "postgres" 2>/dev/null || echo "ERROR")

    if [[ "$insert_result" == "ERROR" || -z "$insert_result" ]]; then
        add_result "Write Test Data" "FAIL" "Failed to insert test data into primary"
        return 1
    fi

    log_verbose "Insert result: $insert_result"

    # Store test_id for verification
    echo "$test_id" > /tmp/replication-test-id-$$

    add_result "Write Test Data" "PASS" "Test data written to primary (test_id: $test_id)"
    return 0
}

# =============================================================================
# Validation Step 4: Verify data appears on standby within lag threshold
# =============================================================================
verify_replication_data() {
    log_step "Step 4: Verifying data appears on standby within lag threshold"

    if [[ "$SKIP_WRITE" == "true" ]]; then
        add_result "Verify Replication" "SKIP" "Skipped by --skip-write flag"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "DRY RUN: Would verify test data on standby"
        add_result "Verify Replication" "SKIP" "Dry run mode - skipping verification"
        return 0
    fi

    # Get test ID
    local test_id
    if [[ -f /tmp/replication-test-id-$$ ]]; then
        test_id=$(cat /tmp/replication-test-id-$$)
    else
        add_result "Verify Replication" "FAIL" "Test ID not found (write test may have failed)"
        return 1
    fi

    log_info "Waiting for data to replicate (test_id: $test_id)..."

    local start_time
    start_time=$(date +%s)
    local elapsed=0
    local data_found=false

    while [[ $elapsed -lt $LAG_THRESHOLD ]]; do
        # Query standby for test data
        local standby_result
        standby_result=$(exec_sql_standby "
            SELECT test_id, test_value, created_at
            FROM ${TEST_SCHEMA}.${TEST_TABLE}
            WHERE test_id = '${test_id}';
        " "acgs" 2>/dev/null || exec_sql_standby "
            SELECT test_id, test_value, created_at
            FROM ${TEST_SCHEMA}.${TEST_TABLE}
            WHERE test_id = '${test_id}';
        " "postgres" 2>/dev/null || echo "")

        if [[ -n "$standby_result" ]]; then
            data_found=true
            local replication_time=$(($(date +%s) - start_time))
            log_verbose "Data found on standby after ${replication_time}s"
            add_result "Data Replication" "PASS" "Data replicated to standby in ${replication_time}s (threshold: ${LAG_THRESHOLD}s)"
            break
        fi

        sleep 1
        elapsed=$(($(date +%s) - start_time))
        log_verbose "Waiting for replication... ${elapsed}s / ${LAG_THRESHOLD}s"
    done

    if [[ "$data_found" == "false" ]]; then
        add_result "Data Replication" "FAIL" "Data not found on standby within ${LAG_THRESHOLD}s threshold"
        return 1
    fi

    return 0
}

# =============================================================================
# Validation Step 5: Validate replication lag is within acceptable range
# =============================================================================
validate_replication_lag() {
    log_step "Step 5: Validating replication lag is within acceptable range"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "DRY RUN: Would check replication lag"
        add_result "Replication Lag" "SKIP" "Dry run mode - skipping lag check"
        return 0
    fi

    # Get replication lag from primary's perspective
    local lag_info
    lag_info=$(exec_sql_primary "
        SELECT
            application_name,
            client_addr,
            state,
            COALESCE(EXTRACT(EPOCH FROM replay_lag)::numeric(10,2), 0) as replay_lag_seconds,
            COALESCE(EXTRACT(EPOCH FROM write_lag)::numeric(10,2), 0) as write_lag_seconds,
            COALESCE(EXTRACT(EPOCH FROM flush_lag)::numeric(10,2), 0) as flush_lag_seconds,
            pg_wal_lsn_diff(sent_lsn, replay_lsn) as replay_lag_bytes
        FROM pg_stat_replication
        WHERE state = 'streaming'
        ORDER BY replay_lag_seconds DESC
        LIMIT 1;
    " || echo "ERROR")

    if [[ "$lag_info" == "ERROR" || -z "$lag_info" ]]; then
        add_result "Replication Lag" "WARN" "Could not determine replication lag (no streaming replicas)"
        return 0
    fi

    # Parse the lag value (format: app_name|client|state|replay_lag|write_lag|flush_lag|bytes)
    local replay_lag
    replay_lag=$(echo "$lag_info" | cut -d'|' -f4 | xargs)

    # Handle empty or null lag
    if [[ -z "$replay_lag" || "$replay_lag" == "0" || "$replay_lag" == "0.00" ]]; then
        add_result "Replication Lag" "PASS" "Replication lag: 0s (fully synchronized)"
        return 0
    fi

    # Compare with threshold (convert to integer for comparison)
    local lag_int
    lag_int=$(echo "$replay_lag" | cut -d'.' -f1)

    if [[ $lag_int -lt $LAG_THRESHOLD ]]; then
        add_result "Replication Lag" "PASS" "Replication lag: ${replay_lag}s (threshold: ${LAG_THRESHOLD}s)"
    else
        add_result "Replication Lag" "FAIL" "Replication lag: ${replay_lag}s exceeds threshold: ${LAG_THRESHOLD}s"
        VALIDATION_PASSED=false
    fi

    # Get standby's perspective using pg_stat_wal_receiver
    local standby_lag
    standby_lag=$(exec_sql_standby "
        SELECT
            CASE
                WHEN pg_last_wal_receive_lsn() = pg_last_wal_replay_lsn() THEN 0
                ELSE COALESCE(EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()))::numeric(10,2), 0)
            END as lag_seconds,
            CASE WHEN pg_is_in_recovery() THEN 'replica' ELSE 'primary' END as mode
        ;
    " || echo "")

    if [[ -n "$standby_lag" ]]; then
        local standby_lag_seconds
        standby_lag_seconds=$(echo "$standby_lag" | cut -d'|' -f1 | xargs)
        log_verbose "Standby reports lag: ${standby_lag_seconds}s"
    fi

    return 0
}

# =============================================================================
# Cleanup Test Data
# =============================================================================
cleanup_test_data() {
    if [[ "$CLEANUP" == "false" ]]; then
        return 0
    fi

    log_step "Cleaning up test data"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "DRY RUN: Would clean up test table"
        return 0
    fi

    if [[ -f /tmp/replication-test-id-$$ ]]; then
        local test_id
        test_id=$(cat /tmp/replication-test-id-$$)

        log_info "Removing test data: $test_id"
        exec_sql_primary "
            DELETE FROM ${TEST_SCHEMA}.${TEST_TABLE} WHERE test_id = '${test_id}';
        " "acgs" 2>/dev/null || exec_sql_primary "
            DELETE FROM ${TEST_SCHEMA}.${TEST_TABLE} WHERE test_id = '${test_id}';
        " "postgres" 2>/dev/null || true

        rm -f /tmp/replication-test-id-$$
        log_success "Test data cleaned up"
    fi
}

# =============================================================================
# Additional Checks
# =============================================================================
validate_standby_mode() {
    log_step "Validating standby is in recovery mode"

    if [[ "$DRY_RUN" == "true" ]]; then
        add_result "Standby Mode" "SKIP" "Dry run mode - skipping standby mode check"
        return 0
    fi

    local is_replica
    is_replica=$(exec_sql_standby "SELECT pg_is_in_recovery();" || echo "ERROR")

    if [[ "$is_replica" == "t" || "$is_replica" == "true" ]]; then
        add_result "Standby Mode" "PASS" "Standby is correctly in recovery mode (read-only replica)"
    elif [[ "$is_replica" == "f" || "$is_replica" == "false" ]]; then
        add_result "Standby Mode" "FAIL" "Standby is NOT in recovery mode (may be a primary)"
        return 1
    else
        add_result "Standby Mode" "WARN" "Could not determine standby mode"
    fi

    return 0
}

validate_wal_receiver() {
    log_step "Validating WAL receiver on standby"

    if [[ "$DRY_RUN" == "true" ]]; then
        add_result "WAL Receiver" "SKIP" "Dry run mode - skipping WAL receiver check"
        return 0
    fi

    local wal_receiver_info
    wal_receiver_info=$(exec_sql_standby "
        SELECT
            status,
            receive_start_lsn,
            received_lsn,
            COALESCE(EXTRACT(EPOCH FROM (now() - last_msg_receipt_time))::int, 0) as last_msg_age_seconds
        FROM pg_stat_wal_receiver;
    " || echo "")

    if [[ -z "$wal_receiver_info" ]]; then
        add_result "WAL Receiver" "FAIL" "No WAL receiver found on standby (replication not active)"
        return 1
    fi

    local status
    status=$(echo "$wal_receiver_info" | cut -d'|' -f1 | xargs)

    if [[ "$status" == "streaming" ]]; then
        add_result "WAL Receiver" "PASS" "WAL receiver status: streaming"
    elif [[ "$status" == "catchup" ]]; then
        add_result "WAL Receiver" "WARN" "WAL receiver status: catchup (may be behind)"
    else
        add_result "WAL Receiver" "WARN" "WAL receiver status: $status"
    fi

    return 0
}

# =============================================================================
# Output Results
# =============================================================================
output_results() {
    END_TIME=$(get_timestamp_ms)
    local duration_ms=$((END_TIME - START_TIME))
    local duration_s=$((duration_ms / 1000))

    if [[ "$JSON_OUTPUT" == "true" ]]; then
        local results_json="["
        for i in "${!RESULTS[@]}"; do
            results_json+="${RESULTS[$i]}"
            if [[ $i -lt $((${#RESULTS[@]} - 1)) ]]; then
                results_json+=","
            fi
        done
        results_json+="]"

        cat <<EOF
{
  "validation": "database-replication",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "primaryContext": "$PRIMARY_CONTEXT",
  "standbyContext": "$STANDBY_CONTEXT",
  "namespace": "$NAMESPACE",
  "primaryPod": "$PRIMARY_POD",
  "standbyPod": "$STANDBY_POD",
  "lagThreshold": $LAG_THRESHOLD,
  "durationMs": $duration_ms,
  "passed": $VALIDATION_PASSED,
  "results": $results_json
}
EOF
    else
        echo ""
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${CYAN}                    VALIDATION SUMMARY                                    ${NC}"
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo "  Primary Context:    $PRIMARY_CONTEXT"
        echo "  Standby Context:    $STANDBY_CONTEXT"
        echo "  Namespace:          $NAMESPACE"
        echo "  Lag Threshold:      ${LAG_THRESHOLD}s"
        echo "  Duration:           ${duration_s}s"
        echo ""

        local pass_count=0
        local fail_count=0
        local warn_count=0
        local skip_count=0

        for result in "${RESULTS[@]}"; do
            if echo "$result" | grep -q '"status": "PASS"'; then
                ((pass_count++))
            elif echo "$result" | grep -q '"status": "FAIL"'; then
                ((fail_count++))
            elif echo "$result" | grep -q '"status": "WARN"'; then
                ((warn_count++))
            elif echo "$result" | grep -q '"status": "SKIP"'; then
                ((skip_count++))
            fi
        done

        echo -e "  ${GREEN}PASSED:${NC}  $pass_count"
        echo -e "  ${RED}FAILED:${NC}  $fail_count"
        echo -e "  ${YELLOW}WARNINGS:${NC} $warn_count"
        echo -e "  ${BLUE}SKIPPED:${NC} $skip_count"
        echo ""

        if [[ "$VALIDATION_PASSED" == "true" ]]; then
            echo -e "${GREEN}✓ Database replication validation PASSED${NC}"
        else
            echo -e "${RED}✗ Database replication validation FAILED${NC}"
            echo ""
            echo -e "${RED}Errors:${NC}"
            for error in "${ERRORS[@]}"; do
                echo -e "  - $error"
            done
        fi
        echo ""
    fi
}

# =============================================================================
# Main Execution
# =============================================================================
main() {
    START_TIME=$(get_timestamp_ms)

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            --primary-pod)
                PRIMARY_POD="$2"
                shift 2
                ;;
            --standby-pod)
                STANDBY_POD="$2"
                shift 2
                ;;
            --lag-threshold)
                LAG_THRESHOLD="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --json)
                JSON_OUTPUT=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --skip-write)
                SKIP_WRITE=true
                shift
                ;;
            --cleanup)
                CLEANUP=true
                shift
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            --help)
                usage
                ;;
            -*)
                echo "Unknown option: $1" >&2
                usage
                ;;
            *)
                if [[ -z "$PRIMARY_CONTEXT" ]]; then
                    PRIMARY_CONTEXT="$1"
                elif [[ -z "$STANDBY_CONTEXT" ]]; then
                    STANDBY_CONTEXT="$1"
                fi
                shift
                ;;
        esac
    done

    # Validate required arguments
    if [[ -z "$PRIMARY_CONTEXT" || -z "$STANDBY_CONTEXT" ]]; then
        echo "Error: Both primary and standby contexts are required" >&2
        echo ""
        usage
    fi

    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo ""
        echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}║     DATABASE REPLICATION VALIDATION                                     ║${NC}"
        echo -e "${CYAN}║     PostgreSQL Cross-Region Streaming Replication                       ║${NC}"
        echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo "Primary Context: $PRIMARY_CONTEXT"
        echo "Standby Context: $STANDBY_CONTEXT"
        echo "Namespace: $NAMESPACE"
        echo "Lag Threshold: ${LAG_THRESHOLD}s"
        echo "Dry Run: $DRY_RUN"
        echo ""
    fi

    # Execute validation steps
    check_prerequisites || true
    check_cluster_access || true
    discover_postgresql_pods || true
    validate_standby_mode || true
    validate_wal_receiver || true
    validate_replication_streaming || true
    validate_replication_slots || true

    if [[ "$SKIP_WRITE" == "false" ]]; then
        write_test_data || true
        verify_replication_data || true
    fi

    validate_replication_lag || true

    # Cleanup
    cleanup_test_data || true
    rm -f /tmp/replication-test-id-$$ 2>/dev/null || true

    # Output results
    output_results

    # Exit with appropriate code
    if [[ "$VALIDATION_PASSED" == "true" ]]; then
        exit 0
    else
        exit 1
    fi
}

# Run main function
main "$@"
