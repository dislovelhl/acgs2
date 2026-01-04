#!/bin/bash
# =============================================================================
# Pod CIDR Verification Script for Istio Multi-Cluster
# =============================================================================
# This script verifies that Pod CIDR ranges do not overlap between Kubernetes
# clusters. CIDR overlap will break Istio service mesh routing and must be
# prevented before deploying a multi-cluster mesh.
#
# Usage:
#   ./verify-pod-cidr.sh [OPTIONS] <cluster1-context> <cluster2-context> [...]
#
# Options:
#   --dry-run        Validate script without executing kubectl commands
#   --json           Output results in JSON format
#   --verbose        Show detailed CIDR information
#   --help           Show this help message
#
# Examples:
#   ./verify-pod-cidr.sh region1 region2
#   ./verify-pod-cidr.sh --verbose us-east-1 eu-west-1 ap-southeast-1
#   ./verify-pod-cidr.sh --json cluster1 cluster2
#
# Requirements:
#   - kubectl (for cluster access)
#   - Valid kubeconfig with contexts for all specified clusters
#
# Critical:
#   Pod CIDR overlap will break Istio mesh routing! This check is MANDATORY
#   before deploying Istio Multi-Primary Multi-Network configuration.
#
# References:
#   - https://istio.io/latest/docs/setup/install/multicluster/
# =============================================================================

set -euo pipefail

# Configuration
DRY_RUN=false
JSON_OUTPUT=false
VERBOSE=false
CLUSTERS=()

# Color output for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${BLUE}[INFO]${NC} $1"
    fi
}

log_success() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${GREEN}[SUCCESS]${NC} $1"
    fi
}

log_warn() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${YELLOW}[WARN]${NC} $1"
    fi
}

log_error() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${RED}[ERROR]${NC} $1" >&2
    fi
}

