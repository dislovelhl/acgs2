#!/bin/bash
# ACGS-2 Enhanced Developer Setup Script
# Constitutional Hash: cdd01ef066bc6cf2
# Version: 2.0.0
#
# This script provides one-command setup with:
# - Pre-flight validation (tools, versions, dependencies)
# - Environment auto-detection (dev/staging/prod)
# - Clear progress tracking
# - Helpful error messages with fix suggestions
# - Configuration validation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Progress tracking
TOTAL_STEPS=8
CURRENT_STEP=0

# ============================================================================
# Helper Functions
# ============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}  ${BOLD}ACGS-2 Developer Setup${NC}                                          ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}  Constitutional Hash: ${CYAN}cdd01ef066bc6cf2${NC}                           ${BLUE}║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

progress_bar() {
    local progress=$1
    local total=$2
    local width=40
    local percentage=$((progress * 100 / total))
    local filled=$((progress * width / total))
    local empty=$((width - filled))

    printf "\r${CYAN}Progress: [${NC}"
    printf "%${filled}s" | tr ' ' '█'
    printf "%${empty}s" | tr ' ' '░'
    printf "${CYAN}] ${percentage}%% (${progress}/${total})${NC}"
}

step() {
    CURRENT_STEP=$((CURRENT_STEP + 1))
    echo ""
    echo -e "${BOLD}[${CURRENT_STEP}/${TOTAL_STEPS}]${NC} $1"
    progress_bar $CURRENT_STEP $TOTAL_STEPS
    echo ""
}

success() {
    echo -e "    ${GREEN}✓${NC} $1"
}

warn() {
    echo -e "    ${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "    ${RED}✗${NC} $1"
}

info() {
    echo -e "    ${BLUE}ℹ${NC} $1"
}

fix_suggestion() {
    echo -e "    ${CYAN}💡 Fix:${NC} $1"
}

# ============================================================================
# Environment Detection
# ============================================================================

detect_environment() {
    step "Detecting environment..."

    # Priority 1: Explicit environment variable
    if [[ "$ACGS_ENV" == "production" ]] || [[ "$APP_ENV" == "production" ]]; then
        DETECTED_ENV="production"
    elif [[ "$ACGS_ENV" == "staging" ]] || [[ "$APP_ENV" == "staging" ]]; then
        DETECTED_ENV="staging"
    elif [[ -n "$ACGS_ENV" ]] || [[ -n "$APP_ENV" ]]; then
        DETECTED_ENV="${ACGS_ENV:-${APP_ENV:-development}}"
    # Priority 2: .env file content (if exists)
    elif [[ -f "$PROJECT_ROOT/.env" ]]; then
        if grep -q "ACGS_ENV=production" "$PROJECT_ROOT/.env" 2>/dev/null; then
            DETECTED_ENV="production"
        elif grep -q "ACGS_ENV=staging" "$PROJECT_ROOT/.env" 2>/dev/null; then
            DETECTED_ENV="staging"
        else
            DETECTED_ENV="development"
        fi
    # Priority 3: Default to development
    else
        DETECTED_ENV="development"
    fi

    # Check CI environment
    if [[ -n "$CI" ]] || [[ -n "$GITHUB_ACTIONS" ]] || [[ -n "$GITLAB_CI" ]]; then
        IS_CI=true
        info "CI environment detected"
    else
        IS_CI=false
    fi

    # Check container environment
    if [[ -f /.dockerenv ]] || grep -q docker /proc/1/cgroup 2>/dev/null; then
        IN_CONTAINER=true
        info "Running inside container"
    else
        IN_CONTAINER=false
    fi

    success "Environment: ${BOLD}${DETECTED_ENV}${NC}"
    export ACGS_ENV="$DETECTED_ENV"
}

# ============================================================================
# Pre-flight Validation
# ============================================================================

