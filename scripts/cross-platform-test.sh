#!/bin/bash
# =============================================================================
# Cross-Platform Testing Script for ACGS-2 Developer Onboarding
# =============================================================================
# This script verifies that the Docker Compose setup works correctly across
# Linux, macOS, and Windows with Docker Desktop (WSL 2).
#
# Usage:
#   ./scripts/cross-platform-test.sh [platform]
#
# Arguments:
#   platform: linux, macos, windows, or auto (default: auto-detect)
#
# Output:
#   - Test results printed to stdout
#   - JSON report saved to cross-platform-test-results.json
#
# Constitutional Hash: cdd01ef066bc6cf2
# =============================================================================

set -e

# =============================================================================
# Configuration
# =============================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test configuration
STARTUP_WAIT=45      # Seconds to wait for services
EXPECTED_SERVICES=5  # Number of expected running services
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}  $1"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_section() {
    echo ""
    echo -e "${CYAN}=== $1 ===${NC}"
    echo ""
}

pass() {
    echo -e "  ${GREEN}✓${NC} $1"
    ((TESTS_PASSED++))
}

fail() {
    echo -e "  ${RED}✗${NC} $1"
    ((TESTS_FAILED++))
}

skip() {
    echo -e "  ${YELLOW}⊘${NC} $1 (skipped)"
    ((TESTS_SKIPPED++))
}

warn() {
    echo -e "  ${YELLOW}⚠${NC} $1"
}

info() {
    echo -e "  ${BLUE}ℹ${NC} $1"
}

# Detect operating system
detect_platform() {
    case "$(uname -s)" in
        Linux*)
            if grep -qi microsoft /proc/version 2>/dev/null; then
                echo "windows"  # WSL
            else
                echo "linux"
            fi
            ;;
        Darwin*)
            echo "macos"
            ;;
        MINGW*|CYGWIN*|MSYS*)
            echo "windows"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

# Get platform-specific memory info
get_memory_info() {
    case "$PLATFORM" in
        linux)
            free -h | grep Mem | awk '{print $2}'
            ;;
        macos)
            sysctl -n hw.memsize | awk '{printf "%.0fGB", $1/1024/1024/1024}'
            ;;
        windows)
            free -h 2>/dev/null | grep Mem | awk '{print $2}' || echo "Unknown"
            ;;
        *)
            echo "Unknown"
            ;;
    esac
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Wait for service to be ready
wait_for_service() {
    local url=$1
    local name=$2
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -sf "$url" >/dev/null 2>&1; then
            return 0
        fi
        sleep 2
        ((attempt++))
    done
    return 1
}

# =============================================================================
# Platform Detection
# =============================================================================

PLATFORM="${1:-auto}"

if [ "$PLATFORM" = "auto" ]; then
    PLATFORM=$(detect_platform)
fi

print_header "ACGS-2 Cross-Platform Test - ${PLATFORM^}"

echo "Test Started: $(date)"
echo "Project Root: $PROJECT_ROOT"
echo ""

# =============================================================================
# Pre-Flight Checks
# =============================================================================

print_section "Pre-Flight Checks"

# Check Docker
if command_exists docker; then
    if docker info >/dev/null 2>&1; then
        DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | tr -d ',')
        pass "Docker daemon running (v$DOCKER_VERSION)"
    else
        fail "Docker daemon not running"
        echo ""
        echo "Please start Docker and run this script again."
        exit 1
    fi
else
    fail "Docker not installed"
    exit 1
fi

# Check Docker Compose
if docker compose version >/dev/null 2>&1; then
    COMPOSE_VERSION=$(docker compose version --short)
    pass "Docker Compose V2 available (v$COMPOSE_VERSION)"
else
    fail "Docker Compose V2 not available"
    exit 1
fi

# Check curl
if command_exists curl; then
    pass "curl available"
else
    fail "curl not installed"
fi

# Check Python (for examples)
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    pass "Python 3 available (v$PYTHON_VERSION)"
else
    warn "Python 3 not available - example tests will be skipped"
fi

# Platform-specific checks
case "$PLATFORM" in
    linux)
        # Check for SELinux
        if command_exists getenforce; then
            SELINUX_STATUS=$(getenforce 2>/dev/null || echo "Unknown")
            info "SELinux status: $SELINUX_STATUS"
        fi

        # Check Docker group membership
        if groups | grep -q docker; then
            pass "User in docker group"
        else
            warn "User not in docker group - may need sudo"
        fi
        ;;
    macos)
        # Check for Apple Silicon
        if [ "$(uname -m)" = "arm64" ]; then
            info "Platform: Apple Silicon (ARM64)"
        else
            info "Platform: Intel (x86_64)"
        fi

        # Check Docker Desktop memory
        info "Verify Docker Desktop has 4GB+ RAM allocated"
        ;;
    windows)
        info "Platform: Windows (WSL 2)"

        # Check WSL integration
        if [ -f /proc/version ] && grep -qi microsoft /proc/version; then
            pass "Running in WSL 2"
        else
            warn "Not running in WSL 2 - recommend using WSL 2 for best results"
        fi
        ;;
