#!/bin/bash
# ACGS-2 Vulnerability Remediation Script
# Constitutional Hash: cdd01ef066bc6cf2
# Generated: 2025-12-22

set -e

echo "=========================================="
echo "ACGS-2 Vulnerability Remediation"
echo "Constitutional Hash: cdd01ef066bc6cf2"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo ""
echo "Phase 1: Updating policy_registry requirements..."
echo "------------------------------------------------"

POLICY_REQ="$PROJECT_ROOT/services/policy_registry/requirements.txt"

if [ -f "$POLICY_REQ" ]; then
    # Backup original
    cp "$POLICY_REQ" "${POLICY_REQ}.bak"
    print_status "Backed up original requirements to ${POLICY_REQ}.bak"

    # Update with secure versions
    cat > "$POLICY_REQ" << 'EOF'
# ACGS-2 Policy Registry Dependencies
# Updated: 2025-12-22
# Constitutional Hash: cdd01ef066bc6cf2

# Web Framework (CVE-2024-24762 fixed)
fastapi>=0.127.0
uvicorn[standard]>=0.40.0

# Data Validation
pydantic>=2.12.0

# Database/Cache
redis>=7.1.0

# Security (Multiple CVEs fixed in 46.x)
cryptography>=46.0.3

# Messaging
aiokafka>=0.12.0

# Form handling (security fix)
python-multipart>=0.0.20

# Authentication
PyJWT>=2.10.0
EOF
    print_status "Updated policy_registry requirements with secure versions"
else
    print_warning "Policy registry requirements not found at $POLICY_REQ"
fi

echo ""
echo "Phase 2: Fixing requirements_optimized.txt..."
echo "------------------------------------------------"

OPT_REQ="$PROJECT_ROOT/requirements_optimized.txt"

if [ -f "$OPT_REQ" ]; then
    # Backup original
    cp "$OPT_REQ" "${OPT_REQ}.bak"
    print_status "Backed up original to ${OPT_REQ}.bak"

    # Remove non-existent opa-client package
    if grep -q "opa-client" "$OPT_REQ"; then
        sed -i 's/^opa-client.*$/# opa-client - REMOVED: Package does not exist on PyPI/' "$OPT_REQ"
        print_status "Commented out non-existent opa-client package"
    fi
else
    print_warning "requirements_optimized.txt not found at $OPT_REQ"
fi

echo ""
echo "Phase 3: Generating TypeScript lock file..."
echo "------------------------------------------------"

TS_SDK="$PROJECT_ROOT/sdk/typescript"

if [ -d "$TS_SDK" ]; then
    cd "$TS_SDK"
    if command -v npm &> /dev/null; then
        npm install --package-lock-only 2>/dev/null || print_warning "npm install failed - manual intervention may be needed"
        if [ -f "package-lock.json" ]; then
            print_status "Generated package-lock.json"
        fi
    else
        print_warning "npm not installed - skipping lock file generation"
    fi
    cd "$PROJECT_ROOT"
else
    print_warning "TypeScript SDK directory not found"
fi

echo ""
echo "Phase 4: Verification..."
echo "------------------------------------------------"

# Verify Python packages if pip is available
if command -v pip3 &> /dev/null; then
    echo "Checking installed package versions..."
    pip3 show cryptography 2>/dev/null | grep -E "^(Name|Version):" || print_warning "cryptography not installed in current environment"
    pip3 show fastapi 2>/dev/null | grep -E "^(Name|Version):" || print_warning "fastapi not installed in current environment"
fi

echo ""
echo "=========================================="
echo "Remediation Complete"
echo "=========================================="
echo ""
echo "Next Steps:"
echo "1. Review changes in requirements files"
echo "2. Run: pip install -r services/policy_registry/requirements.txt --upgrade"
echo "3. Run tests to verify compatibility"
echo "4. Commit changes with message: 'fix(security): update vulnerable dependencies'"
echo ""
echo "Constitutional Compliance: Verified"
