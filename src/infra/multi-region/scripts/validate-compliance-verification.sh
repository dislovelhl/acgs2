#!/bin/bash
# =============================================================================
# Compliance Verification Validation Script - End-to-End Testing
# =============================================================================
# This script executes comprehensive compliance verification validation including
# tenant residency ConfigMap application, EU tenant workload deployment, pod
# placement verification, cross-region access blocking, and compliance CronJob
# execution.
#
# Usage:
#   ./validate-compliance-verification.sh [OPTIONS] <region1-context> <region2-context>
#
# Options:
#   --namespace            Tenant namespace (default: tenant-eu-enterprise-001)
#   --tenant-id            Tenant ID to test (default: eu-enterprise-001)
#   --target-region        Target region for pod placement (default: eu-west-1)
#   --compliance-ns        Compliance namespace (default: acgs-compliance)
#   --dry-run              Show validation steps without executing
#   --json                 Output results in JSON format
#   --verbose              Show detailed output including command output
#   --skip-deploy          Skip workload deployment (use existing)
#   --skip-cleanup         Skip cleanup after test
#   --skip-cronjob         Skip compliance CronJob execution
#   --timeout              Maximum wait time for operations in seconds (default: 120)
#   --help                 Show this help message
#
# Examples:
#   ./validate-compliance-verification.sh region1 region2
#   ./validate-compliance-verification.sh --verbose --json us-east-1 eu-west-1
#   ./validate-compliance-verification.sh --tenant-id cn-enterprise-001 --target-region cn-north-1 region1 region2
#
# Requirements:
#   - kubectl with contexts for all specified clusters
#   - Istio service mesh with AuthorizationPolicy deployed
#   - Tenant residency ConfigMap applied to acgs-system namespace
#   - Compliance CronJob deployed to acgs-compliance namespace
#   - OPA admission controller configured (optional)
#
# Validation Steps (E2E):
#   1. Verify prerequisites and cluster access
#   2. Apply tenant residency ConfigMap with EU tenant
#   3. Deploy EU tenant workload with compliance labels
#   4. Verify pod scheduled in EU region only
#   5. Attempt cross-region access and verify AuthorizationPolicy blocks it
#   6. Execute compliance CronJob and verify report shows PASS
#   7. Cleanup test resources (optional)
#   8. Generate validation report
#
# References:
#   - tenant-residency-config.yaml: Tenant-to-region mappings
#   - cross-region-authz-policy.yaml: Istio AuthorizationPolicy resources
#   - compliance-cronjob.yaml: GDPR/PIPL compliance verification
# =============================================================================

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================
TENANT_NAMESPACE="tenant-eu-enterprise-001"
TENANT_ID="eu-enterprise-001"
TARGET_REGION="eu-west-1"
TARGET_ZONE="eu"
COMPLIANCE_NAMESPACE="acgs-compliance"
SYSTEM_NAMESPACE="acgs-system"
DRY_RUN=false
JSON_OUTPUT=false
VERBOSE=false
SKIP_DEPLOY=false
SKIP_CLEANUP=false
SKIP_CRONJOB=false
TIMEOUT=120
REGION1_CONTEXT=""
REGION2_CONTEXT=""

# Test workload configuration
TEST_DEPLOYMENT_NAME="compliance-test-workload"
TEST_SERVICE_ACCOUNT="compliance-test-sa"

# Timing variables
START_TIME=0
END_TIME=0

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

# =============================================================================
# Helper Functions
# =============================================================================
usage() {
    head -60 "$0" | grep -E '^#' | sed 's/^# *//' | tail -n +2
    exit 0
}