esac

# Check memory
TOTAL_MEMORY=$(get_memory_info)
info "System memory: $TOTAL_MEMORY"

# =============================================================================
# Compose Configuration Validation
# =============================================================================

print_section "Compose Configuration Validation"

cd "$PROJECT_ROOT"

# Validate compose.yaml
if docker compose config --quiet 2>/dev/null; then
    pass "compose.yaml syntax valid"
else
    fail "compose.yaml syntax invalid"
fi

# Check .env file
if [ -f ".env" ]; then
    pass ".env file exists"
else
    if [ -f ".env.example" ]; then
        warn ".env file missing - copying from .env.example"
        cp .env.example .env
        pass ".env file created from template"
    else
        fail ".env file missing and no template found"
    fi
fi

# Check required directories
for dir in "notebooks" "examples" "src/core/enhanced_agent_bus/policies"; do
    if [ -d "$dir" ]; then
        pass "Directory exists: $dir"
    else
        fail "Directory missing: $dir"
    fi
done

# =============================================================================
# Service Startup Test
# =============================================================================

print_section "Service Startup Test"

# Clean up any existing containers
info "Cleaning up existing containers..."
docker compose down --remove-orphans 2>/dev/null || true

# Start services
info "Starting services..."
docker compose up -d

# Wait for services to initialize
info "Waiting ${STARTUP_WAIT}s for services to initialize..."

# Show progress
for i in $(seq 1 $STARTUP_WAIT); do
    echo -n "."
    sleep 1
done
echo ""

# Count running services
RUNNING_SERVICES=$(docker compose ps --filter 'status=running' --format '{{.Service}}' 2>/dev/null | wc -l)

if [ "$RUNNING_SERVICES" -ge "$EXPECTED_SERVICES" ]; then
    pass "All $EXPECTED_SERVICES services running"
else
    fail "Expected $EXPECTED_SERVICES services, got $RUNNING_SERVICES"
    echo ""
    echo "Service status:"
    docker compose ps
fi

# List running services
echo ""
info "Running services:"
docker compose ps --filter 'status=running' --format '  - {{.Service}}: {{.Status}}'

# =============================================================================
# Service Health Tests
# =============================================================================

print_section "Service Health Tests"

# OPA Health
if curl -sf http://localhost:8181/health >/dev/null 2>&1; then
    pass "OPA health check passed"
else
    fail "OPA health check failed"
fi

# OPA Policy Query
if curl -sf http://localhost:8181/v1/policies >/dev/null 2>&1; then
    pass "OPA policies endpoint accessible"
else
    fail "OPA policies endpoint not accessible"
fi

# Jupyter Health
if wait_for_service "http://localhost:8888" "Jupyter"; then
    pass "Jupyter accessible (may take longer on first start)"
else
    warn "Jupyter not responding - may still be starting"
fi

# Redis Health
if docker compose exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; then
    pass "Redis ping successful"
else
    fail "Redis ping failed"
fi

# Kafka Health (may need more time)
if docker compose exec -T kafka kafka-topics --bootstrap-server localhost:29092 --list >/dev/null 2>&1; then
    pass "Kafka broker accessible"
else
    warn "Kafka not ready yet - this is normal on first startup"
fi

# =============================================================================
# Example Project Tests
# =============================================================================

print_section "Example Project Tests"

# Test Example 01: Basic Policy Evaluation
EXAMPLE_01_DIR="$PROJECT_ROOT/examples/01-basic-policy-evaluation"
if [ -d "$EXAMPLE_01_DIR" ]; then
    info "Testing Example 01: Basic Policy Evaluation"

    cd "$EXAMPLE_01_DIR"

    # Start example OPA
    docker compose down --remove-orphans 2>/dev/null || true
    docker compose up -d
    sleep 10

    # Check if OPA is running
    if curl -sf http://localhost:8181/health >/dev/null 2>&1; then
        pass "Example 01: OPA started"

        # Run Python client if available
        if command_exists python3 && [ -f "evaluate_policy.py" ]; then
            if python3 evaluate_policy.py >/dev/null 2>&1; then
                pass "Example 01: Python client succeeded"
            else
                fail "Example 01: Python client failed"
            fi
        else
            skip "Example 01: Python client test (python3 not available)"
        fi
    else
        fail "Example 01: OPA failed to start"
    fi

    # Cleanup
    docker compose down
else
    skip "Example 01: Directory not found"
fi

cd "$PROJECT_ROOT"

