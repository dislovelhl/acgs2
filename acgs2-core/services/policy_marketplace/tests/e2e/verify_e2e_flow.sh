#!/bin/bash
# E2E Verification Script: Template Upload to Download Flow
#
# This script manually verifies the complete template upload to download workflow.
#
# Prerequisites:
#   1. Backend service running on port 8003
#   2. Frontend running on port 5173 (optional for UI verification)
#
# Usage:
#   ./verify_e2e_flow.sh [BASE_URL]
#   Default BASE_URL: http://localhost:8003

set -e

BASE_URL="${1:-http://localhost:8003}"
API_URL="$BASE_URL/api/v1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================================"
echo "E2E Verification: Template Upload to Download Flow"
echo "============================================================"
echo "API URL: $API_URL"
echo ""

# Function to check status code
check_status() {
    local expected=$1
    local actual=$2
    local step=$3

    if [ "$actual" -eq "$expected" ]; then
        echo -e "${GREEN}[PASS]${NC} $step (HTTP $actual)"
        return 0
    else
        echo -e "${RED}[FAIL]${NC} $step (expected HTTP $expected, got HTTP $actual)"
        return 1
    fi
}

# Step 1: Health Check
echo ""
echo "[Step 1/7] Checking API health..."
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health/ready")
check_status 200 "$HEALTH_STATUS" "Health check"

# Step 2: Get Initial Template Count
echo ""
echo "[Step 2/7] Getting initial template list..."
INITIAL_RESPONSE=$(curl -s "$API_URL/templates")
INITIAL_COUNT=$(echo "$INITIAL_RESPONSE" | grep -o '"total_items":[0-9]*' | cut -d':' -f2)
echo "         Initial template count: $INITIAL_COUNT"

# Step 3: Upload Template
echo ""
echo "[Step 3/7] Uploading test template..."

# Create temporary test file
TEST_FILE=$(mktemp)
cat > "$TEST_FILE" << 'EOF'
{
  "policy": {
    "name": "E2E Verification Test",
    "version": "1.0.0",
    "rules": [
      {
        "id": "rule-001",
        "action": "allow",
        "condition": {"subject": "admin", "resource": "*"}
      }
    ]
  }
}
EOF

UPLOAD_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_URL/templates/upload" \
    -F "file=@$TEST_FILE;filename=e2e_test.json" \
    -F "name=E2E Verification Template" \
    -F "description=Template created for E2E verification testing" \
    -F "category=compliance")

UPLOAD_STATUS=$(echo "$UPLOAD_RESPONSE" | tail -1)
UPLOAD_BODY=$(echo "$UPLOAD_RESPONSE" | sed '$d')

check_status 201 "$UPLOAD_STATUS" "Upload template"

# Extract template ID
TEMPLATE_ID=$(echo "$UPLOAD_BODY" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
echo "         Template uploaded with ID: $TEMPLATE_ID"

# Clean up temp file
rm -f "$TEST_FILE"

# Step 4: Verify in Listing
echo ""
echo "[Step 4/7] Verifying template appears in listing..."
LIST_RESPONSE=$(curl -s "$API_URL/templates")
NEW_COUNT=$(echo "$LIST_RESPONSE" | grep -o '"total_items":[0-9]*' | cut -d':' -f2)

if [ "$NEW_COUNT" -gt "$INITIAL_COUNT" ]; then
    echo -e "${GREEN}[PASS]${NC} Template count increased ($INITIAL_COUNT -> $NEW_COUNT)"
else
    echo -e "${RED}[FAIL]${NC} Template count did not increase"
    exit 1
fi

# Check if template ID is in listing
if echo "$LIST_RESPONSE" | grep -q "\"id\":$TEMPLATE_ID"; then
    echo -e "${GREEN}[PASS]${NC} Template found in listing"
else
    echo -e "${RED}[FAIL]${NC} Template not found in listing"
    exit 1
fi

# Step 5: Download Template
echo ""
echo "[Step 5/7] Downloading template..."
DOWNLOAD_RESPONSE=$(curl -s -w "\n%{http_code}" "$API_URL/templates/$TEMPLATE_ID/download")
DOWNLOAD_STATUS=$(echo "$DOWNLOAD_RESPONSE" | tail -1)
DOWNLOAD_BODY=$(echo "$DOWNLOAD_RESPONSE" | sed '$d')

check_status 200 "$DOWNLOAD_STATUS" "Download template"

# Verify content contains our policy
if echo "$DOWNLOAD_BODY" | grep -q "E2E Verification Test"; then
    echo -e "${GREEN}[PASS]${NC} Downloaded content matches uploaded content"
else
    echo -e "${RED}[FAIL]${NC} Content mismatch in download"
    exit 1
fi

# Step 6: Verify Download Count
echo ""
echo "[Step 6/7] Verifying download count incremented..."
DOWNLOAD_COUNT=$(echo "$DOWNLOAD_BODY" | grep -o '"downloads":[0-9]*' | cut -d':' -f2)

if [ "$DOWNLOAD_COUNT" -eq 1 ]; then
    echo -e "${GREEN}[PASS]${NC} Download count is 1"
else
    echo -e "${RED}[FAIL]${NC} Download count not incremented (expected 1, got $DOWNLOAD_COUNT)"
    exit 1
fi

# Step 7: Verify Count Persisted
echo ""
echo "[Step 7/7] Verifying count persisted in template record..."
GET_RESPONSE=$(curl -s "$API_URL/templates/$TEMPLATE_ID")
PERSISTED_COUNT=$(echo "$GET_RESPONSE" | grep -o '"downloads":[0-9]*' | cut -d':' -f2)

if [ "$PERSISTED_COUNT" -eq 1 ]; then
    echo -e "${GREEN}[PASS]${NC} Download count persisted correctly"
else
    echo -e "${RED}[FAIL]${NC} Download count not persisted (expected 1, got $PERSISTED_COUNT)"
    exit 1
fi

echo ""
echo "============================================================"
echo -e "${GREEN}ALL E2E VERIFICATION TESTS PASSED!${NC}"
echo "============================================================"
echo ""
echo "Summary:"
echo "  - API Health: OK"
echo "  - Template Upload: OK (ID: $TEMPLATE_ID)"
echo "  - Template Listing: OK"
echo "  - Template Download: OK"
echo "  - Download Counter: OK"
echo ""
echo "To verify via UI:"
echo "  1. Open http://localhost:5173 in browser"
echo "  2. Navigate to template listing"
echo "  3. Find 'E2E Verification Template'"
echo "  4. Click to view details"
echo "  5. Click download button"
echo "  6. Refresh page and verify download count increased"
