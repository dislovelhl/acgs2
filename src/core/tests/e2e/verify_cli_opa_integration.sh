#!/bin/bash
# E2E verification script for CLI-OPA integration
# Run this script after starting OPA server with:
#   docker run -d -p 8181:8181 openpolicyagent/opa run --server

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/../fixtures"
CLI_DIR="$SCRIPT_DIR/../../"

echo "=== CLI-OPA Integration E2E Verification ==="
echo ""

# Check OPA health
echo "1. Checking OPA server health..."
if curl -s http://localhost:8181/health | grep -q "{}"; then
    echo "   OK: OPA server is running"
else
    echo "   FAIL: OPA server not running"
    echo "   Start with: docker run -d -p 8181:8181 openpolicyagent/opa run --server"
    exit 1
fi
echo ""

# Test CLI help
echo "2. Testing CLI help..."
cd "$CLI_DIR"
if python -m cli.policy_cli --help | grep -q "validate"; then
    echo "   OK: CLI help displays correctly"
else
    echo "   FAIL: CLI help failed"
    exit 1
fi
echo ""

# Test health command
echo "3. Testing health command..."
if python -m cli.policy_cli health | grep -q "healthy"; then
    echo "   OK: Health command works"
else
    echo "   FAIL: Health command failed"
    exit 1
fi
echo ""

# Test validate valid policy
echo "4. Testing policy validation (valid policy)..."
if python -m cli.policy_cli validate "$FIXTURES_DIR/valid_policy.rego" | grep -q "valid"; then
    echo "   OK: Valid policy validated successfully"
else
    echo "   FAIL: Valid policy validation failed"
    exit 1
fi
echo ""

# Test validate invalid policy
echo "5. Testing policy validation (invalid policy)..."
if python -m cli.policy_cli validate "$FIXTURES_DIR/invalid_policy.rego" 2>&1 | grep -qi "error\|failed"; then
    echo "   OK: Invalid policy correctly rejected"
else
    echo "   FAIL: Invalid policy should have been rejected"
    exit 1
fi
echo ""

# Test policy evaluation with inline JSON
echo "6. Testing policy evaluation (inline JSON)..."
if python -m cli.policy_cli test "$FIXTURES_DIR/rbac_policy.rego" \
    --input '{"role": "admin", "action": "delete"}' \
    --path "data.test.rbac.allow" | grep -qi "true\|allowed"; then
    echo "   OK: Policy evaluation with inline JSON works"
else
    echo "   FAIL: Policy evaluation with inline JSON failed"
    exit 1
fi
echo ""

# Test policy evaluation with file input
echo "7. Testing policy evaluation (file input)..."
if python -m cli.policy_cli test "$FIXTURES_DIR/rbac_policy.rego" \
    --input "@$FIXTURES_DIR/rbac_input_admin.json" \
    --path "data.test.rbac.allow" | grep -qi "true\|allowed"; then
    echo "   OK: Policy evaluation with file input works"
else
    echo "   FAIL: Policy evaluation with file input failed"
    exit 1
fi
echo ""

# Test policy evaluation access denied
echo "8. Testing policy evaluation (access denied)..."
if python -m cli.policy_cli test "$FIXTURES_DIR/rbac_policy.rego" \
    --input '{"role": "viewer", "action": "write"}' \
    --path "data.test.rbac.allow" | grep -qi "false\|denied"; then
    echo "   OK: Access denial works correctly"
else
    echo "   FAIL: Access denial test failed"
    exit 1
fi
echo ""

echo "=== All E2E Tests Passed ==="
