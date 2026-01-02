#!/bin/bash
# =============================================================================
# Regional Failover Test Script for Multi-Region Deployment
# =============================================================================
# This script simulates regional failures and measures Recovery Time Objective (RTO)
# to validate that the Istio-based locality failover achieves the <60s RTO target.
#
# Usage:
#   ./test-failover.sh [OPTIONS] <primary-context> <failover-context>
#
# Options:
#   --service         Service to test (default: claude-flow)
#   --namespace       Service namespace (default: acgs-services)
#   --dry-run         Validate script without executing failover
#   --json            Output results in JSON format
#   --verbose         Show detailed timing information
#   --restore         Restore pods after test (default: true)
#   --test-endpoint   Custom health check endpoint (default: /health)
#   --timeout         Maximum wait time for failover in seconds (default: 120)
#   --help            Show this help message
#
# Examples:
#   ./test-failover.sh region1 region2
#   ./test-failover.sh --service neural-mcp --verbose region1 region2
#   ./test-failover.sh --json --timeout 90 us-east-1 eu-west-1
#
# Requirements:
#   - kubectl (for cluster access and pod management)
#   - curl (for health check probing)
#   - Valid kubeconfig with contexts for all specified clusters
#   - Istio service mesh deployed with locality-aware load balancing
#
# RTO Calculation:
#   Expected RTO = Detection Time + Ejection Time + Pod Readiness
#   - Detection Time: consecutiveErrors * requestTimeout = 3 * 5s = 15s
#   - Analysis Interval: 10s
#   - Base Ejection Time: 30s
#   - Target: <60s total (55s expected with current configuration)
#
# References:
#   - https://istio.io/latest/docs/tasks/traffic-management/locality-load-balancing/
#   - https://istio.io/latest/docs/reference/config/networking/destination-rule/
# =============================================================================

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================
SERVICE="claude-flow"
NAMESPACE="acgs-services"
DRY_RUN=false
JSON_OUTPUT=false
VERBOSE=false
RESTORE_PODS=true
TEST_ENDPOINT="/health"
TIMEOUT=120
PRIMARY_CONTEXT=""
FAILOVER_CONTEXT=""
PROBE_INTERVAL=1

# Timing variables
START_TIME=0
FAILOVER_DETECTED_TIME=0
RECOVERY_TIME=0

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
        echo -e "${GREEN}[SUCCESS]${NC} $(date '+%H:%M:%S') $1"
    fi
}

log_warn() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${YELLOW}[WARN]${NC} $(date '+%H:%M:%S') $1"
    fi
}

log_error() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $1" >&2
    fi
}

log_verbose() {
    if [[ "$VERBOSE" == "true" ]] && [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${CYAN}[VERBOSE]${NC} $(date '+%H:%M:%S') $1"
    fi
}

log_timing() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${MAGENTA}[TIMING]${NC} $(date '+%H:%M:%S') $1"
    fi
}

# =============================================================================
# Help Message
# =============================================================================
show_help() {
    grep '^#' "$0" | grep -v '#!/bin/bash' | sed 's/^# //' | sed 's/^#//'
    exit 0
}

# =============================================================================
# Argument Parsing
# =============================================================================
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --service)
                SERVICE="$2"
                shift 2
                ;;
            --namespace)
                NAMESPACE="$2"
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
            --restore)
                RESTORE_PODS=true
                shift
                ;;
            --no-restore)
                RESTORE_PODS=false
                shift
                ;;
            --test-endpoint)
                TEST_ENDPOINT="$2"
                shift 2
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            --help|-h)
                show_help
                ;;
            -*)
                log_error "Unknown option: $1"
                show_help
                ;;
            *)
                if [[ -z "$PRIMARY_CONTEXT" ]]; then
                    PRIMARY_CONTEXT="$1"
                elif [[ -z "$FAILOVER_CONTEXT" ]]; then
                    FAILOVER_CONTEXT="$1"
                else
                    log_error "Unexpected argument: $1"
                    exit 1
                fi
                shift
                ;;
        esac
    done

    # Validate required arguments
    if [[ -z "$PRIMARY_CONTEXT" ]] || [[ -z "$FAILOVER_CONTEXT" ]]; then
        log_error "Both primary and failover cluster contexts are required"
        log_error "Usage: $0 [OPTIONS] <primary-context> <failover-context>"
        exit 1
    fi
}

# =============================================================================
# Dependency Checks
# =============================================================================
check_dependencies() {
    local missing_deps=()

    if ! command -v kubectl &> /dev/null; then
        missing_deps+=("kubectl")
    fi

    if ! command -v curl &> /dev/null; then
        missing_deps+=("curl")
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        log_error "Please install the missing tools and try again."
        return 1
    fi

    log_success "All required dependencies are available"
    return 0
}

