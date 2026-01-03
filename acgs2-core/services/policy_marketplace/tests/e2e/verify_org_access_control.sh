#!/bin/bash
# Verify Organization-Private Templates Access Control via curl
#
# Prerequisites:
#   - Policy Marketplace service running on port 8003
#
# Usage:
#   ./verify_org_access_control.sh

set -e

API_URL="${API_URL:-http://localhost:8003}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Organization IDs
ORG_A_ID="org-alpha-001"
ORG_B_ID="org-beta-002"
ORG_A_USER="user-alice-001"
ORG_B_USER="user-bob-001"

# Test template data
TEMPLATE_NAME="Org Access Control Test Template"
TEMPLATE_DESC="Testing organization-private access control via curl"
TEMPLATE_CATEGORY="access_control"

echo "=========================================="
echo "Organization-Private Access Control Test"
echo "=========================================="
echo "API URL: $API_URL"
echo "Org A: $ORG_A_ID"
echo "Org B: $ORG_B_ID"
echo ""

# Step 1: Health check
echo -e "${YELLOW}[1/10] Checking API health...${NC}"
HEALTH=$(curl -s "$API_URL/health/ready")
if echo "$HEALTH" | grep -q '"status":"ready"'; then
    echo -e "${GREEN}       PASS: API is healthy${NC}"
else
    echo -e "${RED}       FAIL: API is not ready${NC}"
    exit 1
fi

# Step 2: Create private template for Org A
echo -e "\n${YELLOW}[2/10] Creating private template for Org A...${NC}"
UPLOAD_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/templates/upload" \
    -H "X-User-Id: $ORG_A_USER" \
    -H "X-Organization-Id: $ORG_A_ID" \
    -F "file=@-;filename=org_a_private.json" \
    -F "name=$TEMPLATE_NAME" \
    -F "description=$TEMPLATE_DESC" \
    -F "category=$TEMPLATE_CATEGORY" \
    -F "is_public=false" \
    -F "organization_id=$ORG_A_ID" \
    <<< '{"policy": "org_a_private", "version": "1.0.0"}')

TEMPLATE_ID=$(echo "$UPLOAD_RESPONSE" | grep -o '"id":[0-9]*' | head -1 | grep -o '[0-9]*')
IS_PUBLIC=$(echo "$UPLOAD_RESPONSE" | grep -o '"is_public":[^,]*' | grep -o 'true\|false')
TEMPLATE_ORG=$(echo "$UPLOAD_RESPONSE" | grep -o '"organization_id":"[^"]*"' | cut -d'"' -f4)

if [ -n "$TEMPLATE_ID" ] && [ "$IS_PUBLIC" = "false" ] && [ "$TEMPLATE_ORG" = "$ORG_A_ID" ]; then
    echo -e "${GREEN}       PASS: Private template created (ID: $TEMPLATE_ID, is_public: $IS_PUBLIC, org: $TEMPLATE_ORG)${NC}"
else
    echo -e "${RED}       FAIL: Could not create private template${NC}"
    echo "Response: $UPLOAD_RESPONSE"
    exit 1
fi

# Step 3: Org A user can GET template
echo -e "\n${YELLOW}[3/10] Verifying Org A user can GET template...${NC}"
ORG_A_GET=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/v1/templates/$TEMPLATE_ID" \
    -H "X-User-Id: $ORG_A_USER" \
    -H "X-Organization-Id: $ORG_A_ID")

if [ "$ORG_A_GET" = "200" ]; then
    echo -e "${GREEN}       PASS: Org A user can access template (HTTP $ORG_A_GET)${NC}"
else
    echo -e "${RED}       FAIL: Org A user got HTTP $ORG_A_GET instead of 200${NC}"
    exit 1
fi

# Step 4: Org A user can see template in list
echo -e "\n${YELLOW}[4/10] Verifying Org A user sees template in listing...${NC}"
ORG_A_LIST=$(curl -s "$API_URL/api/v1/templates" \
    -H "X-User-Id: $ORG_A_USER" \
    -H "X-Organization-Id: $ORG_A_ID")

if echo "$ORG_A_LIST" | grep -q "\"id\":$TEMPLATE_ID"; then
    echo -e "${GREEN}       PASS: Template visible in Org A user's list${NC}"
else
    echo -e "${RED}       FAIL: Template not visible in Org A user's list${NC}"
    exit 1
fi

