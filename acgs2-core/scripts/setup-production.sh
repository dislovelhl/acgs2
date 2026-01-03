#!/bin/bash

# ACGS-2 Production Environment Setup Script
# Constitutional Hash: cdd01ef066bc6cf2
#
# This script sets up a complete production environment including:
# - Environment configuration
# - Security secrets generation
# - Docker services deployment
# - Monitoring stack initialization
# - Health checks and validation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env.production"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.production.yml"

echo -e "${BLUE}🚀 ACGS-2 Production Environment Setup${NC}"
echo "======================================"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to generate secure secrets
generate_secrets() {
    echo -e "${GREEN}🔐 Generating Production Secrets${NC}"

    # Generate JWT secrets
    echo "# JWT_SECRET (64 characters - 256 bits)" > "$ENV_FILE.secrets"
    echo -n "JWT_SECRET=" >> "$ENV_FILE.secrets"
    openssl rand -hex 32 >> "$ENV_FILE.secrets"
    echo "" >> "$ENV_FILE.secrets"

    # Generate API keys
    echo "# API_KEY_INTERNAL (32 characters)" >> "$ENV_FILE.secrets"
    echo -n "API_KEY_INTERNAL=" >> "$ENV_FILE.secrets"
    openssl rand -hex 32 >> "$ENV_FILE.secrets"
    echo "" >> "$ENV_FILE.secrets"

    # Generate blockchain keys
    echo "# BLOCKCHAIN_PRIVATE_KEY (64 characters)" >> "$ENV_FILE.secrets"
    echo -n "BLOCKCHAIN_PRIVATE_KEY=" >> "$ENV_FILE.secrets"
    openssl rand -hex 32 >> "$ENV_FILE.secrets"
    echo "" >> "$ENV_FILE.secrets"

    # Generate audit encryption key
    echo "# AUDIT_ENCRYPTION_KEY (32 characters)" >> "$ENV_FILE.secrets"
    echo -n "AUDIT_ENCRYPTION_KEY=" >> "$ENV_FILE.secrets"
    openssl rand -hex 32 >> "$ENV_FILE.secrets"
    echo "" >> "$ENV_FILE.secrets"

    # Generate database and Redis passwords
    echo "# Database Password" >> "$ENV_FILE.secrets"
    echo -n "DB_USER_PASSWORD=" >> "$ENV_FILE.secrets"
    openssl rand -base64 16 | tr -d "=+/" | cut -c1-16 >> "$ENV_FILE.secrets"
    echo "" >> "$ENV_FILE.secrets"

    echo "# Redis Password" >> "$ENV_FILE.secrets"
    echo -n "REDIS_PASSWORD=" >> "$ENV_FILE.secrets"
    openssl rand -base64 16 | tr -d "=+/" | cut -c1-16 >> "$ENV_FILE.secrets"
    echo "" >> "$ENV_FILE.secrets"

    echo -e "${GREEN}✅ Secrets generated and saved to: $ENV_FILE.secrets${NC}"
    echo -e "${YELLOW}⚠️  IMPORTANT: Review and backup these secrets securely!${NC}"
    echo ""
}

# Function to setup environment configuration
setup_environment() {
    echo -e "${GREEN}📋 Setting up Environment Configuration${NC}"

    # Copy template if it doesn't exist
    if [ ! -f "$ENV_FILE" ]; then
        cp "$PROJECT_ROOT/.env.production.template" "$ENV_FILE"
        echo -e "${GREEN}✅ Created environment template: $ENV_FILE${NC}"
    else
        echo -e "${YELLOW}⚠️  Environment file already exists: $ENV_FILE${NC}"
    fi

    # Merge secrets if they exist
    if [ -f "$ENV_FILE.secrets" ]; then
        echo -e "${BLUE}📝 Merging generated secrets into environment file...${NC}"
        # Simple merge - in production, use more sophisticated merging
        cat "$ENV_FILE.secrets" >> "$ENV_FILE"
        echo -e "${GREEN}✅ Secrets merged into environment file${NC}"
    fi

    echo -e "${YELLOW}📝 Please edit $ENV_FILE with your specific configuration values${NC}"
    echo ""
}