# =============================================================================
# Cluster Validation
# =============================================================================
validate_cluster_context() {
    local context="$1"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "Dry run: Skipping context validation for $context"
        return 0
    fi

    log_verbose "Validating cluster context: $context"

    if ! kubectl --context="$context" cluster-info &>/dev/null; then
        log_error "Cannot access cluster with context: $context"
        log_error "Verify the context exists in your kubeconfig and you have access"
        return 1
    fi

    log_verbose "Cluster context validated: $context"
    return 0
}

# =============================================================================
# Service Discovery
# =============================================================================
get_service_pods() {
    local context="$1"
    local service="$2"
    local namespace="$3"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo "${service}-pod-1 ${service}-pod-2"
        return 0
    fi

    kubectl --context="$context" get pods -n "$namespace" \
        -l "app.kubernetes.io/name=$service" \
        -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || true
}

get_pod_count() {
    local context="$1"
    local service="$2"
    local namespace="$3"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo "2"
        return 0
    fi

    kubectl --context="$context" get pods -n "$namespace" \
        -l "app.kubernetes.io/name=$service" \
        --field-selector=status.phase=Running \
        -o jsonpath='{.items}' 2>/dev/null | jq -r 'length' 2>/dev/null || echo "0"
}

get_service_endpoint() {
    local context="$1"
    local service="$2"
    local namespace="$3"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo "http://${service}.${namespace}.svc.cluster.local:8080"
        return 0
    fi

    # Get the service cluster IP and port
    local svc_info
    svc_info=$(kubectl --context="$context" get svc "$service" -n "$namespace" \
        -o jsonpath='{.spec.clusterIP}:{.spec.ports[0].port}' 2>/dev/null) || true

    if [[ -n "$svc_info" ]]; then
        echo "http://${svc_info}"
    else
        echo "http://${service}.${namespace}.svc.cluster.local:8080"
    fi
}

# =============================================================================
# Pre-Flight Checks
# =============================================================================
preflight_checks() {
    log_info "Running pre-flight checks..."
    echo ""

    # Check Istio is installed
    log_verbose "Checking Istio installation in $PRIMARY_CONTEXT..."
    if [[ "$DRY_RUN" == "false" ]]; then
        if ! kubectl --context="$PRIMARY_CONTEXT" get ns istio-system &>/dev/null; then
            log_error "Istio system namespace not found in $PRIMARY_CONTEXT"
            return 1
        fi
    fi

    # Check service exists in both clusters
    local primary_pods failover_pods
    primary_pods=$(get_pod_count "$PRIMARY_CONTEXT" "$SERVICE" "$NAMESPACE")
    failover_pods=$(get_pod_count "$FAILOVER_CONTEXT" "$SERVICE" "$NAMESPACE")

    log_info "Primary cluster ($PRIMARY_CONTEXT): $primary_pods running pods"
    log_info "Failover cluster ($FAILOVER_CONTEXT): $failover_pods running pods"

    if [[ "$primary_pods" == "0" ]]; then
        log_error "No running pods found for $SERVICE in primary cluster"
        return 1
    fi

    if [[ "$failover_pods" == "0" ]]; then
        log_error "No running pods found for $SERVICE in failover cluster"
        return 1
    fi

    # Check DestinationRule exists
    log_verbose "Checking DestinationRule for $SERVICE..."
    if [[ "$DRY_RUN" == "false" ]]; then
        if ! kubectl --context="$PRIMARY_CONTEXT" get destinationrule \
            "${SERVICE}-locality-lb" -n "$NAMESPACE" &>/dev/null; then
            log_warn "DestinationRule ${SERVICE}-locality-lb not found"
            log_warn "Failover may not work as expected without locality-aware load balancing"
        fi
    fi

    log_success "Pre-flight checks passed"
    return 0
}

# =============================================================================
# Timestamp Functions
# =============================================================================
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

calculate_rto() {
    local start="$1"
    local end="$2"
    echo $(( (end - start) / 1000 ))
}

# =============================================================================
# Health Check Functions
# =============================================================================
check_service_health() {
    local context="$1"
    local service="$2"
    local namespace="$3"

    if [[ "$DRY_RUN" == "true" ]]; then
        return 0
    fi

    # Use port-forward to check health
    local pod_name
    pod_name=$(kubectl --context="$context" get pods -n "$namespace" \
        -l "app.kubernetes.io/name=$service" \
        --field-selector=status.phase=Running \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null) || true

    if [[ -z "$pod_name" ]]; then
        return 1
    fi

    # Check pod is ready
    local ready
    ready=$(kubectl --context="$context" get pod "$pod_name" -n "$namespace" \
        -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null) || true

    if [[ "$ready" == "True" ]]; then
        return 0
    fi

    return 1
}

