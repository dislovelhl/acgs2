#!/bin/bash
# =============================================================================
# Cross-Cluster Service Discovery Validation Script
# =============================================================================
# This script validates cross-cluster service discovery, mTLS communication,
# and Istio mesh connectivity between multi-region deployments.
#
# Usage:
#   ./validate-service-discovery.sh [OPTIONS] <region1-context> <region2-context>
#
# Options:
#   --namespace       Service namespace (default: acgs-services)
#   --dry-run         Show validation steps without executing
#   --json            Output results in JSON format
#   --verbose         Show detailed output including istioctl commands
#   --service         Specific service to test (default: all)
#   --skip-mtls       Skip mTLS certificate validation
#   --skip-http       Skip cross-region HTTP call test
#   --timeout         Timeout for HTTP requests in seconds (default: 30)
#   --help            Show this help message
#
# Examples:
#   ./validate-service-discovery.sh region1 region2
#   ./validate-service-discovery.sh --verbose --json us-east-1 eu-west-1
#   ./validate-service-discovery.sh --service claude-flow region1 region2
#
# Requirements:
#   - kubectl with contexts for all specified clusters
#   - istioctl CLI installed and available
#   - curl for HTTP connectivity testing
#   - Istio service mesh deployed with multi-cluster configuration
#   - Services deployed in both regions
#
# Validation Steps:
#   1. Verify service deployment in both regions
#   2. Check Istio proxy-status for SYNCED state
#   3. Verify cross-cluster service discovery (services from region2 in region1)
#   4. Execute cross-region HTTP call from region1 to region2
#   5. Validate mTLS certificate chain
#
# References:
#   - https://istio.io/latest/docs/setup/install/multicluster/
#   - https://istio.io/latest/docs/ops/diagnostic-tools/istioctl/
# =============================================================================

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================
NAMESPACE="acgs-services"
DRY_RUN=false
JSON_OUTPUT=false
VERBOSE=false
SPECIFIC_SERVICE=""
SKIP_MTLS=false
SKIP_HTTP=false
HTTP_TIMEOUT=30
REGION1_CONTEXT=""
REGION2_CONTEXT=""

# Services to validate
SERVICES=("claude-flow" "neural-mcp")

# Results tracking
VALIDATION_PASSED=true
RESULTS=()
ERRORS=()

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

# =============================================================================
# Helper Functions
# =============================================================================
usage() {
    head -50 "$0" | grep -E '^#' | sed 's/^# *//' | tail -n +2
    exit 0
}