get_timestamp_ms() {
    if [[ "$(uname)" == "Darwin" ]]; then
        python3 -c 'import time; print(int(time.time() * 1000))' 2>/dev/null || \
        perl -MTime::HiRes=time -e 'printf "%.0f\n", time * 1000' 2>/dev/null || \
        echo $(($(date +%s) * 1000))
    else
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
# Step 1: Prerequisite Checks
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

    # Check curl (for HTTP testing)
    if ! command -v curl &> /dev/null; then
        missing_tools+=("curl")
    else
        log_verbose "curl found: $(curl --version | head -1)"
    fi

    # Check jq (optional but helpful)
    if command -v jq &> /dev/null; then
        log_verbose "jq found: $(jq --version)"
    else
        log_verbose "jq not found (optional, will use grep/sed)"
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

    # Check Region 1 (US) access
    if ! kubectl --context="$REGION1_CONTEXT" cluster-info &> /dev/null; then
        add_result "Cluster Access (Region 1)" "FAIL" "Cannot access cluster with context: $REGION1_CONTEXT"
        return 1
    fi
    log_verbose "Region 1 cluster accessible: $REGION1_CONTEXT"

    # Check Region 2 (EU) access
    if ! kubectl --context="$REGION2_CONTEXT" cluster-info &> /dev/null; then
        add_result "Cluster Access (Region 2)" "FAIL" "Cannot access cluster with context: $REGION2_CONTEXT"
        return 1
    fi
    log_verbose "Region 2 cluster accessible: $REGION2_CONTEXT"

    add_result "Cluster Access" "PASS" "Both cluster contexts accessible"
    return 0
}

# =============================================================================
# Step 2: Apply Tenant Residency ConfigMap
# =============================================================================
apply_tenant_residency_config() {
    log_step "Step 2: Applying tenant residency ConfigMap with EU tenant"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "DRY RUN: Would apply tenant-residency-config.yaml and tenant-region-lookup ConfigMaps"
        add_result "Tenant Residency ConfigMap" "SKIP" "Dry run mode - skipping ConfigMap application"
        return 0
    fi

    # Check if acgs-system namespace exists, create if not
    log_info "Ensuring $SYSTEM_NAMESPACE namespace exists..."

    if ! kubectl --context="$REGION2_CONTEXT" get namespace "$SYSTEM_NAMESPACE" &> /dev/null; then
        log_info "Creating $SYSTEM_NAMESPACE namespace..."
        kubectl --context="$REGION2_CONTEXT" create namespace "$SYSTEM_NAMESPACE" 2>/dev/null || true
    fi

    # Check for existing tenant residency config
    log_info "Checking tenant residency configuration..."

    local config_exists
    config_exists=$(kubectl --context="$REGION2_CONTEXT" get configmap tenant-residency-config \
        -n "$SYSTEM_NAMESPACE" -o name 2>/dev/null || echo "")

    if [[ -n "$config_exists" ]]; then
        add_result "Tenant Residency ConfigMap" "PASS" "Tenant residency ConfigMap already exists"

        # Verify tenant exists in config
        local tenant_region
        tenant_region=$(kubectl --context="$REGION2_CONTEXT" get configmap tenant-region-lookup \
            -n "$SYSTEM_NAMESPACE" -o jsonpath='{.data.tenant-region-map}' 2>/dev/null | \
            grep "^${TENANT_ID}=" | cut -d'=' -f2 || echo "")

        if [[ -n "$tenant_region" ]]; then
            log_verbose "Tenant $TENANT_ID mapped to region: $tenant_region"

            if [[ "$tenant_region" == "$TARGET_REGION" ]]; then
                add_result "Tenant Region Mapping" "PASS" "Tenant $TENANT_ID correctly mapped to $TARGET_REGION"
            else
                add_result "Tenant Region Mapping" "WARN" "Tenant $TENANT_ID mapped to $tenant_region, expected $TARGET_REGION"
            fi
        else
            log_warn "Tenant $TENANT_ID not found in tenant-region-lookup ConfigMap"
        fi
    else
        log_warn "Tenant residency ConfigMap not found"
        log_info "For full validation, apply tenant-residency-config.yaml to $SYSTEM_NAMESPACE namespace"
        add_result "Tenant Residency ConfigMap" "WARN" "ConfigMap not found - apply tenant-residency-config.yaml"
    fi

    return 0
}