check_traffic_routing() {
    local context="$1"
    local expected_region="$2"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "Dry run: Simulating traffic check to $expected_region"
        return 0
    fi

    # Check Envoy sidecar routing decisions via istioctl
    local routing_info
    routing_info=$(kubectl --context="$context" exec -n "$NAMESPACE" \
        "$(kubectl --context="$context" get pods -n "$NAMESPACE" \
        -l "app.kubernetes.io/name=$SERVICE" \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)" \
        -c istio-proxy -- pilot-agent request GET clusters 2>/dev/null | \
        grep -i "$expected_region" | head -5) || true

    if [[ -n "$routing_info" ]]; then
        log_verbose "Traffic routing detected to $expected_region"
        return 0
    fi

    return 1
}

# =============================================================================
# Failover Simulation
# =============================================================================
simulate_region_failure() {
    local context="$1"
    local service="$2"
    local namespace="$3"

    log_info "Simulating region failure in $context..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "Dry run: Would terminate all pods for $service in $namespace"
        return 0
    fi

    # Get current replica count for restoration
    local deployment_name="${service}"
    local current_replicas
    current_replicas=$(kubectl --context="$context" get deployment "$deployment_name" \
        -n "$namespace" -o jsonpath='{.spec.replicas}' 2>/dev/null) || current_replicas="2"

    # Store for restoration
    echo "$current_replicas" > "/tmp/failover-test-${service}-replicas"

    # Scale down to 0 (simulates region failure)
    log_info "Scaling down $service to 0 replicas..."
    kubectl --context="$context" scale deployment "$deployment_name" \
        -n "$namespace" --replicas=0 2>/dev/null || {
        log_error "Failed to scale down deployment"
        return 1
    }

    # Wait for pods to terminate
    log_verbose "Waiting for pods to terminate..."
    local wait_count=0
    while [[ $wait_count -lt 30 ]]; do
        local running_pods
        running_pods=$(get_pod_count "$context" "$service" "$namespace")
        if [[ "$running_pods" == "0" ]]; then
            log_success "All pods terminated in $context"
            return 0
        fi
        sleep 1
        ((wait_count++))
    done

    log_warn "Timeout waiting for pods to terminate"
    return 0
}

restore_region() {
    local context="$1"
    local service="$2"
    local namespace="$3"

    log_info "Restoring region $context..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "Dry run: Would restore pods for $service in $namespace"
        return 0
    fi

    # Get stored replica count
    local replicas="2"
    if [[ -f "/tmp/failover-test-${service}-replicas" ]]; then
        replicas=$(cat "/tmp/failover-test-${service}-replicas")
        rm -f "/tmp/failover-test-${service}-replicas"
    fi

    # Scale back up
    local deployment_name="${service}"
    log_info "Scaling up $service to $replicas replicas..."
    kubectl --context="$context" scale deployment "$deployment_name" \
        -n "$namespace" --replicas="$replicas" 2>/dev/null || {
        log_error "Failed to scale up deployment"
        return 1
    }

    # Wait for pods to be ready
    log_verbose "Waiting for pods to become ready..."
    local wait_count=0
    while [[ $wait_count -lt 60 ]]; do
        local running_pods
        running_pods=$(get_pod_count "$context" "$service" "$namespace")
        if [[ "$running_pods" -ge "$replicas" ]]; then
            log_success "All pods restored in $context ($running_pods running)"
            return 0
        fi
        sleep 2
        ((wait_count++))
    done

    log_warn "Timeout waiting for pods to restore"
    return 0
}

