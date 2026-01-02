#!/bin/bash
# ACGS-2 New Developer Onboarding Test
# Constitutional Hash: cdd01ef066bc6cf2
#
# This script simulates the new developer experience to verify
# that documentation and setup process work correctly.

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "🧪 ACGS-2 New Developer Simulation Test"
echo "========================================"
echo ""

ERRORS=0
WARNINGS=0
TESTS=0

# Function to run a test
test_step() {
    name="$1"
    cmd="$2"
    TESTS=$((TESTS + 1))
    echo -e "${BLUE}[TEST $TESTS]${NC} $name..."
    if eval "$cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}  ✅ PASS${NC}"
        return 0
    else
        echo -e "${RED}  ❌ FAIL${NC}"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# Function for warning tests (non-critical)
test_optional() {
    name="$1"
    cmd="$2"
    TESTS=$((TESTS + 1))
    echo -e "${BLUE}[TEST $TESTS]${NC} $name..."
    if eval "$cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}  ✅ PASS${NC}"
        return 0
    else
        echo -e "${YELLOW}  ⚠️ WARN (optional)${NC}"
        WARNINGS=$((WARNINGS + 1))
        return 0
    fi
}

echo "📋 Phase 1: Documentation Verification"
echo "---------------------------------------"

test_step "README.md exists" "[ -f README.md ]" || true
test_step "DEVELOPMENT.md exists" "[ -f docs/DEVELOPMENT.md ]" || true
test_step "CONFIGURATION_TROUBLESHOOTING.md exists" "[ -f docs/CONFIGURATION_TROUBLESHOOTING.md ]" || true
test_step "Quick Start section in README" "grep -q 'Quick Start' README.md" || true
test_step "Configuration section in DEVELOPMENT.md" "grep -q 'Configuration System' docs/DEVELOPMENT.md" || true

echo ""
echo "📋 Phase 2: Environment File Verification"
echo "------------------------------------------"

test_step ".env.dev exists" "[ -f .env.dev ]" || true
test_step ".env.staging exists" "[ -f .env.staging ]" || true
test_step ".env.production exists" "[ -f .env.production ]" || true
test_step ".env.dev has ACGS_ENV" "grep -q '^ACGS_ENV=' .env.dev" || true
test_step ".env.dev has REDIS_URL" "grep -q '^REDIS_URL=' .env.dev" || true
test_step ".env.dev has CONSTITUTIONAL_HASH" "grep -q '^CONSTITUTIONAL_HASH=' .env.dev" || true
test_step "Constitutional hash is correct in .env.dev" "grep -q '^CONSTITUTIONAL_HASH=cdd01ef066bc6cf2' .env.dev" || true

echo ""
echo "📋 Phase 3: Quick Start Simulation"
echo "-----------------------------------"

# Simulate: cp .env.dev .env
test_step "Can copy .env.dev to .env" "cp .env.dev .env.test && rm .env.test" || true

# Check Docker Compose
test_step "docker-compose.dev.yml is valid" "docker compose -f docker-compose.dev.yml config --quiet" || true
test_step "docker-compose.dev.yml has env_file directive" "grep -q 'env_file' docker-compose.dev.yml" || true

echo ""
echo "📋 Phase 4: Python Configuration Test"
echo "--------------------------------------"

# Check Python config loads
ORIG_DIR=$(pwd)
cd acgs2-core 2>/dev/null || cd .
test_step "Python shared.config imports" "python3 -c 'import sys; sys.path.insert(0, \".\"); from shared.config import settings; print(settings.env)'" || true
test_step "Constitutional hash accessible via settings.ai" "python3 -c 'import sys; sys.path.insert(0, \".\"); from shared.config import settings; assert settings.ai.constitutional_hash == \"cdd01ef066bc6cf2\"'" || true
cd "$ORIG_DIR" > /dev/null 2>&1 || true

echo ""
echo "📋 Phase 5: Script Validation"
echo "-----------------------------"

test_step "validate-config.sh exists" "[ -f scripts/validate-config.sh ]" || true
test_step "validate-config.sh is executable" "[ -x scripts/validate-config.sh ]" || true
test_step "validate-config.sh runs successfully" "./scripts/validate-config.sh" || true

echo ""
echo "📋 Phase 6: CI/CD Validation"
echo "----------------------------"

test_step "CI workflow exists" "[ -f .github/workflows/acgs2-ci-cd.yml ]" || true
test_step "CI has config validation step" "grep -q 'Centralized config validation' .github/workflows/acgs2-ci-cd.yml" || true
test_step "CI validates constitutional hash" "grep -q 'cdd01ef066bc6cf2' .github/workflows/acgs2-ci-cd.yml" || true

echo ""
echo "📋 Phase 7: Service Connectivity (Optional)"
echo "--------------------------------------------"

test_optional "OPA health check" "curl -s --connect-timeout 2 http://localhost:8181/health" || true
test_optional "Redis ping" "redis-cli -h localhost -p 6379 ping" || true
test_optional "Agent Bus health" "curl -s --connect-timeout 2 http://localhost:8000/health" || true

echo ""
echo "========================================"
echo "📊 New Developer Simulation Results"
echo "========================================"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}🎉 All $TESTS tests passed!${NC}"
    echo ""
    echo "New developer onboarding experience is READY."
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}✅ $((TESTS - WARNINGS)) tests passed, $WARNINGS optional warnings${NC}"
    echo ""
    echo "New developer onboarding experience is READY."
    echo "(Optional services may not be running)"
    exit 0
else
    echo -e "${RED}❌ $ERRORS errors, $WARNINGS warnings out of $TESTS tests${NC}"
    echo ""
    echo "Please fix errors before proceeding."
    exit 1
fi
