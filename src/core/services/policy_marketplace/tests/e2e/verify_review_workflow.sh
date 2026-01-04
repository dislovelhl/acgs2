#!/bin/bash
# ==============================================================================
# E2E Verification: Review Workflow (Submit, Approve, Verify Badge)
# ==============================================================================
# This script verifies the complete review workflow:
# 1. Upload template (DRAFT, is_verified=false)
# 2. Submit for review (PENDING_REVIEW)
# 3. Verify in review queue
# 4. Approve as admin (PUBLISHED, is_verified=true)
# 5. Verify is_verified=true in record
# 6. Verify verified badge displays (is_verified in listing)
# ==============================================================================

set -e

BASE_URL="${BASE_URL:-http://localhost:8003}"
API_URL="${BASE_URL}/api/v1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counter for tests
PASSED=0
FAILED=0

# Test helper functions
pass() {
    echo -e "${GREEN}PASS${NC}: $1"
    ((PASSED++))
}

fail() {
    echo -e "${RED}FAIL${NC}: $1"
    ((FAILED++))
}

info() {
    echo -e "${BLUE}INFO${NC}: $1"
}

header() {
    echo ""
    echo -e "${YELLOW}=== $1 ===${NC}"
}

# ==============================================================================
# Main Tests
# ==============================================================================

header "Review Workflow E2E Verification"
echo "Base URL: ${BASE_URL}"
echo ""

# Test 1: Health Check
header "Step 1: Health Check"
HEALTH=$(curl -s "${BASE_URL}/health/ready")
if echo "$HEALTH" | grep -q '"status":"ready"'; then
    pass "API is healthy"
else
    fail "API health check failed: $HEALTH"
    exit 1
fi

# Test 2: Upload Template (should be DRAFT, is_verified=false)
header "Step 2: Upload Template"
TEMPLATE_CONTENT='{"policy":{"name":"E2E Review Test","version":"1.0.0","rules":[]}}'
UPLOAD_RESPONSE=$(curl -s -X POST "${API_URL}/templates/upload" \
    -F "file=@-;filename=review_test.json;type=application/json" \
    -F "name=Review Workflow E2E Test" \
    -F "description=Testing the review workflow end-to-end" \
    -F "category=compliance" \
    <<< "$TEMPLATE_CONTENT")

TEMPLATE_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.id')
INITIAL_STATUS=$(echo "$UPLOAD_RESPONSE" | jq -r '.status')
INITIAL_VERIFIED=$(echo "$UPLOAD_RESPONSE" | jq -r '.is_verified')

if [ "$TEMPLATE_ID" != "null" ] && [ -n "$TEMPLATE_ID" ]; then
    pass "Template uploaded with ID: $TEMPLATE_ID"
else
    fail "Failed to upload template: $UPLOAD_RESPONSE"
    exit 1
fi

if [ "$INITIAL_STATUS" == "draft" ]; then
    pass "Initial status is 'draft'"
else
    fail "Expected status 'draft', got '$INITIAL_STATUS'"
fi

if [ "$INITIAL_VERIFIED" == "false" ]; then
    pass "Initial is_verified is false"
else
    fail "Expected is_verified=false, got '$INITIAL_VERIFIED'"
fi

# Test 3: Submit for Review
header "Step 3: Submit for Review"
SUBMIT_RESPONSE=$(curl -s -X POST "${API_URL}/reviews/submit/${TEMPLATE_ID}")
NEW_STATUS=$(echo "$SUBMIT_RESPONSE" | jq -r '.new_status')

if [ "$NEW_STATUS" == "pending_review" ]; then
    pass "Template submitted - status is 'pending_review'"
else
    fail "Expected status 'pending_review', got '$NEW_STATUS'"
    echo "Response: $SUBMIT_RESPONSE"
fi

# Test 4: Verify in Review Queue
header "Step 4: Verify Template in Review Queue"
QUEUE_RESPONSE=$(curl -s "${API_URL}/reviews/pending")
IN_QUEUE=$(echo "$QUEUE_RESPONSE" | jq -r ".items[] | select(.id == $TEMPLATE_ID) | .id")

if [ "$IN_QUEUE" == "$TEMPLATE_ID" ]; then
    pass "Template found in pending review queue"
else
    fail "Template not found in review queue"
    echo "Queue response: $QUEUE_RESPONSE"
fi

# Verify status in queue
QUEUE_STATUS=$(echo "$QUEUE_RESPONSE" | jq -r ".items[] | select(.id == $TEMPLATE_ID) | .status")
QUEUE_VERIFIED=$(echo "$QUEUE_RESPONSE" | jq -r ".items[] | select(.id == $TEMPLATE_ID) | .is_verified")

if [ "$QUEUE_STATUS" == "pending_review" ]; then
    pass "Queue item status is 'pending_review'"
else
    fail "Expected queue item status 'pending_review', got '$QUEUE_STATUS'"
fi

if [ "$QUEUE_VERIFIED" == "false" ]; then
    pass "Queue item is_verified is false (not verified yet)"