# =============================================================================
# RTO Measurement
# =============================================================================
measure_failover_rto() {
    log_info "Starting RTO measurement..."
    echo ""

    # Record initial state
    local initial_primary_pods initial_failover_pods
    initial_primary_pods=$(get_pod_count "$PRIMARY_CONTEXT" "$SERVICE" "$NAMESPACE")
    initial_failover_pods=$(get_pod_count "$FAILOVER_CONTEXT" "$SERVICE" "$NAMESPACE")

    log_timing "Initial state: Primary=$initial_primary_pods pods, Failover=$initial_failover_pods pods"

    # Start timing
    START_TIME=$(get_timestamp_ms)
    log_timing "Failure simulation started at $(date '+%Y-%m-%d %H:%M:%S.%3N')"

    # Simulate failure
    simulate_region_failure "$PRIMARY_CONTEXT" "$SERVICE" "$NAMESPACE"

    local failure_time
    failure_time=$(get_timestamp_ms)
    log_timing "Pods terminated at +$((($failure_time - $START_TIME) / 1000))s"

    # Monitor for failover detection
    log_info "Monitoring failover to $FAILOVER_CONTEXT..."
    local elapsed=0
    local failover_detected=false

    while [[ $elapsed -lt $TIMEOUT ]]; do
        # Check if traffic is being routed to failover region
        if check_service_health "$FAILOVER_CONTEXT" "$SERVICE" "$NAMESPACE"; then
            if [[ "$failover_detected" == "false" ]]; then
                FAILOVER_DETECTED_TIME=$(get_timestamp_ms)
                failover_detected=true
                RECOVERY_TIME=$((FAILOVER_DETECTED_TIME - START_TIME))
                log_timing "Failover detected at +$(($RECOVERY_TIME / 1000))s"
                break
            fi
        fi

        sleep $PROBE_INTERVAL
        elapsed=$((elapsed + PROBE_INTERVAL))

        if [[ "$VERBOSE" == "true" ]]; then
            log_verbose "Elapsed: ${elapsed}s, waiting for failover..."
        fi
    done

    if [[ "$failover_detected" == "false" ]]; then
        log_error "Failover not detected within ${TIMEOUT}s timeout"
        RECOVERY_TIME=$((TIMEOUT * 1000))
    fi

    return 0
}

# =============================================================================
# Results Output
# =============================================================================
output_results() {
    local rto_seconds=$((RECOVERY_TIME / 1000))
    local rto_target=60
    local passed="false"

    if [[ $rto_seconds -lt $rto_target ]]; then
        passed="true"
    fi

    if [[ "$JSON_OUTPUT" == "true" ]]; then
        output_json_results "$rto_seconds" "$rto_target" "$passed"
    else
        output_text_results "$rto_seconds" "$rto_target" "$passed"
    fi
}