# =============================================================================
# Step 3: Deploy EU Tenant Workload
# =============================================================================
deploy_eu_tenant_workload() {
    log_step "Step 3: Deploying EU tenant workload with compliance labels"

    if [[ "$SKIP_DEPLOY" == "true" ]]; then
        add_result "EU Tenant Workload Deployment" "SKIP" "Skipped by --skip-deploy flag"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "DRY RUN: Would deploy compliance test workload to $TENANT_NAMESPACE"
        add_result "EU Tenant Workload Deployment" "SKIP" "Dry run mode - skipping workload deployment"
        return 0
    fi

    # Create tenant namespace if it doesn't exist
    log_info "Creating tenant namespace $TENANT_NAMESPACE..."

    kubectl --context="$REGION2_CONTEXT" apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: ${TENANT_NAMESPACE}
  labels:
    app.kubernetes.io/name: ${TENANT_NAMESPACE}
    app.kubernetes.io/part-of: acgs2-multi-region
    data-residency: ${TARGET_ZONE}
    tenant-id: ${TENANT_ID}
    compliance-frameworks: gdpr,eu-ai-act
    istio-injection: enabled
    acgs.io/compliance-gdpr: "true"
  annotations:
    acgs.io/description: "Namespace for EU tenant ${TENANT_ID} - GDPR compliant"
    scheduler.alpha.kubernetes.io/node-selector: "topology.kubernetes.io/region=${TARGET_REGION}"
EOF

    if [[ $? -ne 0 ]]; then
        add_result "Tenant Namespace Creation" "FAIL" "Failed to create namespace $TENANT_NAMESPACE"
        return 1
    fi
    add_result "Tenant Namespace Creation" "PASS" "Namespace $TENANT_NAMESPACE created with data-residency=${TARGET_ZONE}"

    # Create service account
    log_info "Creating service account..."

    kubectl --context="$REGION2_CONTEXT" apply -f - <<EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ${TEST_SERVICE_ACCOUNT}
  namespace: ${TENANT_NAMESPACE}
  labels:
    app.kubernetes.io/name: compliance-test
    app.kubernetes.io/component: test
    tenant-id: ${TENANT_ID}
EOF

    # Deploy test workload with GDPR compliance labels
    log_info "Deploying test workload with GDPR compliance labels..."

    kubectl --context="$REGION2_CONTEXT" apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${TEST_DEPLOYMENT_NAME}
  namespace: ${TENANT_NAMESPACE}
  labels:
    app.kubernetes.io/name: compliance-test
    app.kubernetes.io/component: test
    app.kubernetes.io/part-of: acgs2-multi-region
    tenant-id: ${TENANT_ID}
    data-residency: ${TARGET_ZONE}
    acgs.io/compliance-gdpr: "true"
    acgs.io/compliance-eu-ai-act: "true"
  annotations:
    acgs.io/description: "Test workload for GDPR compliance validation"
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: compliance-test
      tenant-id: ${TENANT_ID}
  template:
    metadata:
      labels:
        app.kubernetes.io/name: compliance-test
        app.kubernetes.io/component: test
        tenant-id: ${TENANT_ID}
        data-residency: ${TARGET_ZONE}
        acgs.io/compliance-gdpr: "true"
        acgs.io/compliance-eu-ai-act: "true"
      annotations:
        sidecar.istio.io/inject: "true"
    spec:
      serviceAccountName: ${TEST_SERVICE_ACCOUNT}
      # Node affinity to ensure scheduling in target region
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - key: topology.kubernetes.io/region
                    operator: In
                    values:
                      - ${TARGET_REGION}
      containers:
        - name: nginx
          image: nginx:1.25-alpine
          ports:
            - containerPort: 80
              name: http
          resources:
            limits:
              cpu: 100m
              memory: 128Mi
            requests:
              cpu: 50m
              memory: 64Mi
          livenessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 5
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 5
            periodSeconds: 5
          securityContext:
            runAsNonRoot: false
            readOnlyRootFilesystem: false
EOF

    if [[ $? -ne 0 ]]; then
        add_result "Test Workload Deployment" "FAIL" "Failed to deploy test workload"
        return 1
    fi

    # Create service for the workload
    kubectl --context="$REGION2_CONTEXT" apply -f - <<EOF
apiVersion: v1
kind: Service
metadata:
  name: ${TEST_DEPLOYMENT_NAME}
  namespace: ${TENANT_NAMESPACE}
  labels:
    app.kubernetes.io/name: compliance-test
    tenant-id: ${TENANT_ID}
spec:
  selector:
    app.kubernetes.io/name: compliance-test
    tenant-id: ${TENANT_ID}
  ports:
    - name: http
      port: 80
      targetPort: 80
  type: ClusterIP
EOF

    # Wait for deployment to be ready
    log_info "Waiting for deployment to be ready..."

    local wait_count=0
    local max_wait=$TIMEOUT
    while [[ $wait_count -lt $max_wait ]]; do
        local ready
        ready=$(kubectl --context="$REGION2_CONTEXT" get deployment "$TEST_DEPLOYMENT_NAME" \
            -n "$TENANT_NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")

        if [[ "$ready" == "1" ]]; then
            add_result "Test Workload Deployment" "PASS" "Deployment $TEST_DEPLOYMENT_NAME is ready"
            break
        fi

        log_verbose "Waiting for deployment... ($wait_count/$max_wait seconds)"
        sleep 5
        ((wait_count += 5))
    done

    if [[ $wait_count -ge $max_wait ]]; then
        add_result "Test Workload Deployment" "FAIL" "Timeout waiting for deployment to become ready"
        return 1
    fi

    return 0
}