log_verbose() {
    if [[ "$VERBOSE" == "true" ]] && [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${CYAN}[VERBOSE]${NC} $1"
    fi
}

# Show help message
show_help() {
    grep '^#' "$0" | grep -v '#!/bin/bash' | sed 's/^# //' | sed 's/^#//'
    exit 0
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
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
            --help|-h)
                show_help
                ;;
            -*)
                log_error "Unknown option: $1"
                show_help
                ;;
            *)
                CLUSTERS+=("$1")
                shift
                ;;
        esac
    done

    # Validate minimum cluster count
    if [[ ${#CLUSTERS[@]} -lt 2 ]]; then
        log_error "At least two cluster contexts are required"
        log_error "Usage: $0 [OPTIONS] <cluster1-context> <cluster2-context> [...]"
        exit 1
    fi
}

# Check required dependencies
check_dependencies() {
    local missing_deps=()

    if ! command -v kubectl &> /dev/null; then
        missing_deps+=("kubectl")
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        log_error "Please install the missing tools and try again."
        return 1
    fi

    log_success "All required dependencies are available"
    return 0
}

# Validate cluster context is accessible
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

# Convert IP address to integer for comparison
ip_to_int() {
    local ip="$1"
    local a b c d

    IFS='.' read -r a b c d <<< "$ip"
    echo $(( (a << 24) + (b << 16) + (c << 8) + d ))
}

# Convert integer back to IP address
int_to_ip() {
    local int="$1"
    echo "$(( (int >> 24) & 255 )).$(( (int >> 16) & 255 )).$(( (int >> 8) & 255 )).$(( int & 255 ))"
}

# Parse CIDR and return start and end IP as integers
parse_cidr() {
    local cidr="$1"
    local ip prefix

    ip="${cidr%/*}"
    prefix="${cidr#*/}"

    local ip_int
    ip_int=$(ip_to_int "$ip")

    # Calculate network mask
    local mask=$(( 0xffffffff << (32 - prefix) & 0xffffffff ))
    local network_int=$(( ip_int & mask ))
    local broadcast_int=$(( network_int | (mask ^ 0xffffffff) ))

    echo "$network_int $broadcast_int"
}

# Check if two CIDR ranges overlap
cidrs_overlap() {
    local cidr1="$1"
    local cidr2="$2"

    local range1 range2
    range1=$(parse_cidr "$cidr1")
    range2=$(parse_cidr "$cidr2")

    local start1 end1 start2 end2
    read -r start1 end1 <<< "$range1"
    read -r start2 end2 <<< "$range2"

    # Check for overlap: ranges overlap if start1 <= end2 AND start2 <= end1
    if [[ $start1 -le $end2 ]] && [[ $start2 -le $end1 ]]; then
        return 0  # Overlapping
    else
        return 1  # Not overlapping
    fi
}

# Get Pod CIDR from a cluster
get_pod_cidr() {
    local context="$1"

    if [[ "$DRY_RUN" == "true" ]]; then
        # Return sample CIDRs for dry run
        case "$context" in
            *region1*|*cluster1*|*us-east*)
                echo "10.244.0.0/16"
                ;;
            *region2*|*cluster2*|*eu-west*)
                echo "10.245.0.0/16"
                ;;
            *region3*|*cluster3*|*ap-*)
                echo "10.246.0.0/16"
                ;;
            *)
                echo "10.244.0.0/16"
                ;;
        esac
        return 0
    fi

    log_verbose "Fetching Pod CIDR from cluster: $context"

    # Try multiple methods to get Pod CIDR
    local cidr=""

    # Method 1: Get from kube-controller-manager
    cidr=$(kubectl --context="$context" get configmap -n kube-system kubeadm-config -o jsonpath='{.data.ClusterConfiguration}' 2>/dev/null | grep -oP 'podSubnet:\s*\K[0-9./]+' || true)

    # Method 2: Get from cluster-info dump
    if [[ -z "$cidr" ]]; then
        cidr=$(kubectl --context="$context" cluster-info dump 2>/dev/null | grep -oP '(?<=--cluster-cidr=)[0-9./]+' | head -1 || true)
    fi

    # Method 3: Get from kube-proxy configmap
    if [[ -z "$cidr" ]]; then
        cidr=$(kubectl --context="$context" get configmap -n kube-system kube-proxy -o jsonpath='{.data.config\.conf}' 2>/dev/null | grep -oP 'clusterCIDR:\s*\K[0-9./]+' || true)
    fi

    # Method 4: Get from node PodCIDR
    if [[ -z "$cidr" ]]; then
        local node_cidr
        node_cidr=$(kubectl --context="$context" get nodes -o jsonpath='{.items[0].spec.podCIDR}' 2>/dev/null || true)
        if [[ -n "$node_cidr" ]]; then
            # Convert node CIDR to cluster CIDR (e.g., 10.244.0.0/24 -> 10.244.0.0/16)
            local base_ip="${node_cidr%/*}"
            local parts
            IFS='.' read -ra parts <<< "$base_ip"
            cidr="${parts[0]}.${parts[1]}.0.0/16"
        fi
    fi

    # Method 5: Get from CNI configuration
    if [[ -z "$cidr" ]]; then
        cidr=$(kubectl --context="$context" get pods -n kube-system -l k8s-app=calico-node -o jsonpath='{.items[0].spec.containers[0].env[?(@.name=="CALICO_IPV4POOL_CIDR")].value}' 2>/dev/null | head -1 || true)
    fi

    if [[ -z "$cidr" ]]; then
        log_error "Could not determine Pod CIDR for cluster: $context"
        log_error "Please ensure you have access to the cluster and try specifying the CIDR manually"
        return 1
    fi

    echo "$cidr"
}

# Get Service CIDR from a cluster
get_service_cidr() {
    local context="$1"

    if [[ "$DRY_RUN" == "true" ]]; then
        # Return sample Service CIDRs for dry run
        case "$context" in
            *region1*|*cluster1*|*us-east*)
                echo "10.96.0.0/16"
                ;;
            *region2*|*cluster2*|*eu-west*)
                echo "10.97.0.0/16"
                ;;
            *region3*|*cluster3*|*ap-*)
                echo "10.98.0.0/16"
                ;;
            *)
                echo "10.96.0.0/16"
                ;;
        esac
        return 0
    fi

    log_verbose "Fetching Service CIDR from cluster: $context"

    local cidr=""

    # Method 1: Get from kube-apiserver
    cidr=$(kubectl --context="$context" cluster-info dump 2>/dev/null | grep -oP '(?<=--service-cluster-ip-range=)[0-9./]+' | head -1 || true)

    # Method 2: Get from kubeadm config
    if [[ -z "$cidr" ]]; then
        cidr=$(kubectl --context="$context" get configmap -n kube-system kubeadm-config -o jsonpath='{.data.ClusterConfiguration}' 2>/dev/null | grep -oP 'serviceSubnet:\s*\K[0-9./]+' || true)
    fi

    # Method 3: Infer from kubernetes service IP
    if [[ -z "$cidr" ]]; then
        local svc_ip
        svc_ip=$(kubectl --context="$context" get svc kubernetes -n default -o jsonpath='{.spec.clusterIP}' 2>/dev/null || true)
        if [[ -n "$svc_ip" ]]; then
            local parts
            IFS='.' read -ra parts <<< "$svc_ip"
            cidr="${parts[0]}.${parts[1]}.0.0/16"
        fi
    fi

    echo "$cidr"
}

