#!/bin/bash
# Script to verify implementation status of all specs
#
# This script scans .auto-claude/specs for implementation_plan.json files
# and reports their status.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SPECS_DIR=".auto-claude/specs"

echo -e "${BLUE}📋 Verifying All Specifications${NC}"
echo "=============================="

TOTAL_SPECS=0
COMPLETED_SPECS=0
PENDING_SPECS=0

# Find all implementation_plan.json files
while IFS= read -r plan_file; do
    TOTAL_SPECS=$((TOTAL_SPECS + 1))

    spec_name=$(basename "$(dirname "$plan_file")")
    status=$(grep -o '"planStatus": "[^"]*"' "$plan_file" | cut -d'"' -f4)

    if [ "$status" == "completed" ] || [ "$status" == "done" ]; then
        echo -e "${GREEN}[DONE]    ${NC} $spec_name"
        COMPLETED_SPECS=$((COMPLETED_SPECS + 1))
    else
        echo -e "${YELLOW}[PENDING] ${NC} $spec_name ($status)"
        PENDING_SPECS=$((PENDING_SPECS + 1))
    fi
done < <(find "$SPECS_DIR" -name "implementation_plan.json" | sort)

echo "=============================="
echo -e "${BLUE}Summary:${NC}"
echo "Total Specs:     $TOTAL_SPECS"
echo -e "Completed:      ${GREEN}$COMPLETED_SPECS${NC}"
echo -e "Pending/Active: ${YELLOW}$PENDING_SPECS${NC}"

if [ "$PENDING_SPECS" -eq 0 ]; then
    echo -e "\n${GREEN}🎉 All specifications are implemented!${NC}"
else
    echo -e "\n${YELLOW}⚠️  Some specifications are still pending.${NC}"
fi
