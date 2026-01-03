#!/bin/bash
# Quick test script for Redis job tracking verification

set -e

API_URL="http://localhost:8100"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "Redis Job Tracking Quick Test"
echo "========================================"
echo ""

# Check if service is running
echo "Checking if integration-service is running..."
if ! curl -s "${API_URL}/health" > /dev/null 2>&1; then
    echo -e "${RED}✗ Integration service is not running${NC}"
    echo "Please start it with:"
    echo "  cd integration-service"
    echo "  uvicorn src.main:app --reload --port 8100"
    exit 1
fi
echo -e "${GREEN}✓ Integration service is running${NC}"
echo ""

# Create an import job
echo "Creating import job..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_URL}/api/imports" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "jira",
    "source_config": {
      "base_url": "https://test.atlassian.net",
      "email": "test@example.com",
      "api_token": "test-token",
      "project_key": "TEST"
    },
    "options": {
      "batch_size": 100,
      "preview_limit": 10
    }
  }')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" != "202" ]; then
    echo -e "${RED}✗ Failed to create import job (HTTP $HTTP_CODE)${NC}"
    echo "Response: $BODY"
    exit 1
fi

JOB_ID=$(echo "$BODY" | grep -o '"job_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$JOB_ID" ]; then
    echo -e "${RED}✗ No job_id in response${NC}"
    echo "Response: $BODY"
    exit 1
fi

echo -e "${GREEN}✓ Import job created${NC}"
echo "  Job ID: $JOB_ID"
echo ""

# Retrieve job via API
echo "Retrieving job via API..."
API_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_URL}/api/imports/${JOB_ID}")
HTTP_CODE=$(echo "$API_RESPONSE" | tail -n1)
BODY=$(echo "$API_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" != "200" ]; then
    echo -e "${RED}✗ Failed to retrieve job (HTTP $HTTP_CODE)${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Job retrieved via API${NC}"
echo ""

# Display job data
echo "Job Data:"
echo "$BODY" | grep -o '"job_id":"[^"]*"' | sed 's/"job_id":"/  Job ID: /' | sed 's/"$//'
echo "$BODY" | grep -o '"status":"[^"]*"' | sed 's/"status":"/  Status: /' | sed 's/"$//'
echo "$BODY" | grep -o '"source_type":"[^"]*"' | sed 's/"source_type":"/  Source: /' | sed 's/"$//'
echo ""

# Instructions for manual Redis verification
echo "========================================"
echo "Manual Redis Verification Steps"
echo "========================================"
echo ""
echo "To verify the job is stored in Redis, run these commands:"
echo ""
echo -e "${YELLOW}1. Check if job exists in Redis:${NC}"
echo "   redis-cli GET \"import:job:${JOB_ID}\""
echo ""
echo -e "${YELLOW}2. Check TTL (should be ~86400 seconds = 24 hours):${NC}"
echo "   redis-cli TTL \"import:job:${JOB_ID}\""
echo ""
echo -e "${YELLOW}3. Expected Results:${NC}"
echo "   - GET command should return JSON with job data"
echo "   - TTL command should return a positive number > 0"
echo "   - TTL should be close to 86400 (24 hours)"
echo ""

# Try to check Redis if redis-cli is available
if command -v redis-cli &> /dev/null; then
    echo "Checking Redis automatically..."
    echo ""

    # Check if key exists
    REDIS_DATA=$(redis-cli GET "import:job:${JOB_ID}" 2>/dev/null || echo "")

    if [ -n "$REDIS_DATA" ]; then
        echo -e "${GREEN}✓ Job found in Redis${NC}"
        echo ""

        # Check TTL
        TTL=$(redis-cli TTL "import:job:${JOB_ID}" 2>/dev/null || echo "-2")

        if [ "$TTL" -gt "0" ]; then
            HOURS=$((TTL / 3600))
            echo -e "${GREEN}✓ TTL is set: ${TTL} seconds (~${HOURS} hours)${NC}"

            if [ "$TTL" -le "86400" ]; then
                echo -e "${GREEN}✓ TTL is within expected range (≤24 hours)${NC}"
            else
                echo -e "${YELLOW}⚠ TTL is longer than expected${NC}"
            fi
        elif [ "$TTL" = "-1" ]; then
            echo -e "${RED}✗ TTL not set (key will never expire)${NC}"
        else
            echo -e "${RED}✗ Key does not exist or TTL check failed${NC}"
        fi
    else
        echo -e "${RED}✗ Job not found in Redis${NC}"
        echo "This could mean:"
        echo "  - Redis is not running"
        echo "  - Redis integration is not working"
        echo "  - Job was not saved to Redis"
    fi
else
    echo -e "${YELLOW}redis-cli not found - skipping automatic Redis check${NC}"
    echo "Install redis-cli or use the manual commands above"
fi

echo ""
echo "========================================"
echo "Test Complete"
echo "========================================"
echo ""
echo "For detailed verification instructions, see:"
echo "  integration-service/REDIS_VERIFICATION.md"
echo ""