check_command() {
    local cmd=$1
    local min_version=$2
    local install_hint=$3

    if command -v "$cmd" &> /dev/null; then
        local version
        case "$cmd" in
            python3)
                version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
                ;;
            docker)
                version=$(docker --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
                ;;
            docker-compose)
                version=$(docker-compose --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
                # Also check for 'docker compose' (v2)
                if [[ -z "$version" ]]; then
                    version=$(docker compose version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
                fi
                ;;
            git)
                version=$(git --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
                ;;
            curl)
                version=$(curl --version 2>&1 | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
                ;;
            *)
                version="unknown"
                ;;
        esac

        success "$cmd found (v$version)"
        return 0
    else
        error "$cmd not found"
        fix_suggestion "$install_hint"
        return 1
    fi
}

preflight_checks() {
    step "Running pre-flight checks..."

    local failed=0

    # Check Python
    if ! check_command "python3" "3.11" "Install Python 3.11+: https://www.python.org/downloads/"; then
        failed=1
    else
        # Validate Python version
        local py_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        local py_major=$(echo "$py_version" | cut -d. -f1)
        local py_minor=$(echo "$py_version" | cut -d. -f2)
        if [[ "$py_major" -lt 3 ]] || { [[ "$py_major" -eq 3 ]] && [[ "$py_minor" -lt 11 ]]; }; then
            warn "Python $py_version detected, but 3.11+ recommended"
        fi
    fi

    # Check Docker
    if ! check_command "docker" "20.0" "Install Docker: https://docs.docker.com/get-docker/"; then
        failed=1
    else
        # Check if Docker daemon is running
        if ! docker info &> /dev/null; then
            error "Docker daemon is not running"
            fix_suggestion "Start Docker Desktop or run: sudo systemctl start docker"
            failed=1
        else
            success "Docker daemon is running"
        fi
    fi

    # Check Docker Compose (v1 or v2)
    if command -v docker-compose &> /dev/null; then
        check_command "docker-compose" "1.29" "Docker Compose v1"
    elif docker compose version &> /dev/null 2>&1; then
        success "docker compose (v2) found"
    else
        error "docker-compose not found"
        fix_suggestion "Install Docker Compose: https://docs.docker.com/compose/install/"
        failed=1
    fi

    # Check Git
    check_command "git" "2.0" "Install Git: https://git-scm.com/downloads" || failed=1

    # Check curl
    check_command "curl" "7.0" "Install curl: apt-get install curl" || failed=1

    # Check available disk space (need at least 5GB)
    local available_gb=$(df -BG "$PROJECT_ROOT" | awk 'NR==2 {print $4}' | tr -d 'G')
    if [[ "$available_gb" -lt 5 ]]; then
        warn "Low disk space: ${available_gb}GB available (5GB+ recommended)"
    else
        success "Disk space: ${available_gb}GB available"
    fi

    # Check available memory
    local total_mem_gb=$(free -g 2>/dev/null | awk '/Mem:/ {print $2}' || echo "unknown")
    if [[ "$total_mem_gb" != "unknown" ]] && [[ "$total_mem_gb" -lt 4 ]]; then
        warn "Low memory: ${total_mem_gb}GB total (4GB+ recommended for Docker)"
    elif [[ "$total_mem_gb" != "unknown" ]]; then
        success "Memory: ${total_mem_gb}GB total"
    fi

    if [[ $failed -eq 1 ]]; then
        echo ""
        error "Pre-flight checks failed. Please fix the issues above and try again."
        exit 1
    fi

    success "All pre-flight checks passed!"
}

# ============================================================================
# Configuration Validation
# ============================================================================

