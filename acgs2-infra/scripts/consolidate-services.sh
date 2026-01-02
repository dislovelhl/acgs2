#!/bin/bash
# ACGS-2 Service Consolidation Script
# Consolidates multiple services into unified deployments

set -euo pipefail

# Configuration
NAMESPACE="${NAMESPACE:-acgs2-system}"
RELEASE_NAME="${RELEASE_NAME:-acgs2}"
BACKUP_DIR="${BACKUP_DIR:-./backups/$(date +%Y%m%d_%H%M%S)}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

# Create backup directory
create_backup() {
    log "Creating backup directory: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"

    # Backup current Helm release
    helm get values "$RELEASE_NAME" -n "$NAMESPACE" > "$BACKUP_DIR/values-current.yaml" 2>/dev/null || true
    helm get manifest "$RELEASE_NAME" -n "$NAMESPACE" > "$BACKUP_DIR/manifest-current.yaml" 2>/dev/null || true

    # Backup current deployments
    kubectl get deployments -n "$NAMESPACE" -o yaml > "$BACKUP_DIR/deployments-current.yaml" 2>/dev/null || true
    kubectl get services -n "$NAMESPACE" -o yaml > "$BACKUP_DIR/services-current.yaml" 2>/dev/null || true
    kubectl get configmaps -n "$NAMESPACE" -o yaml > "$BACKUP_DIR/configmaps-current.yaml" 2>/dev/null || true
    kubectl get secrets -n "$NAMESPACE" -o yaml > "$BACKUP_DIR/secrets-current.yaml" 2>/dev/null || true
}

