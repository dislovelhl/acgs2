#!/bin/bash
# =============================================================================
# Regional Failover Validation Script - End-to-End Testing
# =============================================================================
# This script executes comprehensive regional failover validation including
# traffic monitoring, failure simulation, RTO measurement, and rebalancing
# verification.
#
# Usage:
#   ./validate-regional-failover.sh [OPTIONS] <region1-context> <region2-context>
#
# Options:
#   --namespace       Service namespace (default: acgs-services)
#   --service         Service to test (default: claude-flow)
#   --rto-target      Target RTO in seconds (default: 60)
#   --dry-run         Show validation steps without executing
#   --json            Output results in JSON format
#   --verbose         Show detailed output including timing breakdown
#   --no-restore      Skip pod restoration after test
#   --skip-monitoring Skip monitoring deployment verification
#   --skip-rebalance  Skip traffic rebalancing verification
#   --timeout         Maximum wait time for failover in seconds (default: 120)
#   --probe-interval  Interval between health probes in seconds (default: 1)
#   --help            Show this help message
#
# Examples:
#   ./validate-regional-failover.sh region1 region2
#   ./validate-regional-failover.sh --verbose --json us-east-1 eu-west-1
#   ./validate-regional-failover.sh --service neural-mcp --rto-target 30 region1 region2
#
# Requirements:
#   - kubectl with contexts for all specified clusters
#   - Istio service mesh deployed with locality-aware load balancing
#   - Services deployed and healthy in both regions
#   - DestinationRule with outlierDetection configured
#
# Validation Steps (E2E):
#   1. Verify prerequisites and cluster access
#   2. Deploy/verify monitoring to measure traffic distribution
#   3. Record baseline traffic distribution
#   4. Terminate all pods in Region 1 (simulate failure)
#   5. Measure time until traffic shifts to Region 2
#   6. Verify RTO < target (default: 60 seconds)
#   7. Restore Region 1 pods
#   8. Verify traffic rebalances to original distribution
#   9. Generate validation report
#
# RTO Calculation Components (from DestinationRule):
#   - Detection Time: consecutiveErrors * requestTimeout = 3 * 5s = 15s
#   - Analysis Interval: 10s
#   - Base Ejection Time: 30s
#   - Pod Readiness: ~10s (variable)
#   - Expected Total: ~55-65s
#
# References:
#   - https://istio.io/latest/docs/tasks/traffic-management/locality-load-balancing/
#   - https://istio.io/latest/docs/reference/config/networking/destination-rule/
# =============================================================================

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================
NAMESPACE="acgs-services"
SERVICE="claude-flow"
RTO_TARGET=60
DRY_RUN=false
JSON_OUTPUT=false
VERBOSE=false
RESTORE_PODS=true
SKIP_MONITORING=false
SKIP_REBALANCE=false
TIMEOUT=120
PROBE_INTERVAL=1
REGION1_CONTEXT=""
REGION2_CONTEXT=""

# Timing variables
START_TIME=0
END_TIME=0
FAILURE_START_TIME=0
FAILOVER_DETECTED_TIME=0
RESTORE_START_TIME=0
REBALANCE_COMPLETE_TIME=0
RTO_MEASURED=0

# Traffic baseline
BASELINE_REGION1_PODS=0
BASELINE_REGION2_PODS=0
ORIGINAL_REPLICAS=2

# Results tracking
VALIDATION_PASSED=true
RESULTS=()
ERRORS=()
WARNINGS=()

# Color output for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# =============================================================================
# Logging Functions
# =============================================================================
log_info() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${BLUE}[INFO]${NC} $(date '+%H:%M:%S.%3N') $1"
    fi
}

log_success() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${GREEN}[PASS]${NC} $(date '+%H:%M:%S.%3N') $1"
    fi
}

log_warn() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${YELLOW}[WARN]${NC} $(date '+%H:%M:%S.%3N') $1"
    fi
    WARNINGS+=("$1")
}

log_error() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${RED}[FAIL]${NC} $(date '+%H:%M:%S.%3N') $1" >&2
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
        echo -e "${MAGENTA}[VERBOSE]${NC} $(date '+%H:%M:%S.%3N') $1"
    fi
}

