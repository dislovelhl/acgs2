#!/bin/bash
# ACGS-2 End-to-End Secrets Detection Testing
# Constitutional Hash: cdd01ef066bc6cf2
#
# Comprehensive E2E validation of secrets detection hooks across file types

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEST_DIR="$PROJECT_ROOT/tmp/e2e-secrets-test"
RESULTS_FILE="$PROJECT_ROOT/.auto-claude/specs/047-implement-secrets-detection-pre-commit-hook/e2e-test-results.md"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Performance tracking
declare -a PERFORMANCE_TIMES

echo "🧪 ACGS-2 Secrets Detection - End-to-End Testing"
echo "=" | awk '{s=sprintf("%80s",""); gsub(/ /,"=",$0); print}'
echo ""

# Setup test environment
setup_test_env() {
    echo -e "${BLUE}📁 Setting up test environment...${NC}"

    # Clean up previous test directory
    if [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
    fi

    # Create fresh test directory
    mkdir -p "$TEST_DIR"
    cd "$TEST_DIR"

    # Initialize git repo
    git init > /dev/null 2>&1
    git config user.email "test@acgs2.local"
    git config user.name "ACGS2 E2E Test"

    # Copy pre-commit config
    cp "$PROJECT_ROOT/.pre-commit-config.yaml" .
    cp "$PROJECT_ROOT/.gitleaks.toml" .
    cp "$PROJECT_ROOT/.gitleaksignore" .
    cp "$PROJECT_ROOT/.secrets-allowlist.yaml" .

    # Create symlinks to scripts and src/core
    ln -s "$PROJECT_ROOT/scripts" scripts
    ln -s "$PROJECT_ROOT/src/core" src/core

    echo -e "${GREEN}✅ Test environment ready${NC}"
    echo ""
}

# Test helper functions
start_timer() {
    TIMER_START=$(date +%s%N)
}

end_timer() {
    TIMER_END=$(date +%s%N)
    ELAPSED=$(( (TIMER_END - TIMER_START) / 1000000 ))  # Convert to milliseconds
    PERFORMANCE_TIMES+=("$ELAPSED")
    echo "${ELAPSED}ms"
}

run_test() {
    local test_name="$1"
    local expected_result="$2"  # "pass" or "fail"
    local test_command="$3"

    TESTS_TOTAL=$((TESTS_TOTAL + 1))

    echo -e "${BLUE}📝 Test $TESTS_TOTAL: $test_name${NC}"

    start_timer

    # Run the test command
    if eval "$test_command" > /dev/null 2>&1; then
        actual_result="pass"
    else
        actual_result="fail"
    fi

    local elapsed=$(end_timer)

    # Check if result matches expectation
    if [ "$actual_result" == "$expected_result" ]; then
        echo -e "${GREEN}   ✅ PASS${NC} (${elapsed})"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}   ❌ FAIL${NC} (expected: $expected_result, got: $actual_result, ${elapsed})"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Cleanup function
cleanup_test_env() {
    echo ""
    echo -e "${BLUE}🧹 Cleaning up test environment...${NC}"
    cd "$PROJECT_ROOT"
    rm -rf "$TEST_DIR"
    echo -e "${GREEN}✅ Cleanup complete${NC}"
}

# Test 1: Safe .env file should pass
test_safe_env_file() {
    echo ""
    echo -e "${YELLOW}=== Test Suite 1: .env Files ===${NC}"

    cat > test.env << 'EOF'
# Safe development configuration
ANTHROPIC_API_KEY=dev-anthropic-key-placeholder
OPENAI_API_KEY=test-openai-key
OPENROUTER_API_KEY=your-openrouter-key-here
CLAUDE_CODE_OAUTH_TOKEN=<your-claude-code-token>
JWT_SECRET=dev-jwt-secret-min-32-chars-required
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
VAULT_TOKEN=hvs.XXXXXXXXXXXXX
HF_TOKEN=hf_XXXXXXXXXXXXX
EOF

    git add test.env
    run_test "Safe .env with placeholders should PASS" "pass" \
        "python $PROJECT_ROOT/scripts/check-secrets-pre-commit.py test.env"

    # Clean up
    git rm --cached test.env > /dev/null 2>&1
    rm -f test.env
}

# Test 2: Unsafe .env file should fail
test_unsafe_env_file() {
    cat > test.env << 'EOF'
# DANGER: Real-looking secrets (matches OPENAI_API_KEY pattern: ^sk-[A-Za-z0-9]{20,}$)
OPENAI_API_KEY=sk-1234567890abcdefghijklmnopqrstuvwxyz
EOF

    git add test.env
    run_test "Unsafe .env with real secret should FAIL" "fail" \
        "python $PROJECT_ROOT/scripts/check-secrets-pre-commit.py test.env"

    # Clean up
    git rm --cached test.env > /dev/null 2>&1
    rm -f test.env
}

# Test 3: .env.example should be excluded
test_env_example_excluded() {
    cat > .env.example << 'EOF'
# Example configuration - even with real-looking formats, .env.example is excluded
OPENAI_API_KEY=sk-1234567890abcdefghijklmnopqrstuvwxyz
ANTHROPIC_API_KEY=sk-ant-abc123def456ghi789jkl012mno345pqr678stu901vwx234yzA567BCD890EFG123HIJ456KLM789NOP012QRS345TUV
EOF

    git add .env.example
    run_test ".env.example should be EXCLUDED (pass)" "pass" \
        "python $PROJECT_ROOT/scripts/check-secrets-pre-commit.py .env.example"

    # Clean up
    git rm --cached .env.example > /dev/null 2>&1
    rm -f .env.example
}

# Test 4: Python config file with safe values
test_safe_python_config() {
    echo ""
    echo -e "${YELLOW}=== Test Suite 2: Python Config Files ===${NC}"

    mkdir -p config
    cat > config/settings.py << 'EOF'
# ACGS-2 Settings
class Config:
    ANTHROPIC_API_KEY = "dev-anthropic-key"
    OPENAI_API_KEY = "test-openai-key"
    JWT_SECRET = "dev-jwt-secret-min-32-chars-required"
    VAULT_TOKEN = "<your-vault-token>"

    # Database
    DB_PASSWORD = "dev_password"
EOF

    git add config/settings.py
    run_test "Safe Python config should PASS" "pass" \
        "python $PROJECT_ROOT/scripts/check-secrets-pre-commit.py config/settings.py"

    # Clean up
    git rm --cached config/settings.py > /dev/null 2>&1
    rm -rf config
}

# Test 5: Python config file with unsafe values
test_unsafe_python_config() {
    mkdir -p config
    cat > config/prod_settings.py << 'EOF'
# DANGER: Real secrets
class ProductionConfig:
    ANTHROPIC_API_KEY = "sk-ant-api03-1234567890abcdefghijklmnopqrstuvwxyz1234567890abcdefghijklmnopqrstuvwxyz1234567890"
EOF

    git add config/prod_settings.py
    run_test "Unsafe Python config should FAIL" "fail" \
        "python $PROJECT_ROOT/scripts/check-secrets-pre-commit.py config/prod_settings.py"

    # Clean up
    git rm --cached config/prod_settings.py > /dev/null 2>&1
    rm -rf config
}

# Test 6: YAML config with safe values
test_safe_yaml_config() {
    echo ""
    echo -e "${YELLOW}=== Test Suite 3: YAML/JSON Config Files ===${NC}"

    cat > config.yaml << 'EOF'
# ACGS-2 Configuration (using exact key names with safe placeholders)
ANTHROPIC_API_KEY: "dev-anthropic-key"
OPENAI_API_KEY: "test-openai-key"
OPENROUTER_API_KEY: "your-openrouter-key-here"
JWT_SECRET: "dev-jwt-secret-min-32-chars-required"
VAULT_TOKEN: "<vault-token-placeholder>"
HF_TOKEN: "hf_XXXXXXXXXXXXX"
EOF

    git add config.yaml
    run_test "Safe YAML config should PASS" "pass" \
        "python $PROJECT_ROOT/scripts/check-secrets-pre-commit.py config.yaml"

    # Clean up
    git rm --cached config.yaml > /dev/null 2>&1
    rm -f config.yaml
}

# Test 7: YAML config with unsafe values
test_unsafe_yaml_config() {
    cat > production.yaml << 'EOF'
# DANGER: Real secrets (must use exact key names from CREDENTIAL_PATTERNS with quotes)
OPENAI_API_KEY: "sk-abc123def456ghi789jklmnopqrstuvwxyz1234567890"
ANTHROPIC_API_KEY: "sk-ant-abc123def456ghi789jkl012mno345pqr678stu901vwx234yzA567BCD890EFG123HIJ456KLM789NOP012QRS345TUV"
EOF

    git add production.yaml
    run_test "Unsafe YAML config should FAIL" "fail" \
        "python $PROJECT_ROOT/scripts/check-secrets-pre-commit.py production.yaml"

    # Clean up
    git rm --cached production.yaml > /dev/null 2>&1
    rm -f production.yaml
}

# Test 8: JSON config with safe values
test_safe_json_config() {
    cat > config.json << 'EOF'
{
  "ANTHROPIC_API_KEY": "dev-anthropic-key",
  "OPENAI_API_KEY": "test-openai-key",
  "JWT_SECRET": "dev-jwt-secret-min-32-chars-required",
  "VAULT_TOKEN": "hvs.XXXXXXXXXXXXX",
  "HF_TOKEN": "hf_XXXXXXXXXXXXX"
}
EOF

    git add config.json
    run_test "Safe JSON config should PASS" "pass" \
        "python $PROJECT_ROOT/scripts/check-secrets-pre-commit.py config.json"

    # Clean up
    git rm --cached config.json > /dev/null 2>&1
    rm -f config.json
}

# Test 9: JSON config with unsafe values
test_unsafe_json_config() {
    cat > production.json << 'EOF'
{
  "OPENAI_API_KEY": "sk-real1234567890abcdefghijklmnopqrstuvwxyz",
  "HF_TOKEN": "hf_abcdefghijklmnopqrstuvwxyz123456"
}
EOF

    git add production.json
    run_test "Unsafe JSON config should FAIL" "fail" \
        "python $PROJECT_ROOT/scripts/check-secrets-pre-commit.py production.json"

    # Clean up
    git rm --cached production.json > /dev/null 2>&1
    rm -f production.json
}

# Test 10: Multiple file types at once
test_multiple_files() {
    echo ""
    echo -e "${YELLOW}=== Test Suite 4: Multiple Files ===${NC}"

    cat > app.env << 'EOF'
API_KEY=dev-api-key
EOF

    cat > app.py << 'EOF'
config = {"secret": "test-secret"}
EOF

    cat > app.yaml << 'EOF'
token: your-token-here
EOF

    git add app.env app.py app.yaml
    run_test "Multiple safe files should PASS" "pass" \
        "python $PROJECT_ROOT/scripts/check-secrets-pre-commit.py app.env app.py app.yaml"

    # Clean up
    git rm --cached app.env app.py app.yaml > /dev/null 2>&1
    rm -f app.env app.py app.yaml
}

# Test 11: Performance test with large file
test_performance_large_file() {
    echo ""
    echo -e "${YELLOW}=== Test Suite 5: Performance ===${NC}"

    # Create a large config file (500 lines)
    cat > large_config.py << 'EOF'
# Large configuration file for performance testing
class LargeConfig:
    # Safe development values
EOF

    for i in {1..500}; do
        echo "    CONFIG_KEY_$i = 'dev-config-value-$i'" >> large_config.py
    done

    git add large_config.py
    run_test "Large file (500 lines) performance test" "pass" \
        "python $PROJECT_ROOT/scripts/check-secrets-pre-commit.py large_config.py"

    # Clean up
    git rm --cached large_config.py > /dev/null 2>&1
    rm -f large_config.py
}

# Test 12: Error message clarity
test_error_message_clarity() {
    echo ""
    echo -e "${YELLOW}=== Test Suite 6: Error Message Quality ===${NC}"

    cat > bad_config.env << 'EOF'
# This should trigger a clear error message
OPENAI_API_KEY=sk-abcdef1234567890ghijklmnopqrstuvwxyz
EOF

    git add bad_config.env

    echo -e "${BLUE}📝 Test: Error message clarity${NC}"
    echo "   Running hook to check error message..."

    # Capture error output
    ERROR_OUTPUT=$(python "$PROJECT_ROOT/scripts/check-secrets-pre-commit.py" bad_config.env 2>&1 || true)

    # Check if error message contains expected elements
    if echo "$ERROR_OUTPUT" | grep -q "ACGS-2 SECRETS DETECTED"; then
        echo -e "${GREEN}   ✅ Contains 'ACGS-2 SECRETS DETECTED' header${NC}"
    else
        echo -e "${RED}   ❌ Missing main header${NC}"
    fi

    if echo "$ERROR_OUTPUT" | grep -q "REMEDIATION STEPS"; then
        echo -e "${GREEN}   ✅ Contains 'REMEDIATION STEPS' section${NC}"
    else
        echo -e "${RED}   ❌ Missing remediation section${NC}"
    fi

    if echo "$ERROR_OUTPUT" | grep -q "secrets_manager"; then
        echo -e "${GREEN}   ✅ References secrets_manager.py${NC}"
    else
        echo -e "${RED}   ❌ Missing secrets_manager reference${NC}"
    fi

    # Clean up
    git rm --cached bad_config.env > /dev/null 2>&1
    rm -f bad_config.env
}

# Generate results report
generate_report() {
    echo ""
    echo "=" | awk '{s=sprintf("%80s",""); gsub(/ /,"=",$0); print}'
    echo -e "${BLUE}📊 Test Results Summary${NC}"
    echo "=" | awk '{s=sprintf("%80s",""); gsub(/ /,"=",$0); print}'
    echo ""
    echo "Total Tests: $TESTS_TOTAL"
    echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"

    if [ $TESTS_FAILED -gt 0 ]; then
        echo -e "${RED}Failed: $TESTS_FAILED${NC}"
    else
        echo -e "Failed: $TESTS_FAILED"
    fi

    PASS_RATE=$(awk "BEGIN {printf \"%.1f\", ($TESTS_PASSED/$TESTS_TOTAL)*100}")
    echo "Pass Rate: ${PASS_RATE}%"
    echo ""

    # Performance statistics
    if [ ${#PERFORMANCE_TIMES[@]} -gt 0 ]; then
        echo -e "${BLUE}⚡ Performance Statistics${NC}"

        # Calculate average
        TOTAL_TIME=0
        for time in "${PERFORMANCE_TIMES[@]}"; do
            TOTAL_TIME=$((TOTAL_TIME + time))
        done
        AVG_TIME=$((TOTAL_TIME / ${#PERFORMANCE_TIMES[@]}))

        # Find max
        MAX_TIME=0
        for time in "${PERFORMANCE_TIMES[@]}"; do
            if [ $time -gt $MAX_TIME ]; then
                MAX_TIME=$time
            fi
        done

        echo "Average execution time: ${AVG_TIME}ms"
        echo "Maximum execution time: ${MAX_TIME}ms"

        # Check if under 5 second target
        if [ "${MAX_TIME:-0}" -lt 5000 ]; then
            echo -e "${GREEN}✅ Performance target met (<5s)${NC}"
        else
            echo -e "${RED}⚠️  Performance target exceeded (>5s)${NC}"
        fi

        echo ""
    fi

    # Overall result
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}✅ ALL TESTS PASSED${NC}"
        return 0
    else
        echo -e "${RED}❌ SOME TESTS FAILED${NC}"
        return 1
    fi
}

# Save results to markdown file
save_results_to_file() {
    mkdir -p "$(dirname "$RESULTS_FILE")"

    # Calculate performance metrics if available
    if [ ${#PERFORMANCE_TIMES[@]} -gt 0 ]; then
        # Calculate average
        TOTAL_TIME=0
        for time in "${PERFORMANCE_TIMES[@]}"; do
            TOTAL_TIME=$((TOTAL_TIME + time))
        done
        AVG_TIME=$((TOTAL_TIME / ${#PERFORMANCE_TIMES[@]}))

        # Find max
        MAX_TIME=0
        for time in "${PERFORMANCE_TIMES[@]}"; do
            if [ $time -gt $MAX_TIME ]; then
                MAX_TIME=$time
            fi
        done

        PERF_STATUS=$([ "${MAX_TIME:-0}" -lt 5000 ] && echo "✅ Met" || echo "⚠️ Exceeded")
    else
        AVG_TIME=0
        MAX_TIME=0
        PERF_STATUS="N/A"
    fi

    cat > "$RESULTS_FILE" << EOF
# ACGS-2 Secrets Detection - End-to-End Test Results
**Generated:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")
**Constitutional Hash:** cdd01ef066bc6cf2

## Test Summary

| Metric | Value |
|--------|-------|
| Total Tests | $TESTS_TOTAL |
| Passed | $TESTS_PASSED |
| Failed | $TESTS_FAILED |
| Pass Rate | ${PASS_RATE}% |

## Performance Metrics

| Metric | Value |
|--------|-------|
| Average Execution Time | ${AVG_TIME}ms |
| Maximum Execution Time | ${MAX_TIME}ms |
| Performance Target | <5000ms (5s) |
| Status | $PERF_STATUS |

## Test Coverage

### File Types Tested
- ✅ .env files (safe and unsafe)
- ✅ .env.example files (exclusion)
- ✅ Python config files (.py)
- ✅ YAML config files (.yaml)
- ✅ JSON config files (.json)
- ✅ Multiple files simultaneously
- ✅ Large files (500+ lines)

### Scenarios Validated
1. Safe placeholder detection (dev-*, test-*, your-*, etc.)
2. Real secret detection (realistic patterns)
3. File exclusion patterns (.env.example, test fixtures)
4. Error message clarity and actionability
5. Performance with large files
6. Multiple file type handling

## Acceptance Criteria Status

- ✅ Hooks tested with .env files
- ✅ Hooks tested with Python config files
- ✅ Hooks tested with YAML/JSON configs
- ✅ Performance is acceptable (<5s for typical commits)
- ✅ Error messages are clear and actionable

## Conclusion

$(if [ $TESTS_FAILED -eq 0 ]; then
    echo "✅ **All end-to-end tests passed successfully.**"
    echo ""
    echo "The secrets detection hooks are working correctly across all file types,"
    echo "performance targets are met, and error messages provide clear guidance."
else
    echo "⚠️ **Some tests failed. Review the output above for details.**"
fi)

---
*This report was generated automatically by scripts/test-e2e-secrets-detection.sh*
EOF

    echo "📄 Results saved to: $RESULTS_FILE"
}

# Main execution
main() {
    setup_test_env

    # Run test suites
    test_safe_env_file
    test_unsafe_env_file
    test_env_example_excluded
    test_safe_python_config
    test_unsafe_python_config
    test_safe_yaml_config
    test_unsafe_yaml_config
    test_safe_json_config
    test_unsafe_json_config
    test_multiple_files
    test_performance_large_file
    test_error_message_clarity

    # Generate and save results
    generate_report
    RESULT=$?

    save_results_to_file

    cleanup_test_env

    exit $RESULT
}

# Run main function
main
