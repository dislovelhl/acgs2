#!/bin/bash
# Scan git branch for secrets before merging
#
# Usage:
#   ./scripts/scan-branch-secrets.sh [base-branch]
#
# Examples:
#   ./scripts/scan-branch-secrets.sh                    # Compare against origin/main
#   ./scripts/scan-branch-secrets.sh origin/develop     # Compare against origin/develop
#   ./scripts/scan-branch-secrets.sh main               # Compare against local main
#
# Exit codes:
#   0 - No secrets detected
#   1 - Secrets detected or error occurred

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASE_BRANCH=${1:-origin/main}
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🔍 ACGS-2 Branch Secrets Scanner${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}📌 Current Branch:${NC} $CURRENT_BRANCH"
echo -e "${BLUE}📊 Base Branch:${NC}    $BASE_BRANCH"
echo ""

# Check if gitleaks is installed
if ! command -v gitleaks &> /dev/null; then
    echo -e "${RED}❌ Error: gitleaks is not installed${NC}"
    echo ""
    echo "Install gitleaks:"
    echo "  macOS:   brew install gitleaks"
    echo "  Linux:   See https://github.com/gitleaks/gitleaks#installing"
    echo "  Windows: scoop install gitleaks"
    echo ""
    exit 1
fi

# Check if base branch exists
if ! git rev-parse --verify "$BASE_BRANCH" &> /dev/null; then
    echo -e "${RED}❌ Error: Base branch '$BASE_BRANCH' not found${NC}"
    echo ""
    echo "Available branches:"
    git branch -a | grep -E "^\s*(remotes/)?origin/(main|master|develop)" || true
    echo ""
    echo "Usage: $0 [base-branch]"
    echo "Example: $0 origin/develop"
    exit 1
fi

# Get commit range info
COMMIT_COUNT=$(git rev-list --count "$BASE_BRANCH..HEAD" 2>/dev/null || echo "0")

if [ "$COMMIT_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}⚠️  No commits found between $BASE_BRANCH and HEAD${NC}"
    echo ""
    echo "Possible reasons:"
    echo "  - Your branch is up to date with $BASE_BRANCH"
    echo "  - You're currently on $BASE_BRANCH"
    echo ""
    echo "Scanning current working directory instead..."
    echo ""

    # Scan working directory
    if gitleaks detect --source=. --verbose --redact --no-git 2>&1 | tee /tmp/gitleaks-scan.log; then
        echo ""
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}✅ No secrets detected!${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        exit 0
    else
        FINDING_COUNT=$(grep -c "Finding:" /tmp/gitleaks-scan.log 2>/dev/null || echo "0")
        echo ""
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${RED}❌ Secrets detected: $FINDING_COUNT finding(s)${NC}"
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "${YELLOW}🔧 Next steps:${NC}"
        echo "  1. Review the findings above (secrets are redacted for safety)"
        echo "  2. See docs/SECRETS_QUICK_FIX.md for remediation steps"
        echo "  3. Fix issues and run this script again"
        exit 1
    fi
fi

echo -e "${BLUE}📋 Commits to scan:${NC} $COMMIT_COUNT commit(s)"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🔎 Scanning commits...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Run gitleaks scan
if gitleaks detect --source=. --verbose --redact --log-opts="$BASE_BRANCH..HEAD" 2>&1 | tee /tmp/gitleaks-scan.log; then
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ Scan Complete: No secrets detected!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${GREEN}✅ Branch '$CURRENT_BRANCH' is safe to merge${NC}"
    echo ""
    echo "Summary:"
    echo "  • Commits scanned: $COMMIT_COUNT"
    echo "  • Secrets found: 0"
    echo "  • Status: PASS"
    echo ""
    exit 0
else
    # Count findings
    FINDING_COUNT=$(grep -c "Finding:" /tmp/gitleaks-scan.log 2>/dev/null || echo "0")

    echo ""
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}❌ Scan Complete: Secrets detected!${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Summary:"
    echo "  • Commits scanned: $COMMIT_COUNT"
    echo "  • Secrets found: $FINDING_COUNT"
    echo "  • Status: FAIL"
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}🔧 Remediation Steps:${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "1. Review the findings above (secrets are redacted for safety)"
    echo ""
    echo "2. Determine if findings are real secrets or false positives:"
    echo "   • Real secret: Rotate immediately, remove from code"
    echo "   • False positive: Add to allow-list or use safe placeholder"
    echo ""
    echo "3. Fix the issues:"
    echo "   • See docs/SECRETS_QUICK_FIX.md for detailed instructions"
    echo "   • Use secrets_manager.py for real secrets"
    echo "   • Use safe prefixes for placeholders (dev-, test-, etc.)"
    echo ""
    echo "4. Re-scan after fixes:"
    echo "   $0 $BASE_BRANCH"
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${RED}⚠️  DO NOT merge until secrets are resolved${NC}"
    echo ""

    exit 1
fi
