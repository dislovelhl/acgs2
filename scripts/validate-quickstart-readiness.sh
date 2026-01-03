#!/usr/bin/env bash
#
# ACGS-2 Quickstart Readiness Validator
#
# This script performs automated self-validation to verify that all
# quickstart infrastructure is in place and ready for user testing.
#
# Usage: ./scripts/validate-quickstart-readiness.sh
#
# Exit codes:
#   0 - All checks passed, ready for user testing
#   1 - Some checks failed, issues need resolution
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

# Print functions
pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((PASS_COUNT++))
}

fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    ((FAIL_COUNT++))
}

warn() {
    echo -e "${YELLOW}⚠ WARN${NC}: $1"
    ((WARN_COUNT++))
}

info() {
    echo -e "  ℹ $1"
}

section() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  $1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Header
echo "=============================================================================="
echo "          ACGS-2 Quickstart Infrastructure Readiness Validator"
echo "=============================================================================="
echo ""
echo "This script validates that all quickstart components are in place"
echo "and ready for user testing. It does NOT perform actual user testing."
echo ""
echo "Run date: $(date -Iseconds)"
echo ""

# ============================================================================
# Section 1: Documentation
# ============================================================================
section "1. DOCUMENTATION VALIDATION"

# Quickstart guide
if [[ -f "docs/quickstart/README.md" ]]; then
    LINE_COUNT=$(wc -l < "docs/quickstart/README.md")
    if [[ $LINE_COUNT -ge 500 ]]; then
        pass "Quickstart guide exists (${LINE_COUNT} lines, target: ≥500)"
    else
        fail "Quickstart guide too short (${LINE_COUNT} lines, target: ≥500)"
    fi
else
    fail "Quickstart guide missing: docs/quickstart/README.md"
fi

# Troubleshooting guide
if [[ -f "docs/quickstart/troubleshooting.md" ]]; then
    LINE_COUNT=$(wc -l < "docs/quickstart/troubleshooting.md")
    pass "Troubleshooting guide exists (${LINE_COUNT} lines)"
else
    fail "Troubleshooting guide missing: docs/quickstart/troubleshooting.md"
fi

# Feedback mechanism
if [[ -f "docs/feedback.md" ]]; then
    pass "Feedback mechanism documentation exists"
else
    fail "Feedback documentation missing: docs/feedback.md"
fi

# Validation report template
if [[ -f "docs/validation_report.md" ]]; then
    pass "Validation report template exists"
else
    fail "Validation report missing: docs/validation_report.md"
fi

# Video scripts
VIDEO_SCRIPTS=$(find docs/quickstart/video-scripts -name "*.md" 2>/dev/null | wc -l)
if [[ $VIDEO_SCRIPTS -ge 3 ]]; then
    pass "Video scripts exist (${VIDEO_SCRIPTS} scripts)"
else
    warn "Video scripts incomplete (${VIDEO_SCRIPTS}/3 required)"
fi

# ============================================================================
# Section 2: Docker Infrastructure
# ============================================================================
section "2. DOCKER INFRASTRUCTURE"

# compose.yaml
if [[ -f "compose.yaml" ]]; then
    pass "Root compose.yaml exists"

    # Check for required services
    if grep -q "opa:" compose.yaml; then
        pass "OPA service defined in compose.yaml"
    else
        fail "OPA service missing from compose.yaml"
    fi

    if grep -q "jupyter:" compose.yaml; then
        pass "Jupyter service defined in compose.yaml"
    else
        fail "Jupyter service missing from compose.yaml"
    fi
else
    fail "Root compose.yaml missing"
fi

# .env file
if [[ -f ".env" ]]; then
    pass ".env file exists"

    if grep -q "JUPYTER_PORT" .env; then
        pass "JUPYTER_PORT defined in .env"
    else
        warn "JUPYTER_PORT not found in .env"
    fi

    if grep -q "OPA_PORT" .env || grep -q "OPA_URL" .env; then
        pass "OPA configuration defined in .env"
    else
        warn "OPA configuration not found in .env"
    fi
else
    warn ".env file missing (optional for defaults)"
fi

# .env.example
if [[ -f ".env.example" ]]; then
    pass ".env.example template exists"
else
    warn ".env.example template missing"
fi

# ============================================================================
# Section 3: Examples
# ============================================================================
section "3. EXAMPLE PROJECTS"

EXAMPLES_DIRS=(
    "examples/01-basic-policy-evaluation"
    "examples/02-ai-model-approval"
    "examples/03-data-access-control"
)

