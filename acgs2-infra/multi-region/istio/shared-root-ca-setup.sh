#!/bin/bash
# Shared Root CA Setup for Istio Multi-Cluster mTLS
# This script generates and distributes a shared root certificate for cross-cluster mTLS

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CA_DIR="${SCRIPT_DIR}/ca"
CA_CERT="${CA_DIR}/root-cert.pem"
CA_KEY="${CA_DIR}/root-key.pem"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create CA directory
log_info "Creating CA directory: ${CA_DIR}"
mkdir -p "${CA_DIR}"

# Check if CA already exists
if [[ -f "${CA_CERT}" ]] && [[ -f "${CA_KEY}" ]]; then
    log_warn "Root CA already exists. Skipping generation."
    log_info "Existing CA: ${CA_CERT}"
else
    # Generate root CA private key
    log_info "Generating root CA private key..."
    openssl genrsa -out "${CA_KEY}" 4096

    # Generate root CA certificate
    log_info "Generating root CA certificate..."
    openssl req -x509 -new -nodes -key "${CA_KEY}" -sha256 -days 3650 \
        -out "${CA_CERT}" \
        -subj "/C=US/ST=California/L=San Francisco/O=ACGS-2/OU=Platform/CN=ACGS-2 Root CA"

    log_info "Root CA generated successfully"
    log_info "Certificate: ${CA_CERT}"
    log_info "Private Key: ${CA_KEY}"
fi

# Display CA information
log_info "Root CA Information:"
openssl x509 -in "${CA_CERT}" -text -noout | head -10

# Create Kubernetes secrets for each region
# Note: In production, distribute these securely to each cluster
log_info "Creating Kubernetes secret manifests for each region..."

# Region 1 CA Secret
cat > "${CA_DIR}/region1-ca-secret.yaml" << EOF
apiVersion: v1
kind: Secret
metadata:
  name: cacerts
  namespace: istio-system
  labels:
    security.istio.io/tlsMode: istio
    networking.istio.io/gatewayType: ingress
type: Opaque
data:
  ca-cert.pem: $(base64 -w 0 "${CA_CERT}")
  ca-key.pem: $(base64 -w 0 "${CA_KEY}")
  cert-chain.pem: $(base64 -w 0 "${CA_CERT}")
  root-cert.pem: $(base64 -w 0 "${CA_CERT}")
EOF

# Region 2 CA Secret
cat > "${CA_DIR}/region2-ca-secret.yaml" << EOF
apiVersion: v1
kind: Secret
metadata:
  name: cacerts
  namespace: istio-system
  labels:
    security.istio.io/tlsMode: istio
    networking.istio.io/gatewayType: ingress
type: Opaque
data:
  ca-cert.pem: $(base64 -w 0 "${CA_CERT}")
  ca-key.pem: $(base64 -w 0 "${CA_KEY}")
  cert-chain.pem: $(base64 -w 0 "${CA_CERT}")
  root-cert.pem: $(base64 -w 0 "${CA_CERT}")
EOF

log_info "CA secret manifests created:"
log_info "  - ${CA_DIR}/region1-ca-secret.yaml"
log_info "  - ${CA_DIR}/region2-ca-secret.yaml"

# Instructions for distribution
log_warn "IMPORTANT: Distribute these CA secrets to each cluster BEFORE installing Istio"
log_info "To apply to Region 1:"
log_info "  kubectl apply -f ${CA_DIR}/region1-ca-secret.yaml --context=region1"
log_info "To apply to Region 2:"
log_info "  kubectl apply -f ${CA_DIR}/region2-ca-secret.yaml --context=region2"

log_info "Shared root CA setup complete!"
log_info "CA Certificate Subject: ACGS-2 Root CA"
log_info "CA Valid Until: $(openssl x509 -in "${CA_CERT}" -enddate -noout | cut -d= -f2)"