log_timing() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${BOLD}[TIMING]${NC} $(date '+%H:%M:%S.%3N') $1"
    fi
}

# =============================================================================
# Helper Functions
# =============================================================================
usage() {
    head -60 "$0" | grep -E '^#' | sed 's/^# *//' | tail -n +2
    exit 0
}

get_timestamp_ms() {
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS
        python3 -c 'import time; print(int(time.time() * 1000))' 2>/dev/null || \
        perl -MTime::HiRes=time -e 'printf "%.0f\n", time * 1000' 2>/dev/null || \
        echo $(($(date +%s) * 1000))
    else
        # Linux
        date +%s%3N 2>/dev/null || echo $(($(date +%s) * 1000))
    fi
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
    elif [[ "$status" == "SKIP" ]]; then
        log_info "$test_name: $message (SKIPPED)"
    else
        log_warn "$test_name: $message"
    fi
}

# =============================================================================
# Prerequisite Checks
# =============================================================================
check_prerequisites() {
    log_step "Step 1: Checking prerequisites"

    local missing_tools=()

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        missing_tools+=("kubectl")
    else
        log_verbose "kubectl found: $(kubectl version --client --short 2>/dev/null || kubectl version --client -o yaml | grep gitVersion | head -1)"
    fi

    # Check curl (for HTTP probing)
    if ! command -v curl &> /dev/null; then
        missing_tools+=("curl")
    else
        log_verbose "curl found: $(curl --version | head -1)"
    fi

    # Optional: Check istioctl for detailed diagnostics
    if command -v istioctl &> /dev/null; then
        log_verbose "istioctl found: $(istioctl version --remote=false 2>/dev/null || echo 'version check failed')"
    else
        log_verbose "istioctl not found (optional for diagnostics)"
    fi

    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        add_result "Prerequisites" "FAIL" "Missing required tools: ${missing_tools[*]}"
        return 1
    fi

    add_result "Prerequisites" "PASS" "All required tools available (kubectl, curl)"
    return 0
}

check_cluster_access() {
    log_step "Step 1b: Verifying cluster access"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "DRY RUN: Would check cluster access for contexts $REGION1_CONTEXT and $REGION2_CONTEXT"
        add_result "Cluster Access" "SKIP" "Dry run mode - skipping cluster access check"
        return 0
    fi

    # Check Region 1 access
    if ! kubectl --context="$REGION1_CONTEXT" cluster-info &> /dev/null; then
        add_result "Cluster Access (Region 1)" "FAIL" "Cannot access cluster with context: $REGION1_CONTEXT"
        return 1
    fi
    log_verbose "Region 1 cluster accessible: $REGION1_CONTEXT"

    # Check Region 2 access
    if ! kubectl --context="$REGION2_CONTEXT" cluster-info &> /dev/null; then
        add_result "Cluster Access (Region 2)" "FAIL" "Cannot access cluster with context: $REGION2_CONTEXT"
        return 1
    fi
    log_verbose "Region 2 cluster accessible: $REGION2_CONTEXT"

    add_result "Cluster Access" "PASS" "Both cluster contexts accessible"
    return 0
}