for example_dir in "${EXAMPLES_DIRS[@]}"; do
    example_name=$(basename "$example_dir")

    if [[ -d "$example_dir" ]]; then
        pass "Example directory exists: ${example_name}"

        # Check required files
        if [[ -f "$example_dir/README.md" ]]; then
            pass "  └─ README.md exists"
        else
            fail "  └─ README.md missing"
        fi

        if [[ -f "$example_dir/compose.yaml" ]]; then
            pass "  └─ compose.yaml exists"
        else
            fail "  └─ compose.yaml missing"
        fi

        if [[ -f "$example_dir/requirements.txt" ]]; then
            pass "  └─ requirements.txt exists"
        else
            fail "  └─ requirements.txt missing"
        fi

        # Check for policies
        POLICY_COUNT=$(find "$example_dir/policies" -name "*.rego" 2>/dev/null | wc -l)
        if [[ $POLICY_COUNT -ge 1 ]]; then
            pass "  └─ Rego policies exist (${POLICY_COUNT} files)"
        else
            fail "  └─ No Rego policies found"
        fi

        # Check for Python client
        PYTHON_COUNT=$(find "$example_dir" -maxdepth 1 -name "*.py" 2>/dev/null | wc -l)
        if [[ $PYTHON_COUNT -ge 1 ]]; then
            pass "  └─ Python scripts exist (${PYTHON_COUNT} files)"
        else
            fail "  └─ No Python scripts found"
        fi
    else
        fail "Example directory missing: ${example_name}"
    fi
done

# Examples index
if [[ -f "examples/README.md" ]]; then
    pass "Examples index (README.md) exists"
else
    fail "Examples index missing: examples/README.md"
fi

# ============================================================================
# Section 4: Jupyter Notebooks
# ============================================================================
section "4. JUPYTER NOTEBOOKS"

if [[ -d "notebooks" ]]; then
    pass "Notebooks directory exists"

    NOTEBOOK_COUNT=$(find notebooks -name "*.ipynb" 2>/dev/null | wc -l)
    if [[ $NOTEBOOK_COUNT -ge 2 ]]; then
        pass "Jupyter notebooks exist (${NOTEBOOK_COUNT} notebooks, target: ≥2)"
    else
        fail "Insufficient notebooks (${NOTEBOOK_COUNT}/2 required)"
    fi

    if [[ -f "notebooks/README.md" ]]; then
        pass "Notebooks README exists"
    else
        fail "Notebooks README missing"
    fi

    if [[ -f "notebooks/requirements.txt" ]]; then
        if grep -q "notebook>=7.0.0" notebooks/requirements.txt; then
            pass "Notebook 7.x dependency specified"
        else
            warn "notebook>=7.0.0 not found in requirements"
        fi
    else
        fail "Notebooks requirements.txt missing"
    fi
else
    fail "Notebooks directory missing"
fi

# ============================================================================
# Section 5: Root README
# ============================================================================
section "5. ROOT DOCUMENTATION"

if [[ -f "README.md" ]]; then
    if grep -qi "quickstart" README.md; then
        pass "Root README mentions quickstart"
    else
        warn "Root README does not mention quickstart"
    fi
else
    fail "Root README.md missing"
fi

# ============================================================================
# Section 6: Syntax Validation (without Docker)
# ============================================================================
section "6. SYNTAX VALIDATION"

# Check Python syntax
PYTHON_ERRORS=0
for py_file in $(find examples -name "*.py" 2>/dev/null); do
    if python3 -m py_compile "$py_file" 2>/dev/null; then
        pass "Python syntax OK: $(basename "$py_file")"
    else
        fail "Python syntax error: $py_file"
        ((PYTHON_ERRORS++))
    fi
done

if [[ $PYTHON_ERRORS -eq 0 ]]; then
    pass "All Python files have valid syntax"
fi

# Check YAML syntax (basic)
for yaml_file in compose.yaml examples/*/compose.yaml; do
    if [[ -f "$yaml_file" ]]; then
        if python3 -c "import yaml; yaml.safe_load(open('$yaml_file'))" 2>/dev/null; then
            pass "YAML syntax OK: $yaml_file"
        else
            fail "YAML syntax error: $yaml_file"
        fi
    fi
done

# ============================================================================
# Summary
# ============================================================================
section "VALIDATION SUMMARY"

echo ""
echo "Results:"
echo -e "  ${GREEN}Passed${NC}: ${PASS_COUNT}"
echo -e "  ${RED}Failed${NC}: ${FAIL_COUNT}"
echo -e "  ${YELLOW}Warnings${NC}: ${WARN_COUNT}"
echo ""

TOTAL=$((PASS_COUNT + FAIL_COUNT))
if [[ $TOTAL -gt 0 ]]; then
    PASS_RATE=$((PASS_COUNT * 100 / TOTAL))
    echo "Pass rate: ${PASS_RATE}%"
fi

echo ""

if [[ $FAIL_COUNT -eq 0 ]]; then
    echo -e "${GREEN}════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ✓ ALL INFRASTRUCTURE CHECKS PASSED${NC}"
    echo -e "${GREEN}  ✓ READY FOR USER TESTING${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Recruit 3+ test users (see docs/validation_report.md)"
    echo "  2. Run user testing sessions following the protocol"
    echo "  3. Record results in docs/validation_report.md"
    echo "  4. Calculate average time-to-completion (target: <30 min)"
    echo "  5. Calculate average satisfaction score (target: >4.0/5.0)"
    echo ""
    exit 0
else
    echo -e "${RED}════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}  ✗ INFRASTRUCTURE CHECK FAILED${NC}"
    echo -e "${RED}  ✗ RESOLVE ISSUES BEFORE USER TESTING${NC}"
    echo -e "${RED}════════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Fix the failed checks above, then re-run this script."
    echo ""
    exit 1
fi