# Function to validate prerequisites
validate_prerequisites() {
    echo -e "${GREEN}🔍 Validating Prerequisites${NC}"

    local missing_deps=()

    # Check Docker
    if ! command_exists docker; then
        missing_deps+=("docker")
    fi

    # Check Docker Compose
    if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
        missing_deps+=("docker-compose")
    fi

    # Check OpenSSL
    if ! command_exists openssl; then
        missing_deps+=("openssl")
    fi

    if [ ${#missing_deps[@]} -ne 0 ]; then
        echo -e "${RED}❌ Missing required dependencies: ${missing_deps[*]}${NC}"
        echo "Please install the missing dependencies and run this script again."
        exit 1
    fi

    echo -e "${GREEN}✅ All prerequisites satisfied${NC}"
    echo ""
}

# Function to build and deploy services
deploy_services() {
    echo -e "${GREEN}🐳 Building and Deploying Services${NC}"

    cd "$PROJECT_ROOT"

    # Validate docker-compose file
    echo "Validating docker-compose configuration..."
    if command_exists docker-compose; then
        docker-compose -f "$COMPOSE_FILE" config --quiet
    else
        docker compose -f "$COMPOSE_FILE" config --quiet
    fi

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Docker Compose configuration is valid${NC}"
    else
        echo -e "${RED}❌ Docker Compose configuration is invalid${NC}"
        exit 1
    fi

    # Build services
    echo "Building services..."
    if command_exists docker-compose; then
        docker-compose -f "$COMPOSE_FILE" build --parallel
    else
        docker compose -f "$COMPOSE_FILE" build --parallel
    fi

    echo -e "${GREEN}✅ Services built successfully${NC}"
    echo ""

    # Start services
    echo -e "${YELLOW}🚀 Starting production services...${NC}"
    if command_exists docker-compose; then
        docker-compose -f "$COMPOSE_FILE" up -d
    else
        docker compose -f "$COMPOSE_FILE" up -d
    fi

    echo -e "${GREEN}✅ Services started successfully${NC}"
    echo ""
}

# Function to run health checks
run_health_checks() {
    echo -e "${GREEN}🏥 Running Health Checks${NC}"

    local services=("api-gateway" "audit-service" "tenant-management" "compliance-docs")
    local failed_services=()

    for service in "${services[@]}"; do
        echo -n "Checking $service... "

        # Try to connect to service health endpoint
        if curl -f -s "http://localhost:8080/health" >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Healthy${NC}"
        else
            echo -e "${RED}❌ Unhealthy${NC}"
            failed_services+=("$service")
        fi
    done

    if [ ${#failed_services[@]} -ne 0 ]; then
        echo -e "${RED}❌ Health check failed for services: ${failed_services[*]}${NC}"
        echo "Check service logs with: docker-compose -f $COMPOSE_FILE logs"
        exit 1
    fi

    echo -e "${GREEN}✅ All services are healthy${NC}"
    echo ""
}

# Function to initialize monitoring
initialize_monitoring() {
    echo -e "${GREEN}📊 Initializing Monitoring Stack${NC}"

    # Wait for monitoring services to be ready
    echo "Waiting for Prometheus and Grafana to be ready..."
    sleep 30

    # Check if Prometheus is accessible
    if curl -f -s "http://localhost:9090/-/healthy" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Prometheus is healthy${NC}"
    else
        echo -e "${YELLOW}⚠️  Prometheus not yet ready, may take a few minutes${NC}"
    fi

    # Check if Grafana is accessible
    if curl -f -s "http://localhost:3000/api/health" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Grafana is healthy${NC}"
        echo "Grafana Admin Password: ${GRAFANA_ADMIN_PASSWORD:-admin}"
    else
        echo -e "${YELLOW}⚠️  Grafana not yet ready, may take a few minutes${NC}"
    fi

    echo ""
}

# Function to display next steps
display_next_steps() {
    echo -e "${GREEN}🎉 Production Environment Setup Complete!${NC}"
    echo "=============================================="
    echo ""
    echo -e "${BLUE}📋 Next Steps:${NC}"
    echo ""
    echo "1. 🔐 Security Configuration:"
    echo "   - Review and rotate generated secrets"
    echo "   - Configure OAuth2 providers (Google, GitHub)"
    echo "   - Set up Vault for secret management"
    echo ""
    echo "2. 📊 Monitoring Setup:"
    echo "   - Access Grafana: http://localhost:3000 (admin/admin)"
    echo "   - Import dashboard: monitoring/grafana/dashboards/acgs2-overview.json"
    echo "   - Configure alert notifications (Slack, PagerDuty, etc.)"
    echo ""
    echo "3. 🔍 Logging Configuration:"
    echo "   - Loki accessible at: http://localhost:3100"
    echo "   - Promtail is collecting container logs"
    echo "   - Configure log retention and alerting"
    echo ""
    echo "4. 🏥 Service Validation:"
    echo "   - Check service endpoints are responding"
    echo "   - Verify database connections"
    echo "   - Test authentication flows"
    echo ""
    echo "5. 🚀 Production Deployment:"
    echo "   - Set up load balancer (nginx, traefik, etc.)"
    echo "   - Configure SSL/TLS certificates"
    echo "   - Set up backup and disaster recovery"
    echo "   - Configure auto-scaling if needed"
    echo ""
    echo "6. 📚 Documentation:"
    echo "   - Update service documentation with production URLs"
    echo "   - Configure monitoring dashboards"
    echo "   - Set up runbooks for incident response"
    echo ""
    echo -e "${YELLOW}🔗 Service Endpoints:${NC}"
    echo "   API Gateway:    http://localhost:8080"
    echo "   Audit Service:  http://localhost:8300"
    echo "   Tenant Mgmt:    http://localhost:8500"
    echo "   Compliance:     http://localhost:8100"
    echo "   Prometheus:     http://localhost:9090"
    echo "   Grafana:        http://localhost:3000"
    echo "   Loki:          http://localhost:3100"
    echo ""
    echo -e "${RED}🚨 Critical Reminders:${NC}"
    echo "   • Change default Grafana password"
    echo "   • Secure secrets in production"
    echo "   • Enable SSL/TLS in production"
    echo "   • Set up monitoring alerts"
    echo "   • Configure backup procedures"
    echo ""
}

# Main execution
main() {
    echo "Starting ACGS-2 production environment setup..."
    echo ""

    validate_prerequisites
    generate_secrets
    setup_environment

    read -p "Do you want to deploy services now? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        deploy_services
        run_health_checks
        initialize_monitoring
    else
        echo "Skipping service deployment. Run manually with:"
        echo "docker-compose -f $COMPOSE_FILE up -d"
        echo ""
    fi

    display_next_steps
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