# Main verification logic
verify_cidrs() {
    declare -A pod_cidrs
    declare -A service_cidrs
    local overlaps=()
    local warnings=()

    # Collect CIDRs from all clusters
    log_info "Collecting CIDR information from ${#CLUSTERS[@]} clusters..."
    echo ""

    for context in "${CLUSTERS[@]}"; do
        validate_cluster_context "$context" || exit 1

        local pod_cidr service_cidr
        pod_cidr=$(get_pod_cidr "$context") || exit 1
        service_cidr=$(get_service_cidr "$context") || true

        pod_cidrs["$context"]="$pod_cidr"
        if [[ -n "$service_cidr" ]]; then
            service_cidrs["$context"]="$service_cidr"
        fi

        if [[ "$VERBOSE" == "true" ]]; then
            log_verbose "Cluster: $context"
            log_verbose "  Pod CIDR: $pod_cidr"
            if [[ -n "$service_cidr" ]]; then
                log_verbose "  Service CIDR: $service_cidr"
            fi
        fi
    done

    echo ""
    log_info "Checking for CIDR overlaps..."
    echo ""

    # Check for Pod CIDR overlaps between all cluster pairs
    local cluster_array=("${CLUSTERS[@]}")
    local num_clusters=${#cluster_array[@]}

    for ((i = 0; i < num_clusters; i++)); do
        for ((j = i + 1; j < num_clusters; j++)); do
            local cluster1="${cluster_array[$i]}"
            local cluster2="${cluster_array[$j]}"
            local cidr1="${pod_cidrs[$cluster1]}"
            local cidr2="${pod_cidrs[$cluster2]}"

            log_verbose "Checking: $cluster1 ($cidr1) vs $cluster2 ($cidr2)"

            if cidrs_overlap "$cidr1" "$cidr2"; then
                overlaps+=("Pod CIDR overlap detected: $cluster1 ($cidr1) <-> $cluster2 ($cidr2)")
            fi

            # Also check service CIDRs if available
            if [[ -n "${service_cidrs[$cluster1]:-}" ]] && [[ -n "${service_cidrs[$cluster2]:-}" ]]; then
                local svc_cidr1="${service_cidrs[$cluster1]}"
                local svc_cidr2="${service_cidrs[$cluster2]}"

                if cidrs_overlap "$svc_cidr1" "$svc_cidr2"; then
                    warnings+=("Service CIDR overlap: $cluster1 ($svc_cidr1) <-> $cluster2 ($svc_cidr2)")
                fi
            fi

            # Cross-check: Pod CIDR vs Service CIDR
            if [[ -n "${service_cidrs[$cluster2]:-}" ]]; then
                if cidrs_overlap "$cidr1" "${service_cidrs[$cluster2]}"; then
                    overlaps+=("Pod/Service CIDR conflict: $cluster1 Pod ($cidr1) <-> $cluster2 Service (${service_cidrs[$cluster2]})")
                fi
            fi

            if [[ -n "${service_cidrs[$cluster1]:-}" ]]; then
                if cidrs_overlap "$cidr2" "${service_cidrs[$cluster1]}"; then
                    overlaps+=("Pod/Service CIDR conflict: $cluster2 Pod ($cidr2) <-> $cluster1 Service (${service_cidrs[$cluster1]})")
                fi
            fi
        done
    done

    # Output results
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        output_json "${overlaps[@]}" "${warnings[@]}"
    else
        output_text "${overlaps[@]}" "${warnings[@]}"
    fi

    # Return appropriate exit code
    if [[ ${#overlaps[@]} -gt 0 ]]; then
        return 1
    fi
    return 0
}

# Output results in JSON format
output_json() {
    local overlaps=("$@")
    local num_overlaps=${#overlaps[@]}

    echo "{"
    echo "  \"status\": \"$([ $num_overlaps -eq 0 ] && echo "PASS" || echo "FAIL")\","
    echo "  \"clusters\": ["

    local first=true
    for context in "${CLUSTERS[@]}"; do
        if [[ "$first" == "true" ]]; then
            first=false
        else
            echo ","
        fi
        local pod_cidr=""
        local service_cidr=""

        # Get CIDRs (reusing from collected data would be better, but keeping it simple)
        pod_cidr=$(get_pod_cidr "$context" 2>/dev/null) || pod_cidr="unknown"
        service_cidr=$(get_service_cidr "$context" 2>/dev/null) || service_cidr="unknown"

        printf '    {"context": "%s", "podCIDR": "%s", "serviceCIDR": "%s"}' "$context" "$pod_cidr" "$service_cidr"
    done
    echo ""
    echo "  ],"
    echo "  \"overlaps\": ["

    first=true
    for overlap in "${overlaps[@]}"; do
        if [[ "$first" == "true" ]]; then
            first=false
        else
            echo ","
        fi
        printf '    "%s"' "$overlap"
    done
    echo ""
    echo "  ],"
    echo "  \"timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\""
    echo "}"
}

# Output results in text format
output_text() {
    local -a args=("$@")
    local overlaps=()
    local warnings=()

    # Separate overlaps from warnings
    for item in "${args[@]}"; do
        if [[ "$item" == "Service CIDR overlap:"* ]]; then
            warnings+=("$item")
        else
            overlaps+=("$item")
        fi
    done

    echo ""
    echo "============================================================"
    echo "  Pod CIDR Verification Results"
    echo "============================================================"
    echo ""
    echo "Clusters analyzed: ${#CLUSTERS[@]}"
    echo ""

    # Display cluster information
    echo "Cluster CIDR Summary:"
    echo "------------------------------------------------------------"
    for context in "${CLUSTERS[@]}"; do
        local pod_cidr service_cidr
        pod_cidr=$(get_pod_cidr "$context" 2>/dev/null) || pod_cidr="unknown"
        service_cidr=$(get_service_cidr "$context" 2>/dev/null) || service_cidr="N/A"
        printf "  %-30s Pod: %-18s Service: %s\n" "$context" "$pod_cidr" "$service_cidr"
    done
    echo ""

    # Display warnings (non-critical)
    if [[ ${#warnings[@]} -gt 0 ]]; then
        echo "------------------------------------------------------------"
        log_warn "Non-critical issues detected (${#warnings[@]}):"
        for warning in "${warnings[@]}"; do
            echo -e "  ${YELLOW}!${NC} $warning"
        done
        echo ""
    fi

    # Display overlaps (critical)
    if [[ ${#overlaps[@]} -gt 0 ]]; then
        echo "------------------------------------------------------------"
        log_error "CRITICAL: CIDR overlaps detected (${#overlaps[@]}):"
        echo ""
        for overlap in "${overlaps[@]}"; do
            echo -e "  ${RED}X${NC} $overlap"
        done
        echo ""
        echo "------------------------------------------------------------"
        echo ""
        log_error "VERIFICATION FAILED"
        echo ""
        echo "Pod CIDR overlap will break Istio mesh routing!"
        echo ""
        echo "Resolution options:"
        echo "  1. Re-provision clusters with non-overlapping Pod CIDRs"
        echo "  2. For existing clusters, some CNIs support CIDR migration"
        echo "  3. Use network policies to isolate overlapping ranges"
        echo ""
        echo "Recommended non-overlapping CIDR ranges:"
        echo "  Cluster 1 (Region 1): 10.244.0.0/16"
        echo "  Cluster 2 (Region 2): 10.245.0.0/16"
        echo "  Cluster 3 (Region 3): 10.246.0.0/16"
        echo ""
        echo "For kind clusters, specify in cluster config:"
        echo "  networking:"
        echo "    podSubnet: \"10.244.0.0/16\""
        echo "    serviceSubnet: \"10.96.0.0/16\""
        echo ""
    else
        echo "------------------------------------------------------------"
        log_success "VERIFICATION PASSED"
        echo ""
        echo "All Pod CIDR ranges are unique and non-overlapping."
        echo "Clusters are safe for Istio Multi-Primary Multi-Network deployment."
        echo ""
    fi

    echo "============================================================"
}

# Dry run mode
run_dry_run() {
    log_info "Running in DRY RUN mode - using sample CIDR values"
    echo ""
    log_info "This mode validates script logic without kubectl access"
    echo ""

    # Display what would be checked
    log_info "Clusters to verify: ${CLUSTERS[*]}"
    echo ""

    # Run verification with sample data
    verify_cidrs
}

# Main execution
main() {
    parse_args "$@"

    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo ""
        echo "============================================================"
        echo "  ACGS2 Pod CIDR Verification for Istio Multi-Cluster"
        echo "============================================================"
        echo ""
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        run_dry_run
        exit $?
    fi

    # Check dependencies
    check_dependencies || exit 1

    # Run verification
    if verify_cidrs; then
        exit 0
    else
        exit 1
    fi
}

# Run main function
main "$@"