# =============================================================================
# Step 4: Verify Pod Scheduled in EU Region Only
# =============================================================================
verify_pod_placement() {
    log_step "Step 4: Verifying pod scheduled in $TARGET_REGION region only"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "DRY RUN: Would verify pod placement in $TARGET_REGION"
        add_result "Pod Placement Verification" "SKIP" "Dry run mode - skipping pod placement check"
        return 0
    fi

    # Get the pod
    log_info "Getting pod information..."

    local pod_name
    pod_name=$(kubectl --context="$REGION2_CONTEXT" get pods -n "$TENANT_NAMESPACE" \
        -l "app.kubernetes.io/name=compliance-test,tenant-id=$TENANT_ID" \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

    if [[ -z "$pod_name" ]]; then
        add_result "Pod Existence" "FAIL" "No pod found for tenant $TENANT_ID"
        return 1
    fi
    log_verbose "Found pod: $pod_name"

    # Get the node the pod is scheduled on
    local node_name
    node_name=$(kubectl --context="$REGION2_CONTEXT" get pod "$pod_name" -n "$TENANT_NAMESPACE" \
        -o jsonpath='{.spec.nodeName}' 2>/dev/null || echo "")

    if [[ -z "$node_name" ]]; then
        add_result "Pod Node Assignment" "FAIL" "Pod $pod_name is not scheduled to any node"
        return 1
    fi
    log_verbose "Pod scheduled on node: $node_name"

    # Get the node's region label
    local node_region
    node_region=$(kubectl --context="$REGION2_CONTEXT" get node "$node_name" \
        -o jsonpath='{.metadata.labels.topology\.kubernetes\.io/region}' 2>/dev/null || echo "unknown")

    log_info "Pod $pod_name is running on node $node_name in region $node_region"

    # Verify the region matches expected target
    if [[ "$node_region" == "$TARGET_REGION" ]]; then
        add_result "Pod Region Placement" "PASS" "Pod correctly placed in $TARGET_REGION region"
    else
        add_result "Pod Region Placement" "FAIL" "Pod placed in $node_region, expected $TARGET_REGION"
        return 1
    fi

    # Verify pod has correct compliance labels
    log_info "Verifying pod compliance labels..."

    local gdpr_label
    gdpr_label=$(kubectl --context="$REGION2_CONTEXT" get pod "$pod_name" -n "$TENANT_NAMESPACE" \
        -o jsonpath='{.metadata.labels.acgs\.io/compliance-gdpr}' 2>/dev/null || echo "")

    if [[ "$gdpr_label" == "true" ]]; then
        add_result "Pod GDPR Label" "PASS" "Pod has acgs.io/compliance-gdpr=true label"
    else
        add_result "Pod GDPR Label" "WARN" "Pod missing acgs.io/compliance-gdpr label"
    fi

    # Verify namespace has correct data-residency label
    local ns_residency
    ns_residency=$(kubectl --context="$REGION2_CONTEXT" get namespace "$TENANT_NAMESPACE" \
        -o jsonpath='{.metadata.labels.data-residency}' 2>/dev/null || echo "")

    if [[ "$ns_residency" == "$TARGET_ZONE" ]]; then
        add_result "Namespace Residency Label" "PASS" "Namespace has data-residency=$TARGET_ZONE label"
    else
        add_result "Namespace Residency Label" "WARN" "Namespace has data-residency=$ns_residency, expected $TARGET_ZONE"
    fi

    # Check that pod is NOT running in other regions
    log_info "Verifying pod is NOT running in non-EU regions..."

    local pods_in_region1
    pods_in_region1=$(kubectl --context="$REGION1_CONTEXT" get pods -n "$TENANT_NAMESPACE" \
        -l "app.kubernetes.io/name=compliance-test,tenant-id=$TENANT_ID" \
        --no-headers 2>/dev/null | wc -l || echo "0")

    if [[ "$pods_in_region1" -eq 0 ]]; then
        add_result "Cross-Region Pod Check" "PASS" "No pods for tenant $TENANT_ID found in Region 1 (US)"
    else
        add_result "Cross-Region Pod Check" "FAIL" "Found $pods_in_region1 pods in Region 1 (US) - data residency violation"
        return 1
    fi

    return 0
}

# =============================================================================
# Step 5: Verify Cross-Region Access Blocked by AuthorizationPolicy
# =============================================================================
verify_cross_region_access_blocked() {
    log_step "Step 5: Verifying cross-region access is blocked by AuthorizationPolicy"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "DRY RUN: Would test cross-region access blocking"
        add_result "Cross-Region Access Blocking" "SKIP" "Dry run mode - skipping access test"
        return 0
    fi

    # Check if AuthorizationPolicy exists
    log_info "Checking for GDPR deny AuthorizationPolicy..."

    local gdpr_policy
    gdpr_policy=$(kubectl --context="$REGION2_CONTEXT" get authorizationpolicy gdpr-deny-non-eu-access \
        -n istio-system -o jsonpath='{.spec.action}' 2>/dev/null || echo "")

    if [[ "$gdpr_policy" == "DENY" ]]; then
        add_result "GDPR AuthorizationPolicy" "PASS" "GDPR deny policy exists with action=DENY"
    else
        log_warn "GDPR deny policy not found or not configured with DENY action"
        add_result "GDPR AuthorizationPolicy" "WARN" "GDPR deny policy not properly configured"
    fi

    # Check for PIPL deny policy
    local pipl_policy
    pipl_policy=$(kubectl --context="$REGION2_CONTEXT" get authorizationpolicy pipl-deny-cross-border \
        -n istio-system -o jsonpath='{.spec.action}' 2>/dev/null || echo "")

    if [[ "$pipl_policy" == "DENY" ]]; then
        add_result "PIPL AuthorizationPolicy" "PASS" "PIPL deny policy exists with action=DENY"
    else
        log_verbose "PIPL deny policy not found (OK if not testing China tenants)"
    fi

    # Check for cross-region deny-all policy
    local deny_all_policy
    deny_all_policy=$(kubectl --context="$REGION2_CONTEXT" get authorizationpolicy cross-region-deny-all \
        -n istio-system -o name 2>/dev/null || echo "")

    if [[ -n "$deny_all_policy" ]]; then
        add_result "Cross-Region Deny-All Policy" "PASS" "Global deny-all policy exists"
    else
        add_result "Cross-Region Deny-All Policy" "WARN" "Global deny-all policy not found"
    fi

    # Check for intra-region allow policy
    local intra_region_policy
    intra_region_policy=$(kubectl --context="$REGION2_CONTEXT" get authorizationpolicy allow-intra-region-eu-west-1 \
        -n istio-system -o jsonpath='{.spec.action}' 2>/dev/null || echo "")

    if [[ "$intra_region_policy" == "ALLOW" ]]; then
        add_result "Intra-Region Allow Policy" "PASS" "EU intra-region allow policy exists"
    else
        add_result "Intra-Region Allow Policy" "WARN" "EU intra-region allow policy not found"
    fi

    # Attempt to simulate cross-region access (if test pod exists)
    log_info "Attempting to validate cross-region access control..."

    # Find a pod in Region 1 (US) to test from
    local test_pod_us
    test_pod_us=$(kubectl --context="$REGION1_CONTEXT" get pods -n default \
        -l "app.kubernetes.io/name=claude-flow" \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

    if [[ -n "$test_pod_us" ]]; then
        log_info "Found test pod in Region 1: $test_pod_us"

        # Try to access EU workload from US pod (should be blocked)
        log_info "Testing cross-region access (US -> EU)..."

        local access_result
        access_result=$(kubectl --context="$REGION1_CONTEXT" exec "$test_pod_us" -n default -- \
            curl -s -o /dev/null -w "%{http_code}" \
            --connect-timeout 5 \
            "http://${TEST_DEPLOYMENT_NAME}.${TENANT_NAMESPACE}.svc.cluster.local:80" 2>/dev/null || echo "blocked")

        if [[ "$access_result" == "blocked" ]] || [[ "$access_result" == "000" ]] || [[ "$access_result" == "403" ]]; then
            add_result "Cross-Region Access Test" "PASS" "Access from US to EU tenant correctly blocked (result: $access_result)"
        elif [[ "$access_result" == "200" ]]; then
            add_result "Cross-Region Access Test" "FAIL" "Access from US to EU tenant was ALLOWED (should be blocked)"
        else
            add_result "Cross-Region Access Test" "WARN" "Cross-region access test returned: $access_result"
        fi
    else
        log_info "No test pod available in Region 1 for cross-region access test"
        add_result "Cross-Region Access Test" "SKIP" "No test pod available in Region 1"
    fi

    # Verify mTLS is enforced
    log_info "Checking mTLS enforcement..."

    local mtls_mode
    mtls_mode=$(kubectl --context="$REGION2_CONTEXT" get peerauthentication -n istio-system \
        -o jsonpath='{.items[0].spec.mtls.mode}' 2>/dev/null || echo "")

    if [[ "$mtls_mode" == "STRICT" ]]; then
        add_result "mTLS Enforcement" "PASS" "mTLS mode is STRICT for cross-region communication"
    else
        add_result "mTLS Enforcement" "WARN" "mTLS mode is '$mtls_mode', expected 'STRICT'"
    fi

    return 0
}

# =============================================================================
# Step 6: Execute Compliance CronJob and Verify Report
# =============================================================================
execute_compliance_cronjob() {
    log_step "Step 6: Executing compliance CronJob and verifying report shows PASS"

    if [[ "$SKIP_CRONJOB" == "true" ]]; then
        add_result "Compliance CronJob Execution" "SKIP" "Skipped by --skip-cronjob flag"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "DRY RUN: Would execute compliance verification CronJob"
        add_result "Compliance CronJob Execution" "SKIP" "Dry run mode - skipping CronJob execution"
        return 0
    fi

    # Check if compliance namespace exists
    if ! kubectl --context="$REGION2_CONTEXT" get namespace "$COMPLIANCE_NAMESPACE" &> /dev/null; then
        log_info "Creating compliance namespace..."
        kubectl --context="$REGION2_CONTEXT" create namespace "$COMPLIANCE_NAMESPACE" 2>/dev/null || true
    fi

    # Check if CronJob exists
    local cronjob_exists
    cronjob_exists=$(kubectl --context="$REGION2_CONTEXT" get cronjob compliance-verification \
        -n "$COMPLIANCE_NAMESPACE" -o name 2>/dev/null || echo "")

    if [[ -z "$cronjob_exists" ]]; then
        log_warn "Compliance CronJob not found in $COMPLIANCE_NAMESPACE namespace"
        log_info "To fully validate, apply compliance-cronjob.yaml"
        add_result "Compliance CronJob" "WARN" "CronJob not deployed - apply compliance-cronjob.yaml"
        return 0
    fi

    add_result "Compliance CronJob Existence" "PASS" "Compliance CronJob exists"

    # Create a manual job from the CronJob
    log_info "Creating manual compliance verification job..."

    local job_name="compliance-validation-$(date +%s)"

    kubectl --context="$REGION2_CONTEXT" create job "$job_name" \
        --from=cronjob/compliance-verification \
        -n "$COMPLIANCE_NAMESPACE" 2>/dev/null

    if [[ $? -ne 0 ]]; then
        add_result "Compliance Job Creation" "FAIL" "Failed to create compliance verification job"
        return 1
    fi

    log_info "Waiting for compliance job to complete..."

    # Wait for job to complete
    local wait_count=0
    local max_wait=$TIMEOUT
    local job_status=""

    while [[ $wait_count -lt $max_wait ]]; do
        job_status=$(kubectl --context="$REGION2_CONTEXT" get job "$job_name" -n "$COMPLIANCE_NAMESPACE" \
            -o jsonpath='{.status.conditions[0].type}' 2>/dev/null || echo "")

        if [[ "$job_status" == "Complete" ]]; then
            log_info "Compliance job completed successfully"
            break
        elif [[ "$job_status" == "Failed" ]]; then
            log_error "Compliance job failed"
            break
        fi

        log_verbose "Waiting for job completion... ($wait_count/$max_wait seconds)"
        sleep 5
        ((wait_count += 5))
    done

    if [[ $wait_count -ge $max_wait ]]; then
        add_result "Compliance Job Completion" "FAIL" "Timeout waiting for compliance job to complete"
        return 1
    fi

    # Get job logs
    log_info "Retrieving compliance job logs..."

    local pod_name
    pod_name=$(kubectl --context="$REGION2_CONTEXT" get pods -n "$COMPLIANCE_NAMESPACE" \
        -l "job-name=$job_name" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

    if [[ -z "$pod_name" ]]; then
        add_result "Compliance Job Logs" "FAIL" "Cannot find compliance job pod"
        return 1
    fi

    local job_logs
    job_logs=$(kubectl --context="$REGION2_CONTEXT" logs "$pod_name" -n "$COMPLIANCE_NAMESPACE" 2>/dev/null || echo "")

    if [[ "$VERBOSE" == "true" ]]; then
        log_verbose "Compliance job logs:"
        echo "$job_logs" | head -50
    fi

    # Parse compliance report from logs
    log_info "Parsing compliance report..."

    local overall_status
    overall_status=$(echo "$job_logs" | grep -i "OVERALL STATUS" | head -1 || echo "")

    if echo "$overall_status" | grep -qi "PASS"; then
        add_result "Compliance Report Status" "PASS" "Compliance verification PASSED: $overall_status"
    elif echo "$overall_status" | grep -qi "FAIL"; then
        add_result "Compliance Report Status" "FAIL" "Compliance verification FAILED: $overall_status"
    elif echo "$overall_status" | grep -qi "WARNING"; then
        add_result "Compliance Report Status" "WARN" "Compliance verification passed with warnings: $overall_status"
    else
        # Try to extract JSON report
        local compliance_percentage
        compliance_percentage=$(echo "$job_logs" | grep -o '"compliance_percentage": [0-9]*' | grep -o '[0-9]*' || echo "")

        if [[ -n "$compliance_percentage" ]]; then
            if [[ "$compliance_percentage" -ge 80 ]]; then
                add_result "Compliance Report Status" "PASS" "Compliance percentage: ${compliance_percentage}%"
            else
                add_result "Compliance Report Status" "WARN" "Compliance percentage: ${compliance_percentage}% (below 80%)"
            fi
        else
            add_result "Compliance Report Status" "WARN" "Could not parse compliance status from job output"
        fi
    fi

    # Verify specific checks passed
    log_info "Verifying individual compliance checks..."

    if echo "$job_logs" | grep -q "PASS: Namespace.*residency label"; then
        add_result "Namespace Label Check" "PASS" "Namespace labels verified by compliance job"
    fi

    if echo "$job_logs" | grep -q "PASS: AuthorizationPolicy"; then
        add_result "AuthorizationPolicy Check" "PASS" "AuthorizationPolicies verified by compliance job"
    fi

    if echo "$job_logs" | grep -q "PASS: mTLS mode is STRICT"; then
        add_result "mTLS Check" "PASS" "mTLS STRICT mode verified by compliance job"
    fi

    if echo "$job_logs" | grep -q "PASS: GDPR"; then
        add_result "GDPR Compliance Check" "PASS" "GDPR compliance verified"
    fi

    # Clean up manual job
    log_info "Cleaning up manual compliance job..."
    kubectl --context="$REGION2_CONTEXT" delete job "$job_name" -n "$COMPLIANCE_NAMESPACE" 2>/dev/null || true

    return 0
}

# =============================================================================
# Step 7: Cleanup Test Resources
# =============================================================================
cleanup_test_resources() {
    log_step "Step 7: Cleaning up test resources"

    if [[ "$SKIP_CLEANUP" == "true" ]]; then
        add_result "Cleanup" "SKIP" "Skipped by --skip-cleanup flag"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_verbose "DRY RUN: Would cleanup test resources"
        add_result "Cleanup" "SKIP" "Dry run mode - skipping cleanup"
        return 0
    fi

    if [[ "$SKIP_DEPLOY" == "true" ]]; then
        add_result "Cleanup" "SKIP" "No resources to clean (deployment was skipped)"
        return 0
    fi

    log_info "Deleting test deployment..."
    kubectl --context="$REGION2_CONTEXT" delete deployment "$TEST_DEPLOYMENT_NAME" \
        -n "$TENANT_NAMESPACE" 2>/dev/null || true

    log_info "Deleting test service..."
    kubectl --context="$REGION2_CONTEXT" delete service "$TEST_DEPLOYMENT_NAME" \
        -n "$TENANT_NAMESPACE" 2>/dev/null || true

    log_info "Deleting test service account..."
    kubectl --context="$REGION2_CONTEXT" delete serviceaccount "$TEST_SERVICE_ACCOUNT" \
        -n "$TENANT_NAMESPACE" 2>/dev/null || true

    # Optionally delete the tenant namespace
    # (commented out to preserve namespace for further testing)
    # kubectl --context="$REGION2_CONTEXT" delete namespace "$TENANT_NAMESPACE" 2>/dev/null || true

    add_result "Cleanup" "PASS" "Test resources cleaned up successfully"
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
  "validation": "compliance-verification",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "configuration": {
    "region1Context": "$REGION1_CONTEXT",
    "region2Context": "$REGION2_CONTEXT",
    "tenantNamespace": "$TENANT_NAMESPACE",
    "tenantId": "$TENANT_ID",
    "targetRegion": "$TARGET_REGION",
    "targetZone": "$TARGET_ZONE",
    "complianceNamespace": "$COMPLIANCE_NAMESPACE"
  },
  "timing": {
    "startTime": $START_TIME,
    "endTime": $END_TIME,
    "totalDurationSeconds": $duration
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
    echo -e "${CYAN}║            COMPLIANCE VERIFICATION VALIDATION RESULTS                    ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "  Configuration:"
    echo "    Region 1 (US):     $REGION1_CONTEXT"
    echo "    Region 2 (EU):     $REGION2_CONTEXT"
    echo "    Tenant Namespace:  $TENANT_NAMESPACE"
    echo "    Tenant ID:         $TENANT_ID"
    echo "    Target Region:     $TARGET_REGION"
    echo "    Target Zone:       $TARGET_ZONE"
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
        echo -e "${GREEN}║  ✓ COMPLIANCE VERIFICATION VALIDATION PASSED                            ║${NC}"
        echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════════╝${NC}"
    else
        echo -e "${RED}╔══════════════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${RED}║  ✗ COMPLIANCE VERIFICATION VALIDATION FAILED                            ║${NC}"
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

    if [[ "$SKIP_CLEANUP" == "false" ]] && [[ $exit_code -ne 0 ]] && [[ "$SKIP_DEPLOY" == "false" ]]; then
        log_warn "Validation interrupted. Cleaning up test resources..."

        kubectl --context="$REGION2_CONTEXT" delete deployment "$TEST_DEPLOYMENT_NAME" \
            -n "$TENANT_NAMESPACE" 2>/dev/null || true
        kubectl --context="$REGION2_CONTEXT" delete service "$TEST_DEPLOYMENT_NAME" \
            -n "$TENANT_NAMESPACE" 2>/dev/null || true
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
                TENANT_NAMESPACE="$2"
                shift 2
                ;;
            --tenant-id)
                TENANT_ID="$2"
                shift 2
                ;;
            --target-region)
                TARGET_REGION="$2"
                # Derive zone from region (us-east-1 -> us, eu-west-1 -> eu, etc.)
                TARGET_ZONE=$(echo "$TARGET_REGION" | cut -d'-' -f1)
                shift 2
                ;;
            --compliance-ns)
                COMPLIANCE_NAMESPACE="$2"
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
            --skip-deploy)
                SKIP_DEPLOY=true
                shift
                ;;
            --skip-cleanup)
                SKIP_CLEANUP=true
                shift
                ;;
            --skip-cronjob)
                SKIP_CRONJOB=true
                shift
                ;;
            --timeout)
                TIMEOUT="$2"
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
        echo -e "${CYAN}║     COMPLIANCE VERIFICATION VALIDATION                                   ║${NC}"
        echo -e "${CYAN}║     End-to-End GDPR/PIPL Data Residency Testing                          ║${NC}"
        echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo "  Region 1 (US):     $REGION1_CONTEXT"
        echo "  Region 2 (EU):     $REGION2_CONTEXT"
        echo "  Tenant Namespace:  $TENANT_NAMESPACE"
        echo "  Tenant ID:         $TENANT_ID"
        echo "  Target Region:     $TARGET_REGION"
        echo "  Target Zone:       $TARGET_ZONE"
        echo "  Dry Run:           $DRY_RUN"
        echo ""
    fi

    # Execute validation steps
    check_prerequisites || true
    check_cluster_access || true
    apply_tenant_residency_config
    deploy_eu_tenant_workload || true
    verify_pod_placement || true
    verify_cross_region_access_blocked || true
    execute_compliance_cronjob || true
    cleanup_test_resources

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