# Validate current deployment
validate_current() {
    log "Validating current deployment..."

    # Check if services are running
    local services=("constitutional-service" "policy-registry" "audit-service" "agent-bus" "api-gateway")
    local failed_services=()

    for service in "${services[@]}"; do
        if ! kubectl get deployment "$RELEASE_NAME-$service" -n "$NAMESPACE" &>/dev/null; then
            if ! kubectl get deployment "$service" -n "$NAMESPACE" &>/dev/null; then
                failed_services+=("$service")
            fi
        fi
    done

    if [ ${#failed_services[@]} -ne 0 ]; then
        error "Missing services: ${failed_services[*]}"
        return 1
    fi

    log "Current deployment validation passed"
}

# Build consolidated container image
build_consolidated_image() {
    log "Building consolidated core governance image..."

    # This would typically be done in CI/CD
    # For now, we'll assume the image exists or provide build instructions

    cat << 'EOF'
To build the consolidated image:

# Build consolidated service
docker build \
  --target consolidated \
  -t acgs2/core-governance:2.0.0 \
  -f docker/Dockerfile.consolidated \
  .

# Push to registry
docker push acgs2/core-governance:2.0.0
EOF
}

# Update Helm values for consolidation
update_helm_values() {
    log "Updating Helm values for consolidation..."

    # Create new values file with consolidated settings
    cat > values-consolidated.yaml << EOF
# ACGS-2 Consolidated Architecture Values
global:
  constitutionalHash: "cdd01ef066bc6cf2"
  architecture:
    consolidated:
      enabled: true
    traditional:
      enabled: false

# Disable individual services
constitutionalService:
  enabled: false
policyRegistry:
  enabled: false
auditService:
  enabled: false

# Enable consolidated services
consolidatedServices:
  coreGovernance:
    enabled: true
  agentBus:
    enabled: true  # Keep separate for performance
  apiGateway:
    enabled: true  # Keep separate for ingress

# Observability (enhanced for consolidated architecture)
global:
  observability:
    jaeger:
      enabled: true
    prometheus:
      enabled: true
    distributedTracing:
      enabled: true
EOF

    log "Created values-consolidated.yaml"
}

# Deploy consolidated architecture
deploy_consolidated() {
    log "Deploying consolidated architecture..."

    # Update Helm release with new values
    helm upgrade --install "$RELEASE_NAME" ./deploy/helm/acgs2 \
      --namespace "$NAMESPACE" \
      --create-namespace \
      --values values-consolidated.yaml \
      --wait \
      --timeout 600s

    log "Consolidated deployment initiated"
}

# Validate consolidated deployment
validate_consolidated() {
    log "Validating consolidated deployment..."

    # Wait for rollout to complete
    kubectl rollout status deployment/"$RELEASE_NAME-core-governance" -n "$NAMESPACE" --timeout=300s
    kubectl rollout status deployment/"$RELEASE_NAME-agent-bus-enhanced" -n "$NAMESPACE" --timeout=300s
    kubectl rollout status deployment/"$RELEASE_NAME-api-gateway-unified" -n "$NAMESPACE" --timeout=300s

    # Test service endpoints
    local endpoints=(
        "http://$RELEASE_NAME-core-governance:8001/health"
        "http://$RELEASE_NAME-core-governance:8003/health"
        "http://$RELEASE_NAME-core-governance:8084/health"
        "http://$RELEASE_NAME-agent-bus-enhanced:8000/health"
        "http://$RELEASE_NAME-api-gateway-unified:8080/health"
    )

    for endpoint in "${endpoints[@]}"; do
        log "Testing endpoint: $endpoint"
        if ! curl -f --max-time 10 "$endpoint" &>/dev/null; then
            error "Endpoint $endpoint is not responding"
            return 1
        fi
    done

    log "Consolidated deployment validation passed"
}

# Performance validation
validate_performance() {
    log "Running performance validation..."

    # Run performance benchmark
    if [ -f "scripts/performance_benchmark.py" ]; then
        python scripts/performance_benchmark.py --quiet --baseline-comparison
    else
        warn "Performance benchmark script not found, skipping automated validation"
    fi

    log "Performance validation completed"
}

# Rollback function
rollback() {
    log "Initiating rollback to previous architecture..."

    # Restore from backup
    if [ -f "$BACKUP_DIR/values-current.yaml" ]; then
        helm upgrade --install "$RELEASE_NAME" ./deploy/helm/acgs2 \
          --namespace "$NAMESPACE" \
          --values "$BACKUP_DIR/values-current.yaml" \
          --wait \
          --timeout 600s
        log "Rollback completed"
    else
        error "No backup values found, manual rollback required"
        return 1
    fi
}

# Main execution
main() {
    local action="${1:-help}"

    case "$action" in
        "plan")
            log "Service Consolidation Plan:"
            echo "1. Backup current deployment"
            echo "2. Validate current state"
            echo "3. Build consolidated images"
            echo "4. Update Helm values"
            echo "5. Deploy consolidated architecture"
            echo "6. Validate deployment"
            echo "7. Performance testing"
            ;;

        "backup")
            create_backup
            ;;

        "validate-current")
            validate_current
            ;;

        "build")
            build_consolidated_image
            ;;

        "deploy")
            create_backup
            validate_current
            update_helm_values
            deploy_consolidated
            validate_consolidated
            validate_performance
            ;;

        "rollback")
            rollback
            ;;

        "full")
            log "Starting full consolidation process..."
            create_backup
            validate_current
            build_consolidated_image
            update_helm_values
            deploy_consolidated

            if validate_consolidated && validate_performance; then
                log "✅ Consolidation completed successfully!"
                log "Old services can be safely removed after 24-hour monitoring period"
            else
                error "❌ Consolidation validation failed, initiating rollback..."
                rollback
                exit 1
            fi
            ;;

        "help"|*)
            cat << EOF
ACGS-2 Service Consolidation Script

USAGE: $0 <action>

ACTIONS:
  plan              Show consolidation plan
  backup            Create backup of current deployment
  validate-current  Validate current deployment state
  build             Build consolidated container images
  deploy            Deploy consolidated architecture
  rollback          Rollback to previous architecture
  full              Run complete consolidation process
  help              Show this help message

ENVIRONMENT VARIABLES:
  NAMESPACE        Target Kubernetes namespace (default: acgs2-system)
  RELEASE_NAME     Helm release name (default: acgs2)
  BACKUP_DIR       Backup directory path (default: ./backups/YYYYMMDD_HHMMSS)

EXAMPLES:
  $0 plan
  $0 backup
  NAMESPACE=test $0 validate-current
  $0 full
EOF
            ;;
    esac
}

# Run main function with all arguments
main "$@"
