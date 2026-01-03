#!/bin/bash
# =============================================================================
# Shared Root CA Generation Script for Istio Multi-Cluster mTLS
# =============================================================================
# This script generates a shared root CA certificate and key that must be
# distributed to all Istio clusters to enable cross-cluster mTLS communication.
#
# Usage:
#   ./shared-root-ca-setup.sh [OPTIONS]
#
# Options:
#   --dry-run        Validate script without generating certificates
#   --output-dir     Directory to store generated certificates (default: ./certs)
#   --validity-days  Certificate validity period in days (default: 3650)
#   --cluster        Target cluster context for applying secrets
#   --help           Show this help message
#
# Requirements:
#   - openssl (for certificate generation)
#   - kubectl (for applying secrets to clusters)
#
# References:
#   - https://istio.io/latest/docs/tasks/security/cert-management/plugin-ca-cert/
# =============================================================================

set -euo pipefail

# Default configuration
OUTPUT_DIR="./certs"
VALIDITY_DAYS=3650
DRY_RUN=false
CLUSTER_CONTEXT=""
ROOT_CA_CN="ACGS2 Istio Root CA"
ROOT_CA_ORG="ACGS2"
INTERMEDIATE_CA_CN="ACGS2 Istio Intermediate CA"

# Color output for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
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
            --output-dir)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            --validity-days)
                VALIDITY_DAYS="$2"
                shift 2
                ;;
            --cluster)
                CLUSTER_CONTEXT="$2"
                shift 2
                ;;
            --help|-h)
                show_help
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                ;;
        esac
    done
}