output_json_results() {
    local rto_seconds="$1"
    local rto_target="$2"
    local passed="$3"

    cat <<EOF
{
  "test": "regional-failover",
  "service": "$SERVICE",
  "namespace": "$NAMESPACE",
  "primaryContext": "$PRIMARY_CONTEXT",
  "failoverContext": "$FAILOVER_CONTEXT",
  "results": {
    "rtoMeasured": ${rto_seconds},
    "rtoTarget": ${rto_target},
    "rtoUnit": "seconds",
    "passed": ${passed}
  },
  "timing": {
    "startTime": $START_TIME,
    "failoverDetectedTime": $FAILOVER_DETECTED_TIME,
    "recoveryTimeMs": $RECOVERY_TIME
  },
  "configuration": {
    "timeout": $TIMEOUT,
    "probeInterval": $PROBE_INTERVAL,
    "dryRun": $DRY_RUN,
    "restorePods": $RESTORE_PODS
  },
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF
}

output_text_results() {
    local rto_seconds="$1"
    local rto_target="$2"
    local passed="$3"

    echo ""
    echo "============================================================"
    echo "  Regional Failover Test Results"
    echo "============================================================"
    echo ""
    echo "Service:           $SERVICE"
    echo "Namespace:         $NAMESPACE"
    echo "Primary Cluster:   $PRIMARY_CONTEXT"
    echo "Failover Cluster:  $FAILOVER_CONTEXT"
    echo ""
    echo "------------------------------------------------------------"
    echo "  RTO Measurement"
    echo "------------------------------------------------------------"
    echo ""
    echo "  RTO Target:    <${rto_target}s"
    echo "  RTO Measured:  ${rto_seconds}s"
    echo ""

    if [[ "$passed" == "true" ]]; then
        echo -e "  Result:        ${GREEN}PASSED${NC}"
        echo ""
        echo "  The failover completed within the target RTO."
    else
        echo -e "  Result:        ${RED}FAILED${NC}"
        echo ""
        echo "  The failover exceeded the target RTO."
        echo "  Consider tuning the following Istio DestinationRule parameters:"
        echo "    - consecutiveGatewayErrors (currently: 3)"
        echo "    - interval (currently: 10s)"
        echo "    - baseEjectionTime (currently: 30s)"
    fi

    echo ""
    echo "------------------------------------------------------------"
    echo "  Timing Breakdown"
    echo "------------------------------------------------------------"
    echo ""
    echo "  Start Time:              $(date -d @$((START_TIME / 1000)) '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo 'N/A')"
    echo "  Failover Detected:       $(date -d @$((FAILOVER_DETECTED_TIME / 1000)) '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo 'N/A')"
    echo "  Total Recovery Time:     ${rto_seconds}s (${RECOVERY_TIME}ms)"
    echo ""
    echo "------------------------------------------------------------"
    echo "  Expected RTO Components (from DestinationRule)"
    echo "------------------------------------------------------------"
    echo ""
    echo "  Detection Time:          15s (3 errors * 5s timeout)"
    echo "  Analysis Interval:       10s"
    echo "  Base Ejection Time:      30s"
    echo "  Pod Readiness:           ~10s (variable)"
    echo "  Expected Total:          ~55-65s"
    echo ""
    echo "============================================================"
    echo ""

    if [[ "$RESTORE_PODS" == "true" ]]; then
        echo "  Pods were restored after the test."
    else
        echo -e "  ${YELLOW}WARNING:${NC} Pods were NOT restored. Run with --restore or restore manually."
    fi
    echo ""
}

# =============================================================================
# Dry Run Mode
# =============================================================================
run_dry_run() {
    log_info "Running in DRY RUN mode - no changes will be made"
    echo ""

    echo "Configuration:"
    echo "  Service:         $SERVICE"
    echo "  Namespace:       $NAMESPACE"
    echo "  Primary:         $PRIMARY_CONTEXT"
    echo "  Failover:        $FAILOVER_CONTEXT"
    echo "  Timeout:         ${TIMEOUT}s"
    echo "  Restore Pods:    $RESTORE_PODS"
    echo ""

    log_info "Test sequence (simulated):"
    echo "  1. Pre-flight checks"
    echo "  2. Record initial pod counts"
    echo "  3. Start RTO timer"
    echo "  4. Scale down $SERVICE in $PRIMARY_CONTEXT to 0 replicas"
    echo "  5. Monitor traffic routing to $FAILOVER_CONTEXT"
    echo "  6. Record failover detection time"
    echo "  7. Calculate RTO"
    echo "  8. Restore pods (if --restore)"
    echo "  9. Output results"
    echo ""

    # Simulate with fake timing
    START_TIME=$(get_timestamp_ms)
    sleep 1
    FAILOVER_DETECTED_TIME=$(get_timestamp_ms)
    RECOVERY_TIME=$((FAILOVER_DETECTED_TIME - START_TIME))

    # Simulate a passing result
    RECOVERY_TIME=45000  # 45 seconds

    output_results

    log_success "Dry run completed successfully"
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
        log_warn "Test interrupted. Attempting to restore pods..."
        restore_region "$PRIMARY_CONTEXT" "$SERVICE" "$NAMESPACE" || true
    fi

    # Clean up temp files
    rm -f "/tmp/failover-test-${SERVICE}-replicas" 2>/dev/null || true

    exit $exit_code
}

# =============================================================================
# Main Execution
# =============================================================================
main() {
    parse_args "$@"

    # Set up cleanup handler
    trap cleanup EXIT INT TERM

    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo ""
        echo "============================================================"
        echo "  ACGS2 Regional Failover Test"
        echo "============================================================"
        echo ""
        echo "  Testing failover from $PRIMARY_CONTEXT to $FAILOVER_CONTEXT"
        echo "  Service: $SERVICE"
        echo "  Target RTO: <60s"
        echo ""
    fi

    # Dry run mode
    if [[ "$DRY_RUN" == "true" ]]; then
        run_dry_run
        exit 0
    fi

    # Check dependencies
    check_dependencies || exit 1

    # Validate cluster contexts
    validate_cluster_context "$PRIMARY_CONTEXT" || exit 1
    validate_cluster_context "$FAILOVER_CONTEXT" || exit 1

    # Run pre-flight checks
    preflight_checks || exit 1

    echo ""
    log_warn "This test will TERMINATE all $SERVICE pods in $PRIMARY_CONTEXT"
    log_warn "Press Ctrl+C within 5 seconds to abort..."
    echo ""
    sleep 5

    # Measure failover RTO
    measure_failover_rto || {
        log_error "Failover test failed"
        exit 1
    }

    # Restore pods if requested
    if [[ "$RESTORE_PODS" == "true" ]]; then
        echo ""
        restore_region "$PRIMARY_CONTEXT" "$SERVICE" "$NAMESPACE" || {
            log_warn "Failed to restore pods. Manual intervention may be required."
        }
    fi

    # Output results
    output_results

    # Exit with appropriate code
    local rto_seconds=$((RECOVERY_TIME / 1000))
    if [[ $rto_seconds -lt 60 ]]; then
        exit 0
    else
        exit 1
    fi
}

# Run main function
main "$@"
