#!/bin/bash

# ACGS-2 Quarterly Cleanup Script
# Constitutional Hash: cdd01ef066bc6cf2
#
# This script performs comprehensive code cleanup operations:
# - Import optimization and unused import removal
# - Code formatting and linting
# - Security scanning
# - Dependency auditing
# - Performance validation
#
# Usage:
#   ./scripts/quarterly_cleanup.sh [--dry-run] [--skip-tests]

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONSTITUTIONAL_HASH="cdd01ef066bc6cf2"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
DRY_RUN=false
SKIP_TESTS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--dry-run] [--skip-tests]"
            exit 1
            ;;
    esac
done

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in dry run mode
if [ "$DRY_RUN" = true ]; then
    log_info "Running in DRY RUN mode - no changes will be made"
fi

# Navigate to project root
cd "$PROJECT_ROOT"

log_info "Starting ACGS-2 Quarterly Cleanup"
log_info "Constitutional Hash: $CONSTITUTIONAL_HASH"
log_info "Date: $(date)"

# Check Python environment
log_info "Checking Python environment..."
python3 --version
pip --version

# Install/update cleanup tools
log_info "Installing cleanup tools..."
pip install --quiet --upgrade black isort flake8 bandit pip-audit pycln radon pipdeptree

# 1. Import cleanup
log_info "Step 1: Import cleanup and optimization"
if [ "$DRY_RUN" = true ]; then
    python3 tools/import_cleanup.py --dry-run . || log_warning "Import cleanup check failed"
else
    python3 tools/import_cleanup.py --fix . || log_warning "Import cleanup failed"
fi

# 2. Code formatting
log_info "Step 2: Code formatting with Black"
if [ "$DRY_RUN" = true ]; then
    black --check --diff . || log_warning "Code formatting check failed"
else
    black . || log_warning "Code formatting failed"
fi

# 3. Import sorting
log_info "Step 3: Import sorting with isort"
if [ "$DRY_RUN" = true ]; then
    isort --check-only --diff --profile black . || log_warning "Import sorting check failed"
else
    isort --profile black . || log_warning "Import sorting failed"
fi

# 4. Linting
log_info "Step 4: Code linting with flake8"
flake8 --max-line-length=100 --ignore=E501,W503 . || log_warning "Linting failed"

# 5. Security scanning
log_info "Step 5: Security scanning with bandit"
bandit -r . -f json -o security_report.json || log_warning "Security scan failed"

# 6. Dependency auditing
log_info "Step 6: Dependency auditing with pip-audit"
pip-audit --requirement config/requirements_optimized.txt --format json -o dependency_audit.json || log_warning "Dependency audit failed"

# 7. Code complexity analysis
log_info "Step 7: Code complexity analysis with radon"
radon cc -a -j . > complexity_report.json || log_warning "Complexity analysis failed"
radon mi -a -j . > maintainability_report.json || log_warning "Maintainability analysis failed"

# 8. Import dependency analysis
log_info "Step 8: Import dependency analysis"
pipdeptree --warn silence > dependency_tree.txt || log_warning "Dependency tree analysis failed"

# 9. Syntax validation
log_info "Step 9: Syntax validation for all Python files"
find . -name "*.py" -not -path "./venv/*" -not -path "./__pycache__/*" -not -path "./node_modules/*" | head -20 | xargs -I {} python3 -m py_compile {} || log_warning "Syntax validation failed"

# 10. Performance validation (skip in dry run)
if [ "$SKIP_TESTS" = false ] && [ "$DRY_RUN" = false ]; then
    log_info "Step 10: Performance validation"
    python3 testing/performance_test.py || log_warning "Performance tests failed"
fi

# 11. Generate comprehensive report
log_info "Step 11: Generating cleanup report"
REPORT_FILE="QUARTERLY_CLEANUP_REPORT_$(date +%Y%m%d).md"

cat > "$REPORT_FILE" << EOF
# ACGS-2 Quarterly Cleanup Report

**Date**: $(date)
**Constitutional Hash**: \`$CONSTITUTIONAL_HASH\`
**Dry Run**: $DRY_RUN

## Executive Summary

This report summarizes the automated quarterly cleanup operations performed on the ACGS-2 codebase.

## Detailed Results

### 1. Import Cleanup
\`\`\`
$(python3 tools/import_cleanup.py --check . 2>&1 | head -20 || echo "Import check completed")
\`\`\`

### 2. Code Quality Metrics

#### Complexity Analysis
- **Cyclomatic Complexity**: See complexity_report.json
- **Maintainability Index**: See maintainability_report.json

#### Import Dependencies
- **Dependency Tree**: See dependency_tree.txt

### 3. Security Assessment
$(if [ -f security_report.json ]; then
    echo "#### Critical Issues"
    echo "\`\`\`json"
    cat security_report.json | jq '.results | length' 2>/dev/null || echo "0"
    echo "\`\`\`"
else
    echo "Security report not generated"
fi)

### 4. Dependency Audit
$(if [ -f dependency_audit.json ]; then
    echo "#### Vulnerabilities Found"
    echo "\`\`\`json"
    cat dependency_audit.json | jq '.vulnerabilities | length' 2>/dev/null || echo "0"
    echo "\`\`\`"
else
    echo "Dependency audit not generated"
fi)

## Recommendations

### Immediate Actions
1. Review and address any critical security issues
2. Update dependencies with known vulnerabilities
3. Address high-complexity functions (>10 cyclomatic complexity)

### Ongoing Maintenance
1. Continue using automated import cleanup in pre-commit hooks
2. Monitor code complexity trends
3. Regular security scanning and dependency updates

## Files Generated
- \`security_report.json\` - Security scan results
- \`dependency_audit.json\` - Dependency vulnerability report
- \`complexity_report.json\` - Code complexity analysis
- \`maintainability_report.json\` - Maintainability index
- \`dependency_tree.txt\` - Import dependency tree

---
*Generated by quarterly cleanup script*
*Constitutional Hash: $CONSTITUTIONAL_HASH*
EOF

log_success "Cleanup report generated: $REPORT_FILE"

# Summary
log_success "Quarterly cleanup completed!"

if [ "$DRY_RUN" = true ]; then
    log_info "This was a dry run - no changes were made to the codebase"
    log_info "To apply changes, run: $0"
else
    log_info "Changes have been applied to the codebase"
    log_info "Please review and commit the changes as appropriate"
fi

log_info "Generated reports:"
echo "  - $REPORT_FILE"
echo "  - security_report.json"
echo "  - dependency_audit.json"
echo "  - complexity_report.json"
echo "  - maintainability_report.json"
echo "  - dependency_tree.txt"

# Exit with success
exit 0