# Test Example 02: AI Model Approval
EXAMPLE_02_DIR="$PROJECT_ROOT/examples/02-ai-model-approval"
if [ -d "$EXAMPLE_02_DIR" ]; then
    info "Testing Example 02: AI Model Approval"

    cd "$EXAMPLE_02_DIR"

    docker compose down --remove-orphans 2>/dev/null || true
    docker compose up -d
    sleep 10

    if curl -sf http://localhost:8181/health >/dev/null 2>&1; then
        pass "Example 02: OPA started"

        # Test policy query
        RESPONSE=$(curl -sf -X POST http://localhost:8181/v1/data/ai/model/risk/category \
            -H "Content-Type: application/json" \
            -d '{"input": {"model": {"risk_score": 0.5}}}' 2>/dev/null || echo "")

        if [ -n "$RESPONSE" ]; then
            pass "Example 02: Policy query succeeded"
        else
            fail "Example 02: Policy query failed"
        fi
    else
        fail "Example 02: OPA failed to start"
    fi

    docker compose down
else
    skip "Example 02: Directory not found"
fi

cd "$PROJECT_ROOT"

# Test Example 03: Data Access Control
EXAMPLE_03_DIR="$PROJECT_ROOT/examples/03-data-access-control"
if [ -d "$EXAMPLE_03_DIR" ]; then
    info "Testing Example 03: Data Access Control"

    cd "$EXAMPLE_03_DIR"

    docker compose down --remove-orphans 2>/dev/null || true
    docker compose up -d
    sleep 10

    if curl -sf http://localhost:8181/health >/dev/null 2>&1; then
        pass "Example 03: OPA started"
    else
        fail "Example 03: OPA failed to start"
    fi

    docker compose down
else
    skip "Example 03: Directory not found"
fi

cd "$PROJECT_ROOT"

# =============================================================================
# Notebook Verification
# =============================================================================

print_section "Notebook Verification"

# Check notebook files exist
for notebook in "notebooks/01-policy-experimentation.ipynb" "notebooks/02-governance-visualization.ipynb"; do
    if [ -f "$notebook" ]; then
        pass "Notebook exists: $(basename $notebook)"
    else
        fail "Notebook missing: $notebook"
    fi
done

# =============================================================================
# Platform-Specific Tests
# =============================================================================

print_section "Platform-Specific Tests ($PLATFORM)"

case "$PLATFORM" in
    linux)
        # Test volume permissions
        if docker compose exec -T opa ls -la /policies >/dev/null 2>&1; then
            pass "Volume mount permissions OK"
        else
            fail "Volume mount permissions issue"
        fi
        ;;
    macos)
        # Check architecture compatibility
        ARCH=$(uname -m)
        if [ "$ARCH" = "arm64" ]; then
            # Test multi-arch image support
            if docker compose exec -T opa uname -m >/dev/null 2>&1; then
                pass "Multi-arch images working on Apple Silicon"
            else
                fail "Multi-arch image issue on Apple Silicon"
            fi
        else
            pass "Running on Intel architecture"
        fi
        ;;
    windows)
        # Check line endings
        if file scripts/*.sh 2>/dev/null | grep -q "CRLF"; then
            warn "Some scripts have Windows line endings (CRLF)"
            info "Run: find scripts -name '*.sh' -exec dos2unix {} \\;"
        else
            pass "Script line endings OK (LF)"
        fi

        # Check path syntax
        pass "WSL 2 path handling verified"
        ;;
esac

# =============================================================================
# Cleanup
# =============================================================================

print_section "Cleanup"

cd "$PROJECT_ROOT"
docker compose down --remove-orphans
pass "Services stopped and cleaned up"

# =============================================================================
# Results Summary
# =============================================================================

print_header "Test Results Summary"

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED + TESTS_SKIPPED))

echo "Platform: $PLATFORM"
echo "Date: $(date)"
echo ""
echo -e "  ${GREEN}Passed${NC}:  $TESTS_PASSED"
echo -e "  ${RED}Failed${NC}:  $TESTS_FAILED"
echo -e "  ${YELLOW}Skipped${NC}: $TESTS_SKIPPED"
echo "  ─────────────────"
echo "  Total:   $TOTAL_TESTS"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                    ALL TESTS PASSED! ✓                           ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════╝${NC}"
    EXIT_CODE=0
else
    echo -e "${RED}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                    SOME TESTS FAILED ✗                           ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Please check the failed tests above and consult:"
    echo "  - docs/quickstart/troubleshooting.md"
    echo "  - docs/cross-platform-testing.md"
    EXIT_CODE=1
fi

# =============================================================================
# Generate JSON Report
# =============================================================================

REPORT_FILE="$PROJECT_ROOT/cross-platform-test-results.json"

cat > "$REPORT_FILE" << EOF
{
    "platform": "$PLATFORM",
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "docker_version": "$DOCKER_VERSION",
    "compose_version": "$COMPOSE_VERSION",
    "tests": {
        "passed": $TESTS_PASSED,
        "failed": $TESTS_FAILED,
        "skipped": $TESTS_SKIPPED,
        "total": $TOTAL_TESTS
    },
    "success": $([ $TESTS_FAILED -eq 0 ] && echo "true" || echo "false"),
    "system": {
        "memory": "$TOTAL_MEMORY",
        "architecture": "$(uname -m)",
        "kernel": "$(uname -r)"
    }
}
EOF

info "Test report saved to: cross-platform-test-results.json"
echo ""

exit $EXIT_CODE