else
    fail "Expected is_verified=false in queue, got '$QUEUE_VERIFIED'"
fi

# Test 5: Approve Template as Admin
header "Step 5: Approve Template as Admin"
APPROVE_RESPONSE=$(curl -s -X POST "${API_URL}/reviews/${TEMPLATE_ID}/approve" \
    -H "Content-Type: application/json" \
    -d '{"feedback":"Approved via E2E test script"}')

APPROVE_ACTION=$(echo "$APPROVE_RESPONSE" | jq -r '.action')
APPROVE_STATUS=$(echo "$APPROVE_RESPONSE" | jq -r '.new_status')

if [ "$APPROVE_ACTION" == "approve" ]; then
    pass "Approval action recorded"
else
    fail "Expected action 'approve', got '$APPROVE_ACTION'"
fi

if [ "$APPROVE_STATUS" == "published" ]; then
    pass "Template status changed to 'published'"
else
    fail "Expected status 'published', got '$APPROVE_STATUS'"
fi

# Test 6: Verify is_verified=true in Database Record
header "Step 6: Verify is_verified=true in Template Record"
TEMPLATE_RESPONSE=$(curl -s "${API_URL}/templates/${TEMPLATE_ID}")
FINAL_STATUS=$(echo "$TEMPLATE_RESPONSE" | jq -r '.status')
FINAL_VERIFIED=$(echo "$TEMPLATE_RESPONSE" | jq -r '.is_verified')

if [ "$FINAL_VERIFIED" == "true" ]; then
    pass "is_verified is TRUE in template record"
else
    fail "Expected is_verified=true, got '$FINAL_VERIFIED'"
fi

if [ "$FINAL_STATUS" == "published" ]; then
    pass "Final status is 'published'"
else
    fail "Expected status 'published', got '$FINAL_STATUS'"
fi

# Test 7: Verify Badge Displays in UI (via listing endpoint)
header "Step 7: Verify Verified Badge in Listing"
LIST_RESPONSE=$(curl -s "${API_URL}/templates")
LIST_VERIFIED=$(echo "$LIST_RESPONSE" | jq -r ".items[] | select(.id == $TEMPLATE_ID) | .is_verified")

if [ "$LIST_VERIFIED" == "true" ]; then
    pass "Verified badge displays correctly (is_verified=true in listing)"
else
    fail "Expected is_verified=true in listing, got '$LIST_VERIFIED'"
fi

# Test 8: Verify Template Appears in Verified Filter
header "Step 8: Verify Template in is_verified=true Filter"
VERIFIED_RESPONSE=$(curl -s "${API_URL}/templates?is_verified=true")
IN_VERIFIED_LIST=$(echo "$VERIFIED_RESPONSE" | jq -r ".items[] | select(.id == $TEMPLATE_ID) | .id")

if [ "$IN_VERIFIED_LIST" == "$TEMPLATE_ID" ]; then
    pass "Template appears in verified filter results"
else
    fail "Template not found in verified filter"
fi

# Test 9: Template No Longer in Pending Queue
header "Step 9: Verify Template Removed from Pending Queue"
FINAL_QUEUE=$(curl -s "${API_URL}/reviews/pending")
STILL_IN_QUEUE=$(echo "$FINAL_QUEUE" | jq -r ".items[] | select(.id == $TEMPLATE_ID) | .id")

if [ -z "$STILL_IN_QUEUE" ] || [ "$STILL_IN_QUEUE" == "null" ]; then
    pass "Template removed from pending review queue"
else
    fail "Template still in pending queue after approval"
fi

# Test 10: Verify Review History
header "Step 10: Verify Review History"
HISTORY_RESPONSE=$(curl -s "${API_URL}/reviews/${TEMPLATE_ID}/history")
HISTORY_COUNT=$(echo "$HISTORY_RESPONSE" | jq 'length')

if [ "$HISTORY_COUNT" -ge 2 ]; then
    pass "Review history contains $HISTORY_COUNT entries (submit + approve)"
else
    fail "Expected at least 2 history entries, got $HISTORY_COUNT"
fi

# ==============================================================================
# Summary
# ==============================================================================

header "Test Summary"
TOTAL=$((PASSED + FAILED))
echo ""
echo "Passed: $PASSED/$TOTAL"
echo "Failed: $FAILED/$TOTAL"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}ALL REVIEW WORKFLOW TESTS PASSED!${NC}"
    echo ""
    echo "Verification Summary:"
    echo "  1. Template upload creates DRAFT with is_verified=false"
    echo "  2. Submit changes status to PENDING_REVIEW"
    echo "  3. Template appears in review queue"
    echo "  4. Approve sets status=PUBLISHED and is_verified=true"
    echo "  5. Verified badge displays correctly in listing"
    echo "  6. Template appears in verified filter"
    echo "  7. Template removed from pending queue"
    echo "  8. Review history tracks all actions"
    exit 0
else
    echo -e "${RED}SOME TESTS FAILED${NC}"
    exit 1
fi
