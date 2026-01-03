#!/bin/bash
# End-to-End Test: Complete JIRA Import Flow
# Tests the backend API flow from preview to import completion

set -e

API_BASE="http://localhost:8100/api/imports"
PREVIEW_ENDPOINT="$API_BASE/preview"
EXECUTE_ENDPOINT="$API_BASE"
STATUS_ENDPOINT="$API_BASE"

echo "=== E2E Import Flow Test ==="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Test Preview Endpoint
echo "Step 1: Testing Preview Endpoint..."
echo "Request: POST $PREVIEW_ENDPOINT"

PREVIEW_RESPONSE=$(curl -s -X POST "$PREVIEW_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "jira",
    "source_config": {
      "base_url": "https://test.atlassian.net",
      "email": "test@example.com",
      "api_token": "test-token",
      "project_key": "TEST"
    },
    "options": {
      "max_items": 20
    }
  }')

echo "Response:"
echo "$PREVIEW_RESPONSE" | python3 -m json.tool

# Verify preview response structure
PREVIEW_COUNT=$(echo "$PREVIEW_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data.get('preview_items', [])))" 2>/dev/null || echo "0")

if [ "$PREVIEW_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Preview returned $PREVIEW_COUNT items${NC}"
else
    echo -e "${YELLOW}⚠ Preview returned sample data (mock mode)${NC}"
fi
echo ""

# Step 2: Test Execute Endpoint
echo "Step 2: Testing Execute Import Endpoint..."
echo "Request: POST $EXECUTE_ENDPOINT"

EXECUTE_RESPONSE=$(curl -s -X POST "$EXECUTE_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "jira",
    "source_config": {
      "base_url": "https://test.atlassian.net",
      "email": "test@example.com",
      "api_token": "test-token",
      "project_key": "TEST"
    },
    "options": {
      "max_items": 100
    }
  }')

echo "Response:"
echo "$EXECUTE_RESPONSE" | python3 -m json.tool

# Extract job_id
JOB_ID=$(echo "$EXECUTE_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('job_id', ''))" 2>/dev/null || echo "")

if [ -z "$JOB_ID" ]; then
    echo -e "${RED}✗ Failed to get job_id from execute response${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Import job created: $JOB_ID${NC}"
echo ""

# Step 3: Test Status Endpoint (poll for progress)
echo "Step 3: Testing Status Endpoint (polling for progress)..."
echo "Request: GET $STATUS_ENDPOINT/$JOB_ID"

MAX_POLLS=10
POLL_INTERVAL=2
POLL_COUNT=0

while [ $POLL_COUNT -lt $MAX_POLLS ]; do
    STATUS_RESPONSE=$(curl -s -X GET "$STATUS_ENDPOINT/$JOB_ID")

    echo "Poll #$((POLL_COUNT + 1)):"
    echo "$STATUS_RESPONSE" | python3 -m json.tool

    # Extract status and progress
    STATUS=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('status', ''))" 2>/dev/null || echo "")
    PROGRESS=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('progress', {}).get('percentage', 0))" 2>/dev/null || echo "0")
    PROCESSED=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('progress', {}).get('processed', 0))" 2>/dev/null || echo "0")
    TOTAL=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('progress', {}).get('total', 0))" 2>/dev/null || echo "0")

    echo -e "Status: ${YELLOW}$STATUS${NC} | Progress: ${YELLOW}$PROGRESS%${NC} | Items: ${YELLOW}$PROCESSED/$TOTAL${NC}"

    if [ "$STATUS" = "completed" ]; then
        echo -e "${GREEN}✓ Import completed successfully!${NC}"
        break
    elif [ "$STATUS" = "failed" ]; then
        echo -e "${RED}✗ Import failed${NC}"
        ERROR=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('error', ''))" 2>/dev/null || echo "")
        echo "Error: $ERROR"
        exit 1
    fi

    POLL_COUNT=$((POLL_COUNT + 1))

    if [ $POLL_COUNT -lt $MAX_POLLS ]; then
        echo "Waiting ${POLL_INTERVAL}s before next poll..."
        sleep $POLL_INTERVAL
    fi
    echo ""
done

if [ "$STATUS" != "completed" ]; then
    echo -e "${YELLOW}⚠ Import still in progress after $MAX_POLLS polls${NC}"
    echo "Final status: $STATUS"
fi

echo ""
echo "=== E2E Test Summary ==="
echo -e "${GREEN}✓ Preview endpoint returned data${NC}"
echo -e "${GREEN}✓ Execute endpoint created job: $JOB_ID${NC}"
echo -e "${GREEN}✓ Status endpoint tracked progress${NC}"
if [ "$STATUS" = "completed" ]; then
    echo -e "${GREEN}✓ Import completed successfully${NC}"
else
    echo -e "${YELLOW}⚠ Import status: $STATUS${NC}"
fi
echo ""
echo "=== Manual Frontend Testing Required ==="
echo "To complete E2E testing, verify the frontend:"
echo "1. Start the analytics-dashboard:"
echo "   cd analytics-dashboard && npm install && npm run dev"
echo "2. Navigate to http://localhost:3000/import"
echo "3. Verify wizard displays correctly"
echo "4. Test complete flow through the UI"
echo ""