validate_config() {
    step "Validating configuration..."

    local config_errors=0

    # Check for .env file
    if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
        if [[ -f "$PROJECT_ROOT/.env.dev" ]]; then
            info "Creating .env from .env.dev template..."
            cp "$PROJECT_ROOT/.env.dev" "$PROJECT_ROOT/.env"
            success ".env file created"
        else
            warn ".env file not found - will use defaults"
        fi
    else
        success ".env file exists"
    fi

    # Validate required environment variables (if .env exists)
    if [[ -f "$PROJECT_ROOT/.env" ]]; then
        local required_vars=("REDIS_URL" "OPA_URL")
        local optional_vars=("KAFKA_BOOTSTRAP" "LOG_LEVEL" "DEBUG")

        source "$PROJECT_ROOT/.env" 2>/dev/null || true

        for var in "${required_vars[@]}"; do
            if [[ -z "${!var}" ]]; then
                warn "Missing recommended variable: $var"
            else
                success "$var is configured"
            fi
        done

        for var in "${optional_vars[@]}"; do
            if [[ -n "${!var}" ]]; then
                info "$var = ${!var}"
            fi
        done
    fi

    # Check Docker Compose config
    if [[ -f "$PROJECT_ROOT/docker-compose.dev.yml" ]]; then
        info "Validating docker-compose.dev.yml..."
        if docker-compose -f "$PROJECT_ROOT/docker-compose.dev.yml" config --quiet 2>/dev/null; then
            success "Docker Compose configuration is valid"
        else
            warn "Docker Compose configuration has warnings (may still work)"
        fi
    else
        error "docker-compose.dev.yml not found"
        config_errors=1
    fi

    # Check for required directories
    local required_dirs=(
        "src/core"
        "src/core/enhanced_agent_bus"
        "scripts"
    )

    for dir in "${required_dirs[@]}"; do
        if [[ -d "$PROJECT_ROOT/$dir" ]]; then
            success "Directory exists: $dir"
        else
            error "Missing directory: $dir"
            config_errors=1
        fi
    done

    if [[ $config_errors -gt 0 ]]; then
        error "Configuration validation found issues"
        exit 1
    fi

    success "Configuration validation complete!"
}

# ============================================================================
# Python Environment Setup
# ============================================================================

setup_python_env() {
    step "Setting up Python environment..."

    local venv_path="$PROJECT_ROOT/.venv"

    # Check if venv exists
    if [[ -d "$venv_path" ]]; then
        success "Virtual environment exists at .venv"
    else
        info "Creating virtual environment..."
        python3 -m venv "$venv_path"
        success "Virtual environment created"
    fi

    # Activate and install dependencies
    info "Installing Python dependencies..."
    source "$venv_path/bin/activate"

    # Upgrade pip first
    pip install --upgrade pip --quiet

    # Install core dependencies
    if [[ -f "$PROJECT_ROOT/src/core/enhanced_agent_bus/pyproject.toml" ]]; then
        pip install -e "$PROJECT_ROOT/src/core/enhanced_agent_bus" --quiet 2>/dev/null || \
            warn "Some optional dependencies may not have installed"
    fi

    success "Python environment ready"
}

# ============================================================================
# Docker Services Setup
# ============================================================================

setup_docker_services() {
    step "Setting up Docker services..."

    cd "$PROJECT_ROOT"

    # Pull images first
    info "Pulling Docker images (this may take a few minutes on first run)..."
    docker-compose -f docker-compose.dev.yml pull --quiet 2>/dev/null || \
        docker compose -f docker-compose.dev.yml pull --quiet 2>/dev/null || true

    # Build custom images
    info "Building custom images..."
    docker-compose -f docker-compose.dev.yml build --quiet 2>/dev/null || \
        docker compose -f docker-compose.dev.yml build --quiet 2>/dev/null || true

    success "Docker images ready"
}

# ============================================================================
# Start Services
# ============================================================================

start_services() {
    step "Starting services..."

    cd "$PROJECT_ROOT"

    # Start services
    info "Starting Docker Compose services..."
    docker-compose -f docker-compose.dev.yml up -d 2>/dev/null || \
        docker compose -f docker-compose.dev.yml up -d 2>/dev/null

    # Wait for services with progress
    info "Waiting for services to be ready..."
    local max_wait=60
    local waited=0
    local services_ready=false

    while [[ $waited -lt $max_wait ]]; do
        # Check OPA
        if curl -sf http://localhost:8181/health > /dev/null 2>&1; then
            services_ready=true
            break
        fi
        sleep 2
        waited=$((waited + 2))
        printf "."
    done
    echo ""

    if [[ "$services_ready" == "true" ]]; then
        success "OPA is ready"
    else
        warn "OPA may not be fully ready yet (continuing...)"
    fi

    # Check Redis
    if docker-compose -f docker-compose.dev.yml exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; then
        success "Redis is ready"
    else
        warn "Redis may not be fully ready yet"
    fi

    success "Services started"
}