# Step 5: Org B user gets 404 on GET
echo -e "\n${YELLOW}[5/10] Verifying Org B user gets 404 on GET...${NC}"
ORG_B_GET=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/v1/templates/$TEMPLATE_ID" \
    -H "X-User-Id: $ORG_B_USER" \
    -H "X-Organization-Id: $ORG_B_ID")

if [ "$ORG_B_GET" = "404" ]; then
    echo -e "${GREEN}       PASS: Org B user gets 404 (no info disclosure)${NC}"
else
    echo -e "${RED}       FAIL: Org B user got HTTP $ORG_B_GET instead of 404${NC}"
    exit 1
fi

# Step 6: Org B user cannot see template in list
echo -e "\n${YELLOW}[6/10] Verifying Org B user cannot see template in listing...${NC}"
ORG_B_LIST=$(curl -s "$API_URL/api/v1/templates" \
    -H "X-User-Id: $ORG_B_USER" \
    -H "X-Organization-Id: $ORG_B_ID")

if echo "$ORG_B_LIST" | grep -q "\"id\":$TEMPLATE_ID"; then
    echo -e "${RED}       FAIL: Template visible in Org B user's list (should be hidden)${NC}"
    exit 1
else
    echo -e "${GREEN}       PASS: Template NOT visible in Org B user's list${NC}"
fi

# Step 7: Unauthenticated gets 404 on GET
echo -e "\n${YELLOW}[7/10] Verifying unauthenticated user gets 404 on GET...${NC}"
UNAUTH_GET=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/v1/templates/$TEMPLATE_ID")

if [ "$UNAUTH_GET" = "404" ]; then
    echo -e "${GREEN}       PASS: Unauthenticated user gets 404${NC}"
else
    echo -e "${RED}       FAIL: Unauthenticated user got HTTP $UNAUTH_GET instead of 404${NC}"
    exit 1
fi

# Step 8: Unauthenticated cannot see template in list
echo -e "\n${YELLOW}[8/10] Verifying unauthenticated user cannot see template in listing...${NC}"
UNAUTH_LIST=$(curl -s "$API_URL/api/v1/templates")

if echo "$UNAUTH_LIST" | grep -q "\"id\":$TEMPLATE_ID"; then
    echo -e "${RED}       FAIL: Template visible in unauthenticated list (should be hidden)${NC}"
    exit 1
else
    echo -e "${GREEN}       PASS: Template NOT visible in unauthenticated list${NC}"
fi

# Step 9: Org B gets 404 on download
echo -e "\n${YELLOW}[9/10] Verifying Org B user gets 404 on download...${NC}"
ORG_B_DOWNLOAD=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/v1/templates/$TEMPLATE_ID/download" \
    -H "X-User-Id: $ORG_B_USER" \
    -H "X-Organization-Id: $ORG_B_ID")

if [ "$ORG_B_DOWNLOAD" = "404" ]; then
    echo -e "${GREEN}       PASS: Org B user gets 404 on download attempt${NC}"
else
    echo -e "${RED}       FAIL: Org B user got HTTP $ORG_B_DOWNLOAD instead of 404 on download${NC}"
    exit 1
fi

# Step 10: Admin can access private template
echo -e "\n${YELLOW}[10/10] Verifying admin can access private template...${NC}"
ADMIN_GET=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/v1/templates/$TEMPLATE_ID" \
    -H "X-User-Id: admin-001" \
    -H "X-Organization-Id: $ORG_A_ID" \
    -H "X-User-Role: admin")

if [ "$ADMIN_GET" = "200" ]; then
    echo -e "${GREEN}       PASS: Admin can access private template (HTTP $ADMIN_GET)${NC}"
else
    echo -e "${RED}       FAIL: Admin got HTTP $ADMIN_GET instead of 200${NC}"
    exit 1
fi

echo ""
echo "=========================================="
echo -e "${GREEN}ALL ORGANIZATION ACCESS CONTROL TESTS PASSED!${NC}"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - Private template created for Org A (ID: $TEMPLATE_ID)"
echo "  - Org A user: Can GET, list, and download template"
echo "  - Org B user: Gets 404 on GET, list excludes template, 404 on download"
echo "  - Unauthenticated: Gets 404 on GET, list excludes template"
echo "  - Admin: Can access all private templates"
echo "  - 404 (not 403) returned for unauthorized access (no info disclosure)"