# Check required dependencies
check_dependencies() {
    local missing_deps=()

    if ! command -v openssl &> /dev/null; then
        missing_deps+=("openssl")
    fi

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

# Validate configuration
validate_config() {
    log_info "Validating configuration..."

    # Validate validity days
    if ! [[ "$VALIDITY_DAYS" =~ ^[0-9]+$ ]] || [[ "$VALIDITY_DAYS" -lt 1 ]]; then
        log_error "Invalid validity days: $VALIDITY_DAYS (must be a positive integer)"
        return 1
    fi

    # Check OpenSSL version
    local openssl_version
    openssl_version=$(openssl version 2>/dev/null || echo "unknown")
    log_info "OpenSSL version: $openssl_version"

    # Validate output directory is writable (or can be created)
    if [[ "$DRY_RUN" == "false" ]]; then
        if [[ -d "$OUTPUT_DIR" ]]; then
            if [[ ! -w "$OUTPUT_DIR" ]]; then
                log_error "Output directory is not writable: $OUTPUT_DIR"
                return 1
            fi
        else
            # Check if parent directory is writable
            local parent_dir
            parent_dir=$(dirname "$OUTPUT_DIR")
            if [[ ! -w "$parent_dir" ]]; then
                log_error "Cannot create output directory (parent not writable): $OUTPUT_DIR"
                return 1
            fi
        fi
    fi

    log_success "Configuration validated"
    return 0
}

# Generate root CA certificate and key
generate_root_ca() {
    log_info "Generating root CA certificate..."

    local root_key="${OUTPUT_DIR}/root-key.pem"
    local root_cert="${OUTPUT_DIR}/root-cert.pem"
    local root_csr="${OUTPUT_DIR}/root-csr.pem"

    # Generate root CA private key (4096-bit RSA for security)
    log_info "Generating root CA private key (4096-bit RSA)..."
    openssl genrsa -out "$root_key" 4096

    # Generate root CA certificate signing request
    log_info "Creating root CA certificate signing request..."
    openssl req -new -key "$root_key" -out "$root_csr" \
        -subj "/O=${ROOT_CA_ORG}/CN=${ROOT_CA_CN}"

    # Self-sign root CA certificate
    log_info "Self-signing root CA certificate (validity: ${VALIDITY_DAYS} days)..."
    openssl x509 -req -days "$VALIDITY_DAYS" \
        -signkey "$root_key" \
        -in "$root_csr" \
        -out "$root_cert" \
        -extfile <(cat <<EOF
basicConstraints = critical, CA:TRUE
keyUsage = critical, keyCertSign, cRLSign
subjectKeyIdentifier = hash
EOF
)

    # Remove CSR as it's no longer needed
    rm -f "$root_csr"

    # Set secure permissions
    chmod 600 "$root_key"
    chmod 644 "$root_cert"

    log_success "Root CA certificate generated: $root_cert"
    log_success "Root CA private key generated: $root_key"
}

# Generate intermediate CA for a specific cluster
generate_intermediate_ca() {
    local cluster_name="${1:-cluster1}"

    log_info "Generating intermediate CA for cluster: $cluster_name..."

    local root_key="${OUTPUT_DIR}/root-key.pem"
    local root_cert="${OUTPUT_DIR}/root-cert.pem"
    local intermediate_dir="${OUTPUT_DIR}/${cluster_name}"
    local intermediate_key="${intermediate_dir}/ca-key.pem"
    local intermediate_cert="${intermediate_dir}/ca-cert.pem"
    local intermediate_csr="${intermediate_dir}/ca-csr.pem"
    local cert_chain="${intermediate_dir}/cert-chain.pem"
    local root_cert_copy="${intermediate_dir}/root-cert.pem"

    # Create cluster-specific directory
    mkdir -p "$intermediate_dir"

    # Generate intermediate CA private key
    log_info "Generating intermediate CA private key for $cluster_name..."
    openssl genrsa -out "$intermediate_key" 4096

    # Generate intermediate CA certificate signing request
    log_info "Creating intermediate CA CSR for $cluster_name..."
    openssl req -new -key "$intermediate_key" -out "$intermediate_csr" \
        -subj "/O=${ROOT_CA_ORG}/CN=${INTERMEDIATE_CA_CN} - ${cluster_name}"

    # Sign intermediate CA certificate with root CA
    log_info "Signing intermediate CA certificate with root CA..."
    openssl x509 -req -days "$VALIDITY_DAYS" \
        -CA "$root_cert" \
        -CAkey "$root_key" \
        -CAcreateserial \
        -in "$intermediate_csr" \
        -out "$intermediate_cert" \
        -extfile <(cat <<EOF
basicConstraints = critical, CA:TRUE, pathlen:0
keyUsage = critical, keyCertSign, cRLSign
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always, issuer
EOF
)

    # Create certificate chain (intermediate + root)
    cat "$intermediate_cert" "$root_cert" > "$cert_chain"

    # Copy root cert for reference
    cp "$root_cert" "$root_cert_copy"

    # Remove CSR as it's no longer needed
    rm -f "$intermediate_csr"

    # Set secure permissions
    chmod 600 "$intermediate_key"
    chmod 644 "$intermediate_cert" "$cert_chain" "$root_cert_copy"

    log_success "Intermediate CA for $cluster_name generated in: $intermediate_dir"
}

# Apply CA certificates to a Kubernetes cluster as Istio cacerts secret
apply_to_cluster() {
    local cluster_name="${1:-cluster1}"
    local context="${2:-}"

    if [[ -z "$context" ]]; then
        log_warn "No cluster context specified. Skipping secret creation."
        log_info "To apply manually, run:"
        echo ""
        echo "kubectl create namespace istio-system --context=<cluster-context> || true"
        echo "kubectl create secret generic cacerts -n istio-system \\"
        echo "  --from-file=${OUTPUT_DIR}/${cluster_name}/ca-cert.pem \\"
        echo "  --from-file=${OUTPUT_DIR}/${cluster_name}/ca-key.pem \\"
        echo "  --from-file=${OUTPUT_DIR}/${cluster_name}/root-cert.pem \\"
        echo "  --from-file=${OUTPUT_DIR}/${cluster_name}/cert-chain.pem \\"
        echo "  --context=<cluster-context>"
        echo ""
        return 0
    fi

    log_info "Applying CA certificates to cluster context: $context"

    # Ensure istio-system namespace exists
    kubectl create namespace istio-system --context="$context" 2>/dev/null || true

    # Delete existing cacerts secret if it exists
    kubectl delete secret cacerts -n istio-system --context="$context" 2>/dev/null || true

    # Create new cacerts secret
    kubectl create secret generic cacerts -n istio-system \
        --from-file="${OUTPUT_DIR}/${cluster_name}/ca-cert.pem" \
        --from-file="${OUTPUT_DIR}/${cluster_name}/ca-key.pem" \
        --from-file="${OUTPUT_DIR}/${cluster_name}/root-cert.pem" \
        --from-file="${OUTPUT_DIR}/${cluster_name}/cert-chain.pem" \
        --context="$context"

    log_success "CA certificates applied to cluster: $context"
}

# Verify generated certificates
verify_certificates() {
    local cluster_name="${1:-cluster1}"

    log_info "Verifying generated certificates for $cluster_name..."

    local root_cert="${OUTPUT_DIR}/root-cert.pem"
    local intermediate_cert="${OUTPUT_DIR}/${cluster_name}/ca-cert.pem"
    local cert_chain="${OUTPUT_DIR}/${cluster_name}/cert-chain.pem"

    # Verify root certificate
    log_info "Verifying root certificate..."
    openssl x509 -in "$root_cert" -noout -text | grep -E "(Subject:|Issuer:|CA:)" || true

    # Verify intermediate certificate
    log_info "Verifying intermediate certificate..."
    openssl x509 -in "$intermediate_cert" -noout -text | grep -E "(Subject:|Issuer:|CA:)" || true

    # Verify certificate chain
    log_info "Verifying certificate chain..."
    if openssl verify -CAfile "$root_cert" "$intermediate_cert" >/dev/null 2>&1; then
        log_success "Certificate chain verification: PASSED"
    else
        log_error "Certificate chain verification: FAILED"
        return 1
    fi

    # Display certificate expiration
    local expiry
    expiry=$(openssl x509 -in "$root_cert" -noout -enddate | cut -d= -f2)
    log_info "Root CA expiration: $expiry"

    expiry=$(openssl x509 -in "$intermediate_cert" -noout -enddate | cut -d= -f2)
    log_info "Intermediate CA expiration: $expiry"

    log_success "All certificate verifications passed"
}

# Display summary of generated files
show_summary() {
    local cluster_name="${1:-cluster1}"

    echo ""
    echo "============================================================"
    echo "  Shared Root CA Generation Complete"
    echo "============================================================"
    echo ""
    echo "Generated files:"
    echo "  Root CA:"
    echo "    - ${OUTPUT_DIR}/root-cert.pem (public certificate)"
    echo "    - ${OUTPUT_DIR}/root-key.pem (private key - KEEP SECURE!)"
    echo ""
    echo "  Cluster '${cluster_name}' Intermediate CA:"
    echo "    - ${OUTPUT_DIR}/${cluster_name}/ca-cert.pem"
    echo "    - ${OUTPUT_DIR}/${cluster_name}/ca-key.pem"
    echo "    - ${OUTPUT_DIR}/${cluster_name}/cert-chain.pem"
    echo "    - ${OUTPUT_DIR}/${cluster_name}/root-cert.pem"
    echo ""
    echo "Next steps:"
    echo "  1. Generate intermediate CAs for additional clusters:"
    echo "     $0 --output-dir ${OUTPUT_DIR} --cluster cluster2"
    echo ""
    echo "  2. Apply to Kubernetes cluster:"
    echo "     kubectl create secret generic cacerts -n istio-system \\"
    echo "       --from-file=${OUTPUT_DIR}/${cluster_name}/ca-cert.pem \\"
    echo "       --from-file=${OUTPUT_DIR}/${cluster_name}/ca-key.pem \\"
    echo "       --from-file=${OUTPUT_DIR}/${cluster_name}/root-cert.pem \\"
    echo "       --from-file=${OUTPUT_DIR}/${cluster_name}/cert-chain.pem"
    echo ""
    echo "  3. Install Istio with the shared CA:"
    echo "     istioctl install -f istio-operator-region1.yaml"
    echo ""
    echo "SECURITY WARNING:"
    echo "  - Keep root-key.pem secure and backed up!"
    echo "  - Store in a secrets manager (Vault, AWS Secrets Manager, etc.)"
    echo "  - Never commit private keys to version control"
    echo ""
    echo "============================================================"
}

# Dry run mode - validate without generating
run_dry_run() {
    log_info "Running in DRY RUN mode - no certificates will be generated"
    echo ""

    # Check dependencies
    check_dependencies || exit 1

    # Validate configuration
    validate_config || exit 1

    echo ""
    log_info "Dry run validation:"
    echo "  - Output directory: ${OUTPUT_DIR}"
    echo "  - Validity period: ${VALIDITY_DAYS} days"
    echo "  - Root CA CN: ${ROOT_CA_CN}"
    echo "  - Organization: ${ROOT_CA_ORG}"
    echo ""

    log_info "Would generate the following structure:"
    echo "  ${OUTPUT_DIR}/"
    echo "    ├── root-cert.pem"
    echo "    ├── root-key.pem"
    echo "    └── cluster1/"
    echo "        ├── ca-cert.pem"
    echo "        ├── ca-key.pem"
    echo "        ├── cert-chain.pem"
    echo "        └── root-cert.pem"
    echo ""

    log_success "Dry run validation completed successfully"
    log_info "Remove --dry-run flag to generate certificates"
}

# Main execution
main() {
    parse_args "$@"

    echo ""
    echo "============================================================"
    echo "  ACGS2 Shared Root CA Generation for Istio Multi-Cluster"
    echo "============================================================"
    echo ""

    if [[ "$DRY_RUN" == "true" ]]; then
        run_dry_run
        exit 0
    fi

    # Full execution mode
    check_dependencies || exit 1
    validate_config || exit 1

    # Create output directory
    mkdir -p "$OUTPUT_DIR"
    log_info "Output directory: $OUTPUT_DIR"

    # Check if root CA already exists
    if [[ -f "${OUTPUT_DIR}/root-cert.pem" ]] && [[ -f "${OUTPUT_DIR}/root-key.pem" ]]; then
        log_warn "Root CA already exists in ${OUTPUT_DIR}"
        log_info "Reusing existing root CA for intermediate certificate generation"
    else
        # Generate root CA
        generate_root_ca
    fi

    # Generate intermediate CA for default cluster
    generate_intermediate_ca "cluster1"

    # Verify certificates
    verify_certificates "cluster1"

    # Apply to cluster if context specified
    if [[ -n "$CLUSTER_CONTEXT" ]]; then
        apply_to_cluster "cluster1" "$CLUSTER_CONTEXT"
    fi

    # Show summary
    show_summary "cluster1"
}

# Run main function
main "$@"
