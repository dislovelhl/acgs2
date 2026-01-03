#!/bin/bash
# ACGS-2 Quality Gate Script
# Runs automated code quality checks and enforces standards

set -e

echo "🔍 ACGS-2 Quality Gate - Starting Code Quality Analysis"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ACGS2_CORE="$PROJECT_ROOT/acgs2-core"

echo "📁 Project Root: $PROJECT_ROOT"
echo "📁 Core Module: $ACGS2_CORE"
echo

# Check if ruff is installed
if ! command -v ruff &> /dev/null; then
    echo -e "${RED}❌ ruff not found. Install with: pipx install ruff${NC}"
    exit 1
fi

# Check if mypy is available
if ! command -v mypy &> /dev/null; then
    echo -e "${YELLOW}⚠️  mypy not found. Type checking will be skipped.${NC}"
    SKIP_MYPY=true
fi

echo "🔧 Running Critical Quality Checks..."
echo "-----------------------------------"

cd "$ACGS2_CORE"

# Check for syntax errors (most critical) - only check our source directories
echo "Checking syntax errors..."
SYNTAX_ERRORS=$(ruff check enhanced_agent_bus services --select E9,F --output-format=concise 2>/dev/null | wc -l)
if [ "$SYNTAX_ERRORS" -gt 0 ]; then
    echo -e "${RED}❌ Found $SYNTAX_ERRORS syntax errors in core modules${NC}"
    CRITICAL_COUNT=$SYNTAX_ERRORS
else
    echo -e "${GREEN}✅ No syntax errors found in core modules${NC}"
    CRITICAL_COUNT=0
fi

# Check for undefined names in core modules
echo "Checking for undefined names..."
UNDEFINED_NAMES=$(ruff check enhanced_agent_bus services --select F821 --output-format=concise 2>/dev/null | wc -l)
if [ "$UNDEFINED_NAMES" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Found $UNDEFINED_NAMES undefined name references${NC}"
fi

echo
echo "🔍 Checking for Bare Except Clauses..."
echo "------------------------------------"

BARE_EXCEPT_COUNT=$(grep -r "except:" --include="*.py" enhanced_agent_bus services | grep -v "# " | wc -l)
if [ "$BARE_EXCEPT_COUNT" -gt 0 ]; then
    echo -e "${RED}❌ Found $BARE_EXCEPT_COUNT bare except clauses in core modules${NC}"
else
    echo -e "${GREEN}✅ No bare except clauses found in core modules${NC}"
fi

echo
echo "📝 Checking for Print Statements in Production Code..."
echo "---------------------------------------------------"

PRINT_COUNT=$(find enhanced_agent_bus services -name "*.py" -not -path "*/tests/*" -not -path "*/test_*" -not -name "*test.py" | xargs grep -l "print(" 2>/dev/null | wc -l)
if [ "$PRINT_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Found $PRINT_COUNT print statements in production code${NC}"
    echo "   (Should use logging instead)"
else
    echo -e "${GREEN}✅ No print statements in production code${NC}"
fi

echo
echo "📊 Code Quality Summary"
echo "======================"

# Get basic stats for core modules only
TOTAL_FILES=$(find enhanced_agent_bus services -name "*.py" | wc -l)
TOTAL_LINES=$(find enhanced_agent_bus services -name "*.py" -exec wc -l {} \; | awk '{sum += $1} END {print sum}')

echo "📄 Python Files: $TOTAL_FILES"
echo "📏 Total Lines: $TOTAL_LINES"

# Calculate quality score (simplified)
QUALITY_SCORE=100

if [ "$CRITICAL_COUNT" -gt 0 ]; then
    QUALITY_SCORE=$((QUALITY_SCORE - CRITICAL_COUNT * 5))
fi

if [ "$BARE_EXCEPT_COUNT" -gt 0 ]; then
    QUALITY_SCORE=$((QUALITY_SCORE - BARE_EXCEPT_COUNT * 10))
fi

if [ "$PRINT_COUNT" -gt 0 ]; then
    QUALITY_SCORE=$((QUALITY_SCORE - PRINT_COUNT * 2))
fi

# Cap at 0
if [ "$QUALITY_SCORE" -lt 0 ]; then
    QUALITY_SCORE=0
fi

echo "🎯 Quality Score: $QUALITY_SCORE/100"

if [ "$QUALITY_SCORE" -ge 90 ]; then
    echo -e "${GREEN}✅ Quality Gate: PASSED${NC}"
    exit 0
elif [ "$QUALITY_SCORE" -ge 70 ]; then
    echo -e "${YELLOW}⚠️  Quality Gate: WARNING (Address issues for better quality)${NC}"
    exit 0
else
    echo -e "${RED}❌ Quality Gate: FAILED (Fix critical issues before proceeding)${NC}"
    exit 1
fi