add_result() {
    local test_name="$1"
    local status="$2"
    local message="$3"
    local details="${4:-}"

    RESULTS+=("{\"test\": \"$test_name\", \"status\": \"$status\", \"message\": \"$message\", \"details\": \"$details\"}")

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

check_prerequisites() {
    log_step "Checking prerequisites"

    local missing_tools=()

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        missing_tools+=("kubectl")
    else
        log_verbose "kubectl found: $(kubectl version --client --short 2>/dev/null || kubectl version --client -o yaml | grep gitVersion | head -1)"
    fi

    # Check istioctl
    if ! command -v istioctl &> /dev/null; then
        missing_tools+=("istioctl")
    else
        log_verbose "istioctl found: $(istioctl version --remote=false 2>/dev/null || echo 'version check failed')"
    fi

    # Check curl
    if ! command -v curl &> /dev/null; then
        missing_tools+=("curl")
    else
        log_verbose "curl found: $(curl --version | head -1)"
    fi

    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        add_result "Prerequisites" "FAIL" "Missing required tools: ${missing_tools[*]}"
        return 1
    fi

    add_result "Prerequisites" "PASS" "All required tools available (kubectl, istioctl, curl)"
    return 0
}

check_cluster_access() {
    log_step "Verifying cluster access"

    # Check Region 1 access
    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "DRY RUN: Would check cluster access for context $REGION1_CONTEXT"
        log_verbose "DRY RUN: Would check cluster access for context $REGION2_CONTEXT"
        add_result "Cluster Access" "SKIP" "Dry run mode - skipping cluster access check"
        return 0
    fi

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
# Validation Step 1: Verify Service Deployment
# =============================================================================
validate_service_deployment() {
    log_step "Step 1: Verifying service deployments in both regions"

    local services_to_check=("${SERVICES[@]}")
    if [[ -n "$SPECIFIC_SERVICE" ]]; then
        services_to_check=("$SPECIFIC_SERVICE")
    fi

    for service in "${services_to_check[@]}"; do
        log_info "Checking $service deployment..."

        if [[ "$DRY_RUN" == "true" ]]; then
            log_verbose "DRY RUN: kubectl --context=$REGION1_CONTEXT get deployment $service -n $NAMESPACE"
            log_verbose "DRY RUN: kubectl --context=$REGION2_CONTEXT get deployment $service -n $NAMESPACE"
            continue
        fi

        # Check Region 1
        local r1_pods
        r1_pods=$(kubectl --context="$REGION1_CONTEXT" get pods -n "$NAMESPACE" -l "app=$service" -o jsonpath='{.items[*].status.phase}' 2>/dev/null || echo "")

        if [[ -z "$r1_pods" ]]; then
            add_result "Deployment ($service - Region 1)" "FAIL" "No pods found in $REGION1_CONTEXT"
        else
            local r1_running
            r1_running=$(echo "$r1_pods" | tr ' ' '\n' | grep -c "Running" || echo "0")
            if [[ "$r1_running" -gt 0 ]]; then
                add_result "Deployment ($service - Region 1)" "PASS" "$r1_running pod(s) running in $REGION1_CONTEXT"
            else
                add_result "Deployment ($service - Region 1)" "FAIL" "No running pods in $REGION1_CONTEXT (states: $r1_pods)"
            fi
        fi

        # Check Region 2
        local r2_pods
        r2_pods=$(kubectl --context="$REGION2_CONTEXT" get pods -n "$NAMESPACE" -l "app=$service" -o jsonpath='{.items[*].status.phase}' 2>/dev/null || echo "")

        if [[ -z "$r2_pods" ]]; then
            add_result "Deployment ($service - Region 2)" "FAIL" "No pods found in $REGION2_CONTEXT"
        else
            local r2_running
            r2_running=$(echo "$r2_pods" | tr ' ' '\n' | grep -c "Running" || echo "0")
            if [[ "$r2_running" -gt 0 ]]; then
                add_result "Deployment ($service - Region 2)" "PASS" "$r2_running pod(s) running in $REGION2_CONTEXT"
            else
                add_result "Deployment ($service - Region 2)" "FAIL" "No running pods in $REGION2_CONTEXT (states: $r2_pods)"
            fi
        fi
    done

    if [[ "$DRY_RUN" == "true" ]]; then
        add_result "Service Deployment" "SKIP" "Dry run mode - skipping deployment verification"
    fi
}

# =============================================================================
# Validation Step 2: Verify Istio Proxy Status
# =============================================================================
validate_proxy_status() {
    log_step "Step 2: Verifying Istio proxy-status (all proxies should be SYNCED)"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "DRY RUN: istioctl --context=$REGION1_CONTEXT proxy-status"
        log_verbose "DRY RUN: istioctl --context=$REGION2_CONTEXT proxy-status"
        add_result "Proxy Status" "SKIP" "Dry run mode - skipping proxy status check"
        return 0
    fi

    # Check Region 1 proxy status
    log_info "Checking Istio proxy status in Region 1..."
    local r1_status
    r1_status=$(istioctl --context="$REGION1_CONTEXT" proxy-status 2>/dev/null || echo "ERROR")

    if [[ "$r1_status" == "ERROR" ]]; then
        add_result "Proxy Status (Region 1)" "FAIL" "Failed to get proxy status from $REGION1_CONTEXT"
    else
        local r1_synced
        r1_synced=$(echo "$r1_status" | grep -c "SYNCED" || echo "0")
        local r1_not_synced
        r1_not_synced=$(echo "$r1_status" | grep -v "SYNCED" | grep -v "NAME" | grep -c "." || echo "0")

        if [[ "$r1_not_synced" -gt 0 ]]; then
            add_result "Proxy Status (Region 1)" "WARN" "$r1_synced proxies SYNCED, $r1_not_synced not fully synced"
            log_verbose "Region 1 proxy status:\n$r1_status"
        else
            add_result "Proxy Status (Region 1)" "PASS" "All $r1_synced proxies are SYNCED"
        fi
    fi

    # Check Region 2 proxy status
    log_info "Checking Istio proxy status in Region 2..."
    local r2_status
    r2_status=$(istioctl --context="$REGION2_CONTEXT" proxy-status 2>/dev/null || echo "ERROR")

    if [[ "$r2_status" == "ERROR" ]]; then
        add_result "Proxy Status (Region 2)" "FAIL" "Failed to get proxy status from $REGION2_CONTEXT"
    else
        local r2_synced
        r2_synced=$(echo "$r2_status" | grep -c "SYNCED" || echo "0")
        local r2_not_synced
        r2_not_synced=$(echo "$r2_status" | grep -v "SYNCED" | grep -v "NAME" | grep -c "." || echo "0")

        if [[ "$r2_not_synced" -gt 0 ]]; then
            add_result "Proxy Status (Region 2)" "WARN" "$r2_synced proxies SYNCED, $r2_not_synced not fully synced"
            log_verbose "Region 2 proxy status:\n$r2_status"
        else
            add_result "Proxy Status (Region 2)" "PASS" "All $r2_synced proxies are SYNCED"
        fi
    fi
}

# =============================================================================
# Validation Step 3: Verify Cross-Cluster Service Discovery
# =============================================================================
validate_cross_cluster_discovery() {
    log_step "Step 3: Verifying cross-cluster service discovery"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "DRY RUN: istioctl --context=$REGION1_CONTEXT proxy-config cluster <pod> | grep $REGION2_CONTEXT"
        log_verbose "DRY RUN: Check if services from Region 2 appear in Region 1 proxy config"
        add_result "Cross-Cluster Discovery" "SKIP" "Dry run mode - skipping discovery check"
        return 0
    fi

    local services_to_check=("${SERVICES[@]}")
    if [[ -n "$SPECIFIC_SERVICE" ]]; then
        services_to_check=("$SPECIFIC_SERVICE")
    fi

    for service in "${services_to_check[@]}"; do
        log_info "Checking cross-cluster discovery for $service..."

        # Get a pod from Region 1 to check its proxy config
        local test_pod
        test_pod=$(kubectl --context="$REGION1_CONTEXT" get pods -n "$NAMESPACE" -l "app=$service" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

        if [[ -z "$test_pod" ]]; then
            add_result "Cross-Cluster Discovery ($service)" "FAIL" "No pod found in Region 1 to check proxy config"
            continue
        fi

        log_verbose "Using pod $test_pod in Region 1 for discovery check"

        # Check if Region 2 endpoints appear in proxy config
        local endpoints
        endpoints=$(istioctl --context="$REGION1_CONTEXT" proxy-config endpoints "$test_pod.$NAMESPACE" 2>/dev/null || echo "ERROR")

        if [[ "$endpoints" == "ERROR" ]]; then
            add_result "Cross-Cluster Discovery ($service)" "FAIL" "Failed to get proxy config endpoints"
            continue
        fi

        # Look for service endpoints (check if we can see endpoints from the service mesh)
        local service_fqdn="${service}.${NAMESPACE}.svc.cluster.local"
        local endpoint_count
        endpoint_count=$(echo "$endpoints" | grep -c "$service_fqdn" || echo "0")

        if [[ "$endpoint_count" -gt 0 ]]; then
            # Check for multi-region endpoints
            local cluster_count
            cluster_count=$(echo "$endpoints" | grep "$service_fqdn" | awk '{print $5}' | sort -u | wc -l)

            if [[ "$cluster_count" -gt 1 ]]; then
                add_result "Cross-Cluster Discovery ($service)" "PASS" "Found $endpoint_count endpoints across $cluster_count clusters"
            else
                add_result "Cross-Cluster Discovery ($service)" "WARN" "Found $endpoint_count endpoints but only 1 cluster visible"
            fi
        else
            add_result "Cross-Cluster Discovery ($service)" "FAIL" "No endpoints found for $service_fqdn"
        fi

        # Additional check: Verify remote secrets exist
        local remote_secrets
        remote_secrets=$(kubectl --context="$REGION1_CONTEXT" get secrets -n istio-system -l istio/multiCluster=true -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")

        if [[ -n "$remote_secrets" ]]; then
            add_result "Remote Secrets (Region 1)" "PASS" "Remote secrets found: $remote_secrets"
        else
            add_result "Remote Secrets (Region 1)" "WARN" "No remote secrets found in istio-system"
        fi
    done
}

# =============================================================================
# Validation Step 4: Execute Cross-Region HTTP Call
# =============================================================================
validate_cross_region_http() {
    log_step "Step 4: Executing cross-region HTTP call"

    if [[ "$SKIP_HTTP" == "true" ]]; then
        add_result "Cross-Region HTTP" "SKIP" "Skipped by --skip-http flag"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "DRY RUN: Execute HTTP request from Region 1 pod to Region 2 service"
        log_verbose "DRY RUN: kubectl --context=$REGION1_CONTEXT exec <pod> -- curl -s http://<service>.$NAMESPACE.svc.cluster.local/health"
        add_result "Cross-Region HTTP" "SKIP" "Dry run mode - skipping HTTP call"
        return 0
    fi

    local services_to_check=("${SERVICES[@]}")
    if [[ -n "$SPECIFIC_SERVICE" ]]; then
        services_to_check=("$SPECIFIC_SERVICE")
    fi

    for service in "${services_to_check[@]}"; do
        log_info "Testing HTTP connectivity for $service..."

        # Get a source pod from Region 1
        local source_pod
        source_pod=$(kubectl --context="$REGION1_CONTEXT" get pods -n "$NAMESPACE" -l "app=$service" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

        if [[ -z "$source_pod" ]]; then
            add_result "Cross-Region HTTP ($service)" "FAIL" "No source pod found in Region 1"
            continue
        fi

        # Build service URL
        local service_url="http://${service}.${NAMESPACE}.svc.cluster.local:8080/health"
        log_verbose "Testing: $source_pod -> $service_url"

        # Execute HTTP call
        local http_result
        local http_code
        http_result=$(kubectl --context="$REGION1_CONTEXT" exec "$source_pod" -n "$NAMESPACE" -c "$service" -- \
            curl -s -o /dev/null -w "%{http_code}" --connect-timeout "$HTTP_TIMEOUT" "$service_url" 2>/dev/null || echo "000")

        if [[ "$http_result" == "200" ]]; then
            add_result "Cross-Region HTTP ($service)" "PASS" "HTTP call successful (status: $http_result)"
        elif [[ "$http_result" == "000" ]]; then
            add_result "Cross-Region HTTP ($service)" "FAIL" "Connection failed or timed out"
        else
            add_result "Cross-Region HTTP ($service)" "WARN" "HTTP call returned status: $http_result (expected 200)"
        fi

        # Test with specific routing header to force Region 2
        if [[ "$VERBOSE" == "true" ]]; then
            log_verbose "Testing with x-region-override header..."
            local override_result
            override_result=$(kubectl --context="$REGION1_CONTEXT" exec "$source_pod" -n "$NAMESPACE" -c "$service" -- \
                curl -s -o /dev/null -w "%{http_code}" -H "x-region-override: eu-west-1" \
                --connect-timeout "$HTTP_TIMEOUT" "$service_url" 2>/dev/null || echo "000")

            if [[ "$override_result" == "200" ]]; then
                add_result "Cross-Region HTTP (Override)" "PASS" "Region override routing works (status: $override_result)"
            else
                add_result "Cross-Region HTTP (Override)" "WARN" "Region override returned: $override_result"
            fi
        fi
    done
}

# =============================================================================
# Validation Step 5: Verify mTLS Certificate Validation
# =============================================================================
validate_mtls_certificates() {
    log_step "Step 5: Verifying mTLS certificate validation"

    if [[ "$SKIP_MTLS" == "true" ]]; then
        add_result "mTLS Validation" "SKIP" "Skipped by --skip-mtls flag"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "DRY RUN: istioctl --context=$REGION1_CONTEXT authn tls-check <pod>"
        log_verbose "DRY RUN: istioctl --context=$REGION1_CONTEXT pc secret <pod>"
        add_result "mTLS Validation" "SKIP" "Dry run mode - skipping mTLS check"
        return 0
    fi

    local services_to_check=("${SERVICES[@]}")
    if [[ -n "$SPECIFIC_SERVICE" ]]; then
        services_to_check=("$SPECIFIC_SERVICE")
    fi

    for service in "${services_to_check[@]}"; do
        log_info "Checking mTLS for $service..."

        # Get a pod from Region 1
        local test_pod
        test_pod=$(kubectl --context="$REGION1_CONTEXT" get pods -n "$NAMESPACE" -l "app=$service" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

        if [[ -z "$test_pod" ]]; then
            add_result "mTLS ($service)" "FAIL" "No pod found in Region 1 for mTLS check"
            continue
        fi

        # Check TLS configuration using istioctl authn tls-check
        local tls_check
        tls_check=$(istioctl --context="$REGION1_CONTEXT" authn tls-check "$test_pod.$NAMESPACE" 2>/dev/null || echo "ERROR")

        if [[ "$tls_check" == "ERROR" ]]; then
            # Try alternative method with proxy-config
            local secret_check
            secret_check=$(istioctl --context="$REGION1_CONTEXT" pc secret "$test_pod.$NAMESPACE" 2>/dev/null || echo "ERROR")

            if [[ "$secret_check" == "ERROR" ]]; then
                add_result "mTLS ($service)" "FAIL" "Failed to check mTLS configuration"
                continue
            fi

            # Check for valid certificates
            if echo "$secret_check" | grep -q "ACTIVE"; then
                add_result "mTLS ($service)" "PASS" "Active mTLS certificates found"
            else
                add_result "mTLS ($service)" "WARN" "mTLS certificates status unclear"
            fi
        else
            # Check if mTLS is enabled for mesh services
            local mtls_enabled
            mtls_enabled=$(echo "$tls_check" | grep -c "ISTIO_MUTUAL" || echo "0")

            if [[ "$mtls_enabled" -gt 0 ]]; then
                add_result "mTLS ($service)" "PASS" "ISTIO_MUTUAL TLS enabled for $mtls_enabled service(s)"
            else
                add_result "mTLS ($service)" "WARN" "ISTIO_MUTUAL not detected (check PeerAuthentication)"
            fi
        fi

        # Verify shared root CA
        log_verbose "Checking certificate chain..."
        local cert_info
        cert_info=$(istioctl --context="$REGION1_CONTEXT" pc secret "$test_pod.$NAMESPACE" -o json 2>/dev/null || echo "{}")

        if echo "$cert_info" | grep -q "ROOTCA"; then
            add_result "Root CA ($service)" "PASS" "Root CA certificate present"
        else
            add_result "Root CA ($service)" "WARN" "Root CA not found in certificate chain"
        fi
    done

    # Check PeerAuthentication policy
    log_info "Checking PeerAuthentication policies..."
    local peer_auth
    peer_auth=$(kubectl --context="$REGION1_CONTEXT" get peerauthentication -n istio-system -o jsonpath='{.items[0].spec.mtls.mode}' 2>/dev/null || echo "")

    if [[ "$peer_auth" == "STRICT" ]]; then
        add_result "PeerAuthentication" "PASS" "Mesh-wide STRICT mTLS enabled"
    elif [[ "$peer_auth" == "PERMISSIVE" ]]; then
        add_result "PeerAuthentication" "WARN" "PERMISSIVE mode - consider enabling STRICT for production"
    elif [[ -z "$peer_auth" ]]; then
        add_result "PeerAuthentication" "WARN" "No mesh-wide PeerAuthentication found"
    else
        add_result "PeerAuthentication" "INFO" "mTLS mode: $peer_auth"
    fi
}

# =============================================================================
# Validation Step 6: Additional Network Checks
# =============================================================================
validate_network_configuration() {
    log_step "Step 6: Validating network configuration"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "DRY RUN: Check namespace labels for topology.istio.io/network"
        log_verbose "DRY RUN: Verify East-West Gateway is running"
        add_result "Network Configuration" "SKIP" "Dry run mode - skipping network checks"
        return 0
    fi

    # Check namespace labels
    log_info "Checking namespace network topology labels..."
    local r1_network_label
    r1_network_label=$(kubectl --context="$REGION1_CONTEXT" get namespace "$NAMESPACE" -o jsonpath='{.metadata.labels.topology\.istio\.io/network}' 2>/dev/null || echo "")

    local r2_network_label
    r2_network_label=$(kubectl --context="$REGION2_CONTEXT" get namespace "$NAMESPACE" -o jsonpath='{.metadata.labels.topology\.istio\.io/network}' 2>/dev/null || echo "")

    if [[ -n "$r1_network_label" ]]; then
        add_result "Network Label (Region 1)" "PASS" "Namespace labeled with network: $r1_network_label"
    else
        add_result "Network Label (Region 1)" "WARN" "Missing topology.istio.io/network label on namespace"
    fi

    if [[ -n "$r2_network_label" ]]; then
        add_result "Network Label (Region 2)" "PASS" "Namespace labeled with network: $r2_network_label"
    else
        add_result "Network Label (Region 2)" "WARN" "Missing topology.istio.io/network label on namespace"
    fi

    # Check East-West Gateway
    log_info "Checking East-West Gateway status..."
    local ewg_status
    ewg_status=$(kubectl --context="$REGION1_CONTEXT" get pods -n istio-system -l istio=eastwestgateway -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "")

    if [[ "$ewg_status" == "Running" ]]; then
        add_result "East-West Gateway (Region 1)" "PASS" "Gateway is running"
    elif [[ -z "$ewg_status" ]]; then
        add_result "East-West Gateway (Region 1)" "FAIL" "No East-West Gateway found"
    else
        add_result "East-West Gateway (Region 1)" "WARN" "Gateway status: $ewg_status"
    fi

    ewg_status=$(kubectl --context="$REGION2_CONTEXT" get pods -n istio-system -l istio=eastwestgateway -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "")

    if [[ "$ewg_status" == "Running" ]]; then
        add_result "East-West Gateway (Region 2)" "PASS" "Gateway is running"
    elif [[ -z "$ewg_status" ]]; then
        add_result "East-West Gateway (Region 2)" "FAIL" "No East-West Gateway found"
    else
        add_result "East-West Gateway (Region 2)" "WARN" "Gateway status: $ewg_status"
    fi

    # Check mesh ID consistency
    log_info "Checking mesh ID consistency..."
    local r1_mesh_id
    r1_mesh_id=$(kubectl --context="$REGION1_CONTEXT" get configmap istio -n istio-system -o jsonpath='{.data.mesh}' 2>/dev/null | grep -o 'meshId: [^"]*' | head -1 || echo "")

    local r2_mesh_id
    r2_mesh_id=$(kubectl --context="$REGION2_CONTEXT" get configmap istio -n istio-system -o jsonpath='{.data.mesh}' 2>/dev/null | grep -o 'meshId: [^"]*' | head -1 || echo "")

    if [[ -n "$r1_mesh_id" && -n "$r2_mesh_id" ]]; then
        if [[ "$r1_mesh_id" == "$r2_mesh_id" ]]; then
            add_result "Mesh ID Consistency" "PASS" "Both regions use same mesh ID"
        else
            add_result "Mesh ID Consistency" "FAIL" "Mesh IDs differ: Region1=$r1_mesh_id, Region2=$r2_mesh_id"
        fi
    else
        add_result "Mesh ID Consistency" "WARN" "Could not verify mesh ID (R1: $r1_mesh_id, R2: $r2_mesh_id)"
    fi
}

# =============================================================================
# Output Results
# =============================================================================
output_results() {
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        local results_json="["
        for i in "${!RESULTS[@]}"; do
            results_json+="${RESULTS[$i]}"
            if [[ $i -lt $((${#RESULTS[@]} - 1)) ]]; then
                results_json+=","
            fi
        done
        results_json+="]"

        echo "{\"validation\": \"cross-cluster-service-discovery\", \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\", \"region1\": \"$REGION1_CONTEXT\", \"region2\": \"$REGION2_CONTEXT\", \"passed\": $VALIDATION_PASSED, \"results\": $results_json}"
    else
        echo ""
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${CYAN}                    VALIDATION SUMMARY                                    ${NC}"
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

        echo -e "  ${GREEN}PASSED:${NC}  $pass_count"
        echo -e "  ${RED}FAILED:${NC}  $fail_count"
        echo -e "  ${YELLOW}WARNINGS:${NC} $warn_count"
        echo -e "  ${BLUE}SKIPPED:${NC} $skip_count"
        echo ""

        if [[ "$VALIDATION_PASSED" == "true" ]]; then
            echo -e "${GREEN}✓ Cross-cluster service discovery validation PASSED${NC}"
        else
            echo -e "${RED}✗ Cross-cluster service discovery validation FAILED${NC}"
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
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
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
            --service)
                SPECIFIC_SERVICE="$2"
                shift 2
                ;;
            --skip-mtls)
                SKIP_MTLS=true
                shift
                ;;
            --skip-http)
                SKIP_HTTP=true
                shift
                ;;
            --timeout)
                HTTP_TIMEOUT="$2"
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
                if [[ -z "$REGION1_CONTEXT" ]]; then
                    REGION1_CONTEXT="$1"
                elif [[ -z "$REGION2_CONTEXT" ]]; then
                    REGION2_CONTEXT="$2"
                    shift
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

    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo ""
        echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}║     CROSS-CLUSTER SERVICE DISCOVERY VALIDATION                          ║${NC}"
        echo -e "${CYAN}║     Multi-Region Deployment Verification                                ║${NC}"
        echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo "Region 1: $REGION1_CONTEXT"
        echo "Region 2: $REGION2_CONTEXT"
        echo "Namespace: $NAMESPACE"
        if [[ -n "$SPECIFIC_SERVICE" ]]; then
            echo "Service: $SPECIFIC_SERVICE"
        fi
        echo "Dry Run: $DRY_RUN"
        echo ""
    fi

    # Execute validation steps
    check_prerequisites || true
    check_cluster_access || true
    validate_service_deployment
    validate_proxy_status
    validate_cross_cluster_discovery
    validate_cross_region_http
    validate_mtls_certificates
    validate_network_configuration

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