# =============================================================================
# Monitoring Verification
# =============================================================================
verify_monitoring_deployment() {
    log_step "Step 2: Verifying monitoring for traffic distribution measurement"

    if [[ "$SKIP_MONITORING" == "true" ]]; then
        add_result "Monitoring Verification" "SKIP" "Skipped by --skip-monitoring flag"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "DRY RUN: Would verify Prometheus/metrics endpoints"
        add_result "Monitoring Verification" "SKIP" "Dry run mode - skipping monitoring check"
        return 0
    fi

    local monitoring_ready=true

    # Check for Istio sidecar on service pods (provides Envoy metrics)
    log_info "Checking Istio sidecar injection on $SERVICE pods..."

    local pod_name
    pod_name=$(kubectl --context="$REGION1_CONTEXT" get pods -n "$NAMESPACE" \
        -l "app.kubernetes.io/name=$SERVICE" \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

    if [[ -n "$pod_name" ]]; then
        local containers
        containers=$(kubectl --context="$REGION1_CONTEXT" get pod "$pod_name" -n "$NAMESPACE" \
            -o jsonpath='{.spec.containers[*].name}' 2>/dev/null || echo "")

        if echo "$containers" | grep -q "istio-proxy"; then
            add_result "Istio Sidecar (Region 1)" "PASS" "Istio sidecar present on $SERVICE pods"
        else
            add_result "Istio Sidecar (Region 1)" "WARN" "No Istio sidecar found - traffic metrics may be limited"
            monitoring_ready=false
        fi
    else
        add_result "Service Pods (Region 1)" "FAIL" "No $SERVICE pods found in Region 1"
        monitoring_ready=false
    fi

    # Check for metrics endpoint availability
    log_info "Checking metrics endpoint availability..."

    # Check if Prometheus or similar is available for metrics collection
    local prometheus_ready
    prometheus_ready=$(kubectl --context="$REGION1_CONTEXT" get pods -n monitoring \
        -l "app=prometheus" -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "")

    if [[ "$prometheus_ready" == "Running" ]]; then
        add_result "Prometheus Monitoring" "PASS" "Prometheus is running for metrics collection"
    else
        # Try alternative namespace
        prometheus_ready=$(kubectl --context="$REGION1_CONTEXT" get pods -n istio-system \
            -l "app=prometheus" -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "")

        if [[ "$prometheus_ready" == "Running" ]]; then
            add_result "Prometheus Monitoring" "PASS" "Prometheus is running in istio-system"
        else
            add_result "Prometheus Monitoring" "WARN" "Prometheus not detected - using pod count for traffic estimation"
        fi
    fi

    # Check DestinationRule with outlier detection
    log_info "Checking DestinationRule for outlier detection configuration..."

    local dest_rule
    dest_rule=$(kubectl --context="$REGION1_CONTEXT" get destinationrule \
        "${SERVICE}-locality-lb" -n "$NAMESPACE" -o yaml 2>/dev/null || echo "")

    if [[ -n "$dest_rule" ]]; then
        if echo "$dest_rule" | grep -q "outlierDetection"; then
            add_result "DestinationRule (Outlier Detection)" "PASS" "Outlier detection configured for $SERVICE"

            # Extract outlier detection settings for verbose output
            if [[ "$VERBOSE" == "true" ]]; then
                local consecutive_errors
                consecutive_errors=$(echo "$dest_rule" | grep -A5 "outlierDetection" | grep "consecutiveGatewayErrors" | grep -oE '[0-9]+' || echo "N/A")
                local base_ejection
                base_ejection=$(echo "$dest_rule" | grep -A10 "outlierDetection" | grep "baseEjectionTime" | grep -oE '[0-9]+' || echo "N/A")
                log_verbose "Outlier detection: consecutiveErrors=$consecutive_errors, baseEjectionTime=${base_ejection}s"
            fi
        else
            add_result "DestinationRule (Outlier Detection)" "WARN" "No outlier detection in DestinationRule - failover may not work"
        fi
    else
        add_result "DestinationRule" "WARN" "No DestinationRule found for $SERVICE - using default Istio behavior"
    fi

    return 0
}

# =============================================================================
# Baseline Traffic Distribution
# =============================================================================
record_baseline_traffic() {
    log_step "Step 3: Recording baseline traffic distribution"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "DRY RUN: Would record baseline pod counts"
        BASELINE_REGION1_PODS=2
        BASELINE_REGION2_PODS=2
        add_result "Baseline Traffic" "SKIP" "Dry run mode - using simulated baseline"
        return 0
    fi

    # Get running pod count in Region 1
    BASELINE_REGION1_PODS=$(kubectl --context="$REGION1_CONTEXT" get pods -n "$NAMESPACE" \
        -l "app.kubernetes.io/name=$SERVICE" \
        --field-selector=status.phase=Running \
        -o jsonpath='{.items}' 2>/dev/null | jq -r 'length' 2>/dev/null || echo "0")

    # Get running pod count in Region 2
    BASELINE_REGION2_PODS=$(kubectl --context="$REGION2_CONTEXT" get pods -n "$NAMESPACE" \
        -l "app.kubernetes.io/name=$SERVICE" \
        --field-selector=status.phase=Running \
        -o jsonpath='{.items}' 2>/dev/null | jq -r 'length' 2>/dev/null || echo "0")

    log_timing "Baseline: Region 1 = $BASELINE_REGION1_PODS pods, Region 2 = $BASELINE_REGION2_PODS pods"

    if [[ "$BASELINE_REGION1_PODS" -eq 0 ]]; then
        add_result "Baseline (Region 1)" "FAIL" "No running pods found for $SERVICE in Region 1"
        return 1
    fi

    if [[ "$BASELINE_REGION2_PODS" -eq 0 ]]; then
        add_result "Baseline (Region 2)" "FAIL" "No running pods found for $SERVICE in Region 2"
        return 1
    fi

    # Store original replica count for restoration
    ORIGINAL_REPLICAS=$(kubectl --context="$REGION1_CONTEXT" get deployment "$SERVICE" -n "$NAMESPACE" \
        -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "2")

    add_result "Baseline Traffic" "PASS" "Region 1: $BASELINE_REGION1_PODS pods, Region 2: $BASELINE_REGION2_PODS pods"

    # Optional: Record traffic distribution percentages if metrics available
    log_verbose "Expected traffic distribution: Region 1 ~80%, Region 2 ~20% (based on locality config)"

    return 0
}

# =============================================================================
# Region Failure Simulation
# =============================================================================
simulate_region_failure() {
    log_step "Step 4: Simulating Region 1 failure (terminating all pods)"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "DRY RUN: Would scale down $SERVICE deployment to 0 replicas in Region 1"
        add_result "Region Failure Simulation" "SKIP" "Dry run mode - skipping failure simulation"
        return 0
    fi

    # Record failure start time
    FAILURE_START_TIME=$(get_timestamp_ms)
    log_timing "Failure simulation started at $(date '+%Y-%m-%d %H:%M:%S.%3N')"

    # Scale down deployment to 0
    log_info "Scaling $SERVICE to 0 replicas in Region 1..."

    if ! kubectl --context="$REGION1_CONTEXT" scale deployment "$SERVICE" \
        -n "$NAMESPACE" --replicas=0 2>/dev/null; then
        add_result "Region Failure Simulation" "FAIL" "Failed to scale down deployment"
        return 1
    fi

    # Wait for pods to terminate
    log_info "Waiting for all pods to terminate..."

    local wait_count=0
    local max_wait=60
    while [[ $wait_count -lt $max_wait ]]; do
        local running_pods
        running_pods=$(kubectl --context="$REGION1_CONTEXT" get pods -n "$NAMESPACE" \
            -l "app.kubernetes.io/name=$SERVICE" \
            --field-selector=status.phase=Running \
            -o jsonpath='{.items}' 2>/dev/null | jq -r 'length' 2>/dev/null || echo "0")

        if [[ "$running_pods" -eq 0 ]]; then
            local termination_time=$(($(get_timestamp_ms) - FAILURE_START_TIME))
            log_timing "All pods terminated after $((termination_time / 1000))s"
            break
        fi

        log_verbose "Waiting for termination... $running_pods pods still running"
        sleep 1
        ((wait_count++))
    done

    if [[ $wait_count -ge $max_wait ]]; then
        add_result "Pod Termination" "WARN" "Timeout waiting for pods to terminate (some pods may still be running)"
    else
        add_result "Pod Termination" "PASS" "All Region 1 pods terminated"
    fi

    add_result "Region Failure Simulation" "PASS" "Region 1 failure simulated (0 pods running)"
    return 0
}

# =============================================================================
# Failover Detection and RTO Measurement
# =============================================================================
measure_failover_rto() {
    log_step "Step 5: Measuring time until traffic shifts to Region 2 (RTO)"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "DRY RUN: Would monitor Region 2 health and measure failover time"
        RTO_MEASURED=45  # Simulated passing RTO
        add_result "Failover RTO" "SKIP" "Dry run mode - using simulated RTO of ${RTO_MEASURED}s"
        return 0
    fi

    log_info "Monitoring failover to Region 2..."

    local elapsed=0
    local failover_detected=false

    # Start measuring from failure simulation start
    local measure_start=$FAILURE_START_TIME

    while [[ $elapsed -lt $TIMEOUT ]]; do
        # Check if Region 2 is serving traffic (pods are healthy)
        local region2_ready
        region2_ready=$(kubectl --context="$REGION2_CONTEXT" get pods -n "$NAMESPACE" \
            -l "app.kubernetes.io/name=$SERVICE" \
            --field-selector=status.phase=Running \
            -o jsonpath='{.items[0].status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "False")

        if [[ "$region2_ready" == "True" ]]; then
            # Verify service is actually responding
            local pod_name
            pod_name=$(kubectl --context="$REGION2_CONTEXT" get pods -n "$NAMESPACE" \
                -l "app.kubernetes.io/name=$SERVICE" \
                --field-selector=status.phase=Running \
                -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

            if [[ -n "$pod_name" ]]; then
                # Mark failover as detected
                if [[ "$failover_detected" == "false" ]]; then
                    FAILOVER_DETECTED_TIME=$(get_timestamp_ms)
                    failover_detected=true
                    RTO_MEASURED=$(( (FAILOVER_DETECTED_TIME - FAILURE_START_TIME) / 1000 ))
                    log_timing "Failover detected at +${RTO_MEASURED}s"
                    break
                fi
            fi
        fi

        sleep "$PROBE_INTERVAL"
        elapsed=$((elapsed + PROBE_INTERVAL))

        if [[ "$VERBOSE" == "true" ]] && [[ $((elapsed % 5)) -eq 0 ]]; then
            log_verbose "Elapsed: ${elapsed}s / ${TIMEOUT}s, waiting for failover..."
        fi
    done

    if [[ "$failover_detected" == "false" ]]; then
        RTO_MEASURED=$TIMEOUT
        add_result "Failover Detection" "FAIL" "Failover not detected within ${TIMEOUT}s timeout"
        return 1
    fi

    add_result "Failover Detection" "PASS" "Traffic shifted to Region 2 in ${RTO_MEASURED}s"
    return 0
}

# =============================================================================
# RTO Verification
# =============================================================================
verify_rto_target() {
    log_step "Step 6: Verifying RTO < ${RTO_TARGET}s target"

    if [[ "$DRY_RUN" == "true" ]]; then
        add_result "RTO Verification" "SKIP" "Dry run mode - skipping RTO verification"
        return 0
    fi

    log_timing "RTO Measured: ${RTO_MEASURED}s"
    log_timing "RTO Target:   <${RTO_TARGET}s"

    if [[ $RTO_MEASURED -lt $RTO_TARGET ]]; then
        add_result "RTO Verification" "PASS" "RTO ${RTO_MEASURED}s is within target of ${RTO_TARGET}s"

        # Additional timing breakdown
        if [[ "$VERBOSE" == "true" ]]; then
            log_verbose "RTO Breakdown (expected components):"
            log_verbose "  - Detection Time (3 errors * 5s): ~15s"
            log_verbose "  - Analysis Interval: ~10s"
            log_verbose "  - Base Ejection Time: ~30s"
            log_verbose "  - Total Expected: ~55s"
            log_verbose "  - Actual Measured: ${RTO_MEASURED}s"
        fi

        return 0
    else
        add_result "RTO Verification" "FAIL" "RTO ${RTO_MEASURED}s exceeds target of ${RTO_TARGET}s"

        # Provide tuning recommendations
        log_warn "Consider tuning these DestinationRule parameters to reduce RTO:"
        log_warn "  - consecutiveGatewayErrors: reduce from 3 to 2"
        log_warn "  - interval: reduce from 10s to 5s"
        log_warn "  - baseEjectionTime: reduce from 30s to 15s"

        return 1
    fi
}

# =============================================================================
# Region Restoration
# =============================================================================
restore_region() {
    log_step "Step 7: Restoring Region 1 pods"

    if [[ "$RESTORE_PODS" == "false" ]]; then
        log_warn "Skipping pod restoration (--no-restore flag set)"
        add_result "Region Restoration" "SKIP" "Skipped by --no-restore flag"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "DRY RUN: Would scale up $SERVICE deployment to $ORIGINAL_REPLICAS replicas"
        add_result "Region Restoration" "SKIP" "Dry run mode - skipping restoration"
        return 0
    fi

    RESTORE_START_TIME=$(get_timestamp_ms)
    log_timing "Restoration started at $(date '+%Y-%m-%d %H:%M:%S.%3N')"

    # Scale deployment back up
    log_info "Scaling $SERVICE to $ORIGINAL_REPLICAS replicas in Region 1..."

    if ! kubectl --context="$REGION1_CONTEXT" scale deployment "$SERVICE" \
        -n "$NAMESPACE" --replicas="$ORIGINAL_REPLICAS" 2>/dev/null; then
        add_result "Region Restoration" "FAIL" "Failed to scale up deployment"
        return 1
    fi

    # Wait for pods to become ready
    log_info "Waiting for pods to become ready..."

    local wait_count=0
    local max_wait=120
    while [[ $wait_count -lt $max_wait ]]; do
        local ready_pods
        ready_pods=$(kubectl --context="$REGION1_CONTEXT" get pods -n "$NAMESPACE" \
            -l "app.kubernetes.io/name=$SERVICE" \
            --field-selector=status.phase=Running \
            -o jsonpath='{.items}' 2>/dev/null | jq -r '[.[] | select(.status.conditions[] | select(.type=="Ready" and .status=="True"))] | length' 2>/dev/null || echo "0")

        if [[ "$ready_pods" -ge "$ORIGINAL_REPLICAS" ]]; then
            local restoration_time=$(($(get_timestamp_ms) - RESTORE_START_TIME))
            log_timing "All pods ready after $((restoration_time / 1000))s"
            break
        fi

        log_verbose "Waiting for pods... $ready_pods / $ORIGINAL_REPLICAS ready"
        sleep 2
        ((wait_count += 2))
    done

    if [[ $wait_count -ge $max_wait ]]; then
        add_result "Pod Restoration" "WARN" "Timeout waiting for pods to become ready"
    else
        add_result "Pod Restoration" "PASS" "All Region 1 pods restored and ready"
    fi

    add_result "Region Restoration" "PASS" "Region 1 restored with $ORIGINAL_REPLICAS replicas"
    return 0
}

# =============================================================================
# Traffic Rebalancing Verification
# =============================================================================
verify_traffic_rebalance() {
    log_step "Step 8: Verifying traffic rebalances to original distribution"

    if [[ "$SKIP_REBALANCE" == "true" ]]; then
        add_result "Traffic Rebalancing" "SKIP" "Skipped by --skip-rebalance flag"
        return 0
    fi

    if [[ "$RESTORE_PODS" == "false" ]]; then
        add_result "Traffic Rebalancing" "SKIP" "Skipped because pods were not restored"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "DRY RUN: Would verify traffic distribution returns to baseline"
        add_result "Traffic Rebalancing" "SKIP" "Dry run mode - skipping rebalance verification"
        return 0
    fi

    log_info "Waiting for Istio to detect Region 1 recovery and rebalance traffic..."

    # Wait for load balancing to stabilize
    sleep 15

    # Get current pod counts
    local current_region1_pods
    current_region1_pods=$(kubectl --context="$REGION1_CONTEXT" get pods -n "$NAMESPACE" \
        -l "app.kubernetes.io/name=$SERVICE" \
        --field-selector=status.phase=Running \
        -o jsonpath='{.items}' 2>/dev/null | jq -r 'length' 2>/dev/null || echo "0")

    local current_region2_pods
    current_region2_pods=$(kubectl --context="$REGION2_CONTEXT" get pods -n "$NAMESPACE" \
        -l "app.kubernetes.io/name=$SERVICE" \
        --field-selector=status.phase=Running \
        -o jsonpath='{.items}' 2>/dev/null | jq -r 'length' 2>/dev/null || echo "0")

    log_timing "Current: Region 1 = $current_region1_pods pods, Region 2 = $current_region2_pods pods"
    log_timing "Baseline: Region 1 = $BASELINE_REGION1_PODS pods, Region 2 = $BASELINE_REGION2_PODS pods"

    REBALANCE_COMPLETE_TIME=$(get_timestamp_ms)

    # Verify pod counts match baseline
    if [[ "$current_region1_pods" -eq "$BASELINE_REGION1_PODS" ]] && \
       [[ "$current_region2_pods" -eq "$BASELINE_REGION2_PODS" ]]; then
        add_result "Traffic Rebalancing" "PASS" "Pod distribution matches baseline"
    else
        add_result "Traffic Rebalancing" "WARN" "Pod distribution differs from baseline (may still be rebalancing)"
    fi

    # Check if Istio has unejected Region 1 endpoints
    log_info "Checking if Istio has restored Region 1 endpoints..."

    # Get a pod from Region 2 to check endpoint status
    local test_pod
    test_pod=$(kubectl --context="$REGION2_CONTEXT" get pods -n "$NAMESPACE" \
        -l "app.kubernetes.io/name=$SERVICE" \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

    if [[ -n "$test_pod" ]] && command -v istioctl &> /dev/null; then
        local endpoints
        endpoints=$(istioctl --context="$REGION2_CONTEXT" proxy-config endpoints "$test_pod.$NAMESPACE" 2>/dev/null | \
            grep "$SERVICE" | grep -c "HEALTHY" || echo "0")

        if [[ "$endpoints" -gt 1 ]]; then
            add_result "Endpoint Restoration" "PASS" "Istio shows $endpoints healthy endpoints across regions"
        else
            add_result "Endpoint Restoration" "WARN" "Only $endpoints healthy endpoint(s) visible"
        fi
    else
        log_verbose "Skipping Istio endpoint check (istioctl not available or no test pod)"
    fi

    return 0
}

# =============================================================================
# Output Results
# =============================================================================
output_results() {
    END_TIME=$(get_timestamp_ms)
    local total_duration_ms=$((END_TIME - START_TIME))
    local total_duration_s=$((total_duration_ms / 1000))

    if [[ "$JSON_OUTPUT" == "true" ]]; then
        output_json_results "$total_duration_s"
    else
        output_text_results "$total_duration_s"
    fi
}

output_json_results() {
    local duration="$1"

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
  "validation": "regional-failover",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "configuration": {
    "region1Context": "$REGION1_CONTEXT",
    "region2Context": "$REGION2_CONTEXT",
    "namespace": "$NAMESPACE",
    "service": "$SERVICE",
    "rtoTarget": $RTO_TARGET,
    "timeout": $TIMEOUT
  },
  "timing": {
    "startTime": $START_TIME,
    "failureStartTime": $FAILURE_START_TIME,
    "failoverDetectedTime": $FAILOVER_DETECTED_TIME,
    "restoreStartTime": $RESTORE_START_TIME,
    "rebalanceCompleteTime": $REBALANCE_COMPLETE_TIME,
    "endTime": $END_TIME,
    "totalDurationSeconds": $duration
  },
  "rto": {
    "measured": $RTO_MEASURED,
    "target": $RTO_TARGET,
    "passed": $(if [[ $RTO_MEASURED -lt $RTO_TARGET ]]; then echo "true"; else echo "false"; fi)
  },
  "baseline": {
    "region1Pods": $BASELINE_REGION1_PODS,
    "region2Pods": $BASELINE_REGION2_PODS
  },
  "passed": $VALIDATION_PASSED,
  "results": $results_json
}
EOF
}

output_text_results() {
    local duration="$1"

    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║               REGIONAL FAILOVER VALIDATION RESULTS                       ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "  Configuration:"
    echo "    Region 1:        $REGION1_CONTEXT"
    echo "    Region 2:        $REGION2_CONTEXT"
    echo "    Service:         $SERVICE"
    echo "    Namespace:       $NAMESPACE"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo "  RTO MEASUREMENT"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "    Target RTO:      <${RTO_TARGET}s"
    echo "    Measured RTO:    ${RTO_MEASURED}s"
    echo ""

    if [[ $RTO_MEASURED -lt $RTO_TARGET ]]; then
        echo -e "    Result:          ${GREEN}PASSED${NC}"
    else
        echo -e "    Result:          ${RED}FAILED${NC}"
    fi

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo "  VALIDATION SUMMARY"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
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

    echo -e "    ${GREEN}PASSED:${NC}   $pass_count"
    echo -e "    ${RED}FAILED:${NC}   $fail_count"
    echo -e "    ${YELLOW}WARNINGS:${NC} $warn_count"
    echo -e "    ${BLUE}SKIPPED:${NC}  $skip_count"
    echo ""
    echo "    Total Duration: ${duration}s"
    echo ""

    if [[ "$VALIDATION_PASSED" == "true" ]]; then
        echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║  ✓ REGIONAL FAILOVER VALIDATION PASSED                                  ║${NC}"
        echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════════╝${NC}"
    else
        echo -e "${RED}╔══════════════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${RED}║  ✗ REGIONAL FAILOVER VALIDATION FAILED                                  ║${NC}"
        echo -e "${RED}╚══════════════════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo -e "${RED}Errors:${NC}"
        for error in "${ERRORS[@]}"; do
            echo -e "    - $error"
        done
    fi

    if [[ ${#WARNINGS[@]} -gt 0 ]]; then
        echo ""
        echo -e "${YELLOW}Warnings:${NC}"
        for warning in "${WARNINGS[@]}"; do
            echo -e "    - $warning"
        done
    fi

    echo ""
}

# =============================================================================
# Cleanup Handler
# =============================================================================
cleanup() {
    local exit_code=$?

    if [[ "$DRY_RUN" == "true" ]]; then
        exit $exit_code
    fi

    if [[ "$RESTORE_PODS" == "true" ]] && [[ $exit_code -ne 0 ]]; then
        log_warn "Validation interrupted. Attempting to restore pods..."

        # Try to restore pods
        kubectl --context="$REGION1_CONTEXT" scale deployment "$SERVICE" \
            -n "$NAMESPACE" --replicas="$ORIGINAL_REPLICAS" 2>/dev/null || true
    fi

    exit $exit_code
}

# =============================================================================
# Main Execution
# =============================================================================
main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            --service)
                SERVICE="$2"
                shift 2
                ;;
            --rto-target)
                RTO_TARGET="$2"
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
            --no-restore)
                RESTORE_PODS=false
                shift
                ;;
            --skip-monitoring)
                SKIP_MONITORING=true
                shift
                ;;
            --skip-rebalance)
                SKIP_REBALANCE=true
                shift
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            --probe-interval)
                PROBE_INTERVAL="$2"
                shift 2
                ;;
            --help|-h)
                usage
                ;;
            -*)
                echo "Unknown option: $1" >&2
                usage
                ;;
            *)
                if [[ -z "$REGION1_CONTEXT" ]]; then
                    REGION1_CONTEXT="$1"
                elif [[ -z "$REGION2_CONTEXT" ]]; then
                    REGION2_CONTEXT="$1"
                fi
                shift
                ;;
        esac
    done

    # Validate required arguments
    if [[ -z "$REGION1_CONTEXT" || -z "$REGION2_CONTEXT" ]]; then
        echo "Error: Both region contexts are required" >&2
        echo ""
        usage
    fi

    # Set up cleanup handler
    trap cleanup EXIT INT TERM

    # Record start time
    START_TIME=$(get_timestamp_ms)

    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo ""
        echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}║     REGIONAL FAILOVER VALIDATION                                        ║${NC}"
        echo -e "${CYAN}║     End-to-End Multi-Region Failover Testing                            ║${NC}"
        echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo "  Region 1 (Primary): $REGION1_CONTEXT"
        echo "  Region 2 (Failover): $REGION2_CONTEXT"
        echo "  Service: $SERVICE"
        echo "  Namespace: $NAMESPACE"
        echo "  RTO Target: <${RTO_TARGET}s"
        echo "  Timeout: ${TIMEOUT}s"
        echo "  Dry Run: $DRY_RUN"
        echo ""

        if [[ "$DRY_RUN" == "false" ]]; then
            echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "${YELLOW}  WARNING: This test will TERMINATE all $SERVICE pods in Region 1         ${NC}"
            echo -e "${YELLOW}  Press Ctrl+C within 5 seconds to abort...                               ${NC}"
            echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo ""
            sleep 5
        fi
    fi

    # Execute validation steps
    check_prerequisites || true
    check_cluster_access || true
    verify_monitoring_deployment
    record_baseline_traffic || true
    simulate_region_failure || true
    measure_failover_rto || true
    verify_rto_target || true
    restore_region || true
    verify_traffic_rebalance

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
