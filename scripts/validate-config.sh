#!/bin/bash
# ACGS-2 Configuration Validation Script
# Constitutional Hash: cdd01ef066bc6cf2
#
# Usage: ./scripts/validate-config.sh
#
# This script validates the centralized configuration system
# and helps diagnose common setup issues.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 ACGS-2 Configuration Validation"
echo "=================================="
echo ""

ERRORS=0
WARNINGS=0

# Function to log success
success() {
    echo -e "${GREEN}✅${NC} $1"
}

# Function to log warning
warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
    ((WARNINGS++))
}

# Function to log error
error() {
    echo -e "${RED}❌${NC} $1"
    ((ERRORS++))
}

# Check environment files
echo "📁 Checking environment files..."
for env_file in .env.dev .env.staging .env.production; do
    if [ -f "$env_file" ]; then
        success "Found $env_file"
    else
        error "Missing $env_file"
    fi
done
echo ""

# Check .env (local override)
if [ -f ".env" ]; then
    success "Local .env file exists"
else
    warning "No local .env file (run: cp .env.dev .env)"
fi
echo ""

# Validate constitutional hash
echo "🏛️ Validating constitutional hash..."
EXPECTED_HASH="cdd01ef066bc6cf2"
for env_file in .env.dev .env.staging .env.production; do
    if [ -f "$env_file" ]; then
        HASH=$(grep "^CONSTITUTIONAL_HASH=" "$env_file" 2>/dev/null | cut -d= -f2 || echo "")
        if [ "$HASH" = "$EXPECTED_HASH" ]; then
            success "$env_file: hash valid"
        elif [ -z "$HASH" ]; then
            error "$env_file: CONSTITUTIONAL_HASH not set"
        else
            error "$env_file: invalid hash '$HASH'"
        fi
    fi
done
echo ""

# Validate required variables
echo "🔧 Checking required variables..."
REQUIRED_VARS="ACGS_ENV REDIS_URL CONSTITUTIONAL_HASH"
for var in $REQUIRED_VARS; do
    if [ -f ".env.dev" ]; then
        if grep -q "^${var}=" ".env.dev"; then
            success "$var is defined"
        else
            error "$var is missing"
        fi
    fi
done
echo ""

# Check Python config
echo "🐍 Validating Python configuration..."
if command -v python3 &> /dev/null; then
    cd src/core 2>/dev/null || cd .
    if python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from shared.config import settings
    print(f'Environment: {settings.env}')
    print(f'Constitutional Hash: {settings.ai.constitutional_hash}')
    sys.exit(0)
except ImportError as e:
    print(f'Import error: {e}')
    sys.exit(1)
except Exception as e:
    print(f'Config error: {e}')
    sys.exit(1)
" 2>/dev/null; then
        success "Python config loads successfully"
    else
        warning "Python config could not be loaded (may need pydantic-settings)"
    fi
    cd - > /dev/null 2>&1 || true
else
    warning "Python not available for config validation"
fi
echo ""

# Check Docker Compose
echo "🐳 Validating Docker Compose..."
if command -v docker &> /dev/null; then
    if docker compose -f docker-compose.dev.yml config --quiet 2>/dev/null; then
        success "docker-compose.dev.yml is valid"
    else
        error "docker-compose.dev.yml has syntax errors"
    fi
else
    warning "Docker not available for compose validation"
fi
echo ""

# Check services (if running)
echo "🌐 Checking services..."
if command -v curl &> /dev/null; then
    # Check OPA
    if curl -s http://localhost:8181/health > /dev/null 2>&1; then
        success "OPA is running (port 8181)"
    else
        warning "OPA not accessible (start with: docker compose up -d opa)"
    fi

    # Check Redis
    if command -v redis-cli &> /dev/null; then
        if redis-cli -h localhost -p 6379 ping > /dev/null 2>&1; then
            success "Redis is running (port 6379)"
        else
            warning "Redis not accessible (start with: docker compose up -d redis)"
        fi
    fi

    # Check Agent Bus
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        success "Agent Bus is running (port 8000)"
    else
        warning "Agent Bus not accessible"
    fi
fi
echo ""

# Summary
echo "=================================="
echo "📊 Validation Summary"
echo "=================================="
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}All checks passed!${NC}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}$WARNINGS warning(s), no errors${NC}"
    echo "Configuration is functional with some optional improvements."
    exit 0
else
    echo -e "${RED}$ERRORS error(s), $WARNINGS warning(s)${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Run: cp .env.dev .env"
    echo "  2. Start services: docker compose -f docker-compose.dev.yml --env-file .env.dev up -d"
    echo "  3. See: docs/CONFIGURATION_TROUBLESHOOTING.md"
    exit 1
fi
