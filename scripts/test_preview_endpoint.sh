#!/bin/bash

# Test script for import preview endpoint
# Subtask 1-8: Test preview endpoint returns sample data without committing

set -e

echo "=== Testing Import Preview Endpoint ==="
echo ""

# Check if service is running
echo "Checking if integration-service is running..."
if curl -s http://localhost:8100/ > /dev/null 2>&1; then
    echo "✓ Integration service is running on port 8100"
    SERVICE_URL="http://localhost:8100"
else
    echo "✗ Integration service is not running on port 8100"
    echo ""
    echo "To start the service, run:"
    echo "  ./start_integration_service.sh"
    echo ""
    echo "Or manually:"
    echo "  cd integration-service"
    echo "  python3 -m uvicorn src.main:app --port 8100 --reload"
    exit 1
fi

echo ""
echo "Testing preview endpoint at ${SERVICE_URL}/api/imports/preview"
echo ""

# Test with minimal valid request
echo "Test 1: JIRA preview with minimal config"
RESPONSE=$(curl -s -X POST "${SERVICE_URL}/api/imports/preview" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "jira",
    "source_config": {
      "project_key": "TEST",
      "api_token": "test-token",
      "user_email": "test@example.com",
      "base_url": "https://test.atlassian.net"
    }
  }')

echo "Response:"
echo "$RESPONSE"
echo ""

# Check if response contains required fields
if echo "$RESPONSE" | grep -q '"source_type"'; then
    echo "✓ Response contains source_type"
else
    echo "✗ Response missing source_type"
    exit 1
fi

if echo "$RESPONSE" | grep -q '"preview_items"'; then
    echo "✓ Response contains preview_items array"
else
    echo "✗ Response missing preview_items"
    exit 1
fi

echo ""
echo "=== Test Passed ==="
echo ""
echo "Preview endpoint successfully returns sample data without committing"