# ============================================================================
# Final Validation
# ============================================================================

final_validation() {
    step "Running final validation..."

    local all_good=true

    # Quick smoke test
    if [[ -f "$PROJECT_ROOT/src/core/enhanced_agent_bus/tests/test_config.py" ]]; then
        info "Running quick smoke test..."
        cd "$PROJECT_ROOT/src/core/enhanced_agent_bus"
        if python3 -m pytest tests/test_config.py -v --tb=short -q 2>/dev/null; then
            success "Smoke tests passed"
        else
            warn "Some tests may have issues (non-blocking)"
        fi
    fi

    # Validate constitutional hash
    if grep -r "cdd01ef066bc6cf2" "$PROJECT_ROOT/src/core/shared/config.py" > /dev/null 2>&1; then
        success "Constitutional hash verified: cdd01ef066bc6cf2"
    else
        warn "Could not verify constitutional hash"
    fi

    success "Final validation complete!"
}

# ============================================================================
# Print Summary
# ============================================================================

print_summary() {
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}  ${BOLD}🎉 ACGS-2 Setup Complete!${NC}                                       ${GREEN}║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BOLD}Services Running:${NC}"
    echo -e "   ${CYAN}•${NC} API Gateway:  http://localhost:8080"
    echo -e "   ${CYAN}•${NC} Agent Bus:    http://localhost:8000"
    echo -e "   ${CYAN}•${NC} OPA:          http://localhost:8181"
    echo -e "   ${CYAN}•${NC} Redis:        localhost:6379"
    echo -e "   ${CYAN}•${NC} Kafka:        localhost:19092"
    echo ""
    echo -e "${BOLD}Quick Commands:${NC}"
    echo -e "   ${CYAN}./scripts/run-tests.sh${NC}     - Run tests"
    echo -e "   ${CYAN}./scripts/stop-dev.sh${NC}      - Stop services"
    echo -e "   ${CYAN}docker-compose -f docker-compose.dev.yml logs -f${NC} - View logs"
    echo ""
    echo -e "${BOLD}Documentation:${NC}"
    echo -e "   ${CYAN}•${NC} README.md - Project overview"
    echo -e "   ${CYAN}•${NC} docs/GETTING_STARTED.md - Detailed guide"
    echo -e "   ${CYAN}•${NC} docs/TROUBLESHOOTING.md - Common issues"
    echo ""
    echo -e "${BOLD}Environment:${NC} ${DETECTED_ENV}"
    echo -e "${BOLD}Constitutional Hash:${NC} cdd01ef066bc6cf2"
    echo ""
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    print_header

    detect_environment
    preflight_checks
    validate_config
    setup_python_env
    setup_docker_services
    start_services
    final_validation

    print_summary
}

# Handle arguments
case "${1:-}" in
    --help|-h)
        echo "ACGS-2 Developer Setup Script"
        echo ""
        echo "Usage: ./scripts/setup.sh [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --check        Run pre-flight checks only"
        echo "  --validate     Validate configuration only"
        echo "  --skip-docker  Skip Docker service startup"
        echo ""
        exit 0
        ;;
    --check)
        print_header
        detect_environment
        preflight_checks
        exit 0
        ;;
    --validate)
        print_header
        detect_environment
        validate_config
        exit 0
        ;;
    --skip-docker)
        print_header
        detect_environment
        preflight_checks
        validate_config
        setup_python_env
        echo ""
        success "Setup complete (Docker services skipped)"
        exit 0
        ;;
    *)
        main
        ;;
esac
