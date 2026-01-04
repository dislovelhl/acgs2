# Enhanced Agent Bus - Testing Guide

**Constitutional Hash:** cdd01ef066bc6cf2

## Quick Start

### Fix Failing Tests (ORCH-001-B)

```bash
# Option 1: Use the cleanup script (RECOMMENDED)
cd /home/dislove/document/acgs2/acgs2-core/enhanced_agent_bus
chmod +x clean_and_test.sh
./clean_and_test.sh

# Option 2: Manual cleanup
find . -type f -name "*.pyc" -delete
find . -type d -name "__pycache__" -exec rm -rf {} +
rm -rf .pytest_cache tests/.pytest_cache
python3 -m pytest tests/test_constitutional_validation.py -v --cache-clear
```

### Run Specific Test Sets

```bash
# Run all constitutional validation tests
python3 -m pytest tests/test_constitutional_validation.py -v

# Run only MessageProcessor tests
python3 -m pytest tests/test_constitutional_validation.py::TestMessageProcessor -v

# Run only EnhancedAgentBus tests
python3 -m pytest tests/test_constitutional_validation.py::TestEnhancedAgentBus -v

# Run single test
python3 -m pytest tests/test_constitutional_validation.py::TestMessageProcessor::test_process_valid_message -v

# Run with debug output
python3 -m pytest tests/test_constitutional_validation_debug.py -v -s
```

### Verify Test Environment

```bash
# Check that imports and environment are correctly configured
python3 -m pytest tests/test_environment_check.py -v -s
```

## Test Organization

### Constitutional Validation Tests

**File:** `tests/test_constitutional_validation.py`

**Test Classes:**
- `TestConstitutionalHashValidation` - Hash validation utilities
- `TestValidationResult` - ValidationResult class tests
- `TestMessageContentValidation` - Content validation tests
- `TestAgentMessage` - Message model tests
- `TestMessageProcessor` - **Core message processing tests** (9 tests)
- `TestEnhancedAgentBus` - **Agent bus integration tests** (8 tests)
- `TestMessagePriorityAndTypes` - Priority and type handling

**Key Tests:**
1. `test_process_valid_message` - Validates message processing with correct hash
2. `test_process_invalid_hash_message` - Validates hash mismatch detection
3. `test_handler_registration` - Validates async handler execution
4. `test_sync_handler` - Validates sync handler execution
5. `test_processed_count` - Validates processing metrics

### Debug Tests

**File:** `tests/test_constitutional_validation_debug.py`

Same tests as above but with detailed debug output showing:
- Processor configuration
- Message state before/after processing
- Validation results
- Handler execution
- Exact error messages

### Environment Check Tests

**File:** `tests/test_environment_check.py`

Validates:
- Module imports are correctly patched by conftest.py
- Constitutional hash is correct (`cdd01ef066bc6cf2`)
- Rust backend is disabled (unless `TEST_WITH_RUST=1`)
- MessageProcessor can be instantiated
- Basic message processing works

## Test Fixtures (conftest.py)

### Common Fixtures

```python
@pytest.fixture
def constitutional_hash() -> str
    """Returns: 'cdd01ef066bc6cf2'"""

@pytest.fixture
def valid_message() -> AgentMessage
    """Returns: Valid message with correct hash"""

@pytest.fixture
def invalid_hash_message() -> AgentMessage
    """Returns: Message with hash='invalid_hash'"""

@pytest.fixture
def message_processor() -> MessageProcessor
    """Returns: Fresh MessageProcessor instance"""

@pytest.fixture
def agent_bus() -> EnhancedAgentBus
    """Returns: Fresh EnhancedAgentBus instance"""

@pytest.fixture
async def started_agent_bus(agent_bus) -> EnhancedAgentBus
    """Returns: Started agent bus (auto-stopped after test)"""
```

## Common Issues and Solutions

### Issue 1: Import Errors

**Symptom:** `ModuleNotFoundError: No module named 'models'`

**Solution:**
```bash
# Ensure you're in the correct directory
cd /home/dislove/document/acgs2/acgs2-core/enhanced_agent_bus

# Run from the package directory
python3 -m pytest tests/
```

### Issue 2: Stale Bytecode Cache

**Symptom:** Tests fail with unexpected behavior or old code

**Solution:**
```bash
# Clean all cached bytecode
find . -type f -name "*.pyc" -delete
find . -type d -name "__pycache__" -exec rm -rf {} +
rm -rf .pytest_cache
```

### Issue 3: Tests Pass Individually But Fail in Suite

**Symptom:** Individual tests pass but fail when run together

**Solution:**
```bash
# Check for fixture cleanup issues
python3 -m pytest tests/ -v --setup-show

# Run with explicit fixture scope
python3 -m pytest tests/ -v --setup-plan
```

### Issue 4: Constitutional Hash Mismatch

**Symptom:** Tests fail with "Invalid constitutional hash" errors

**Solution:**
```bash
# Verify hash is correct
python3 -c "from models import CONSTITUTIONAL_HASH; print(CONSTITUTIONAL_HASH)"

# Should output: cdd01ef066bc6cf2
```

## Test Markers

### Available Markers

```python
@pytest.mark.asyncio        # Async test (required for async functions)
@pytest.mark.slow           # Slow test (skip with `-m "not slow"`)
@pytest.mark.integration    # Integration test (may require services)
@pytest.mark.constitutional # Constitutional governance test
@pytest.mark.requires_rust  # Requires Rust backend
```

### Using Markers

```bash
# Run only async tests
python3 -m pytest -m asyncio

# Skip slow tests
python3 -m pytest -m "not slow"

# Run only constitutional tests
python3 -m pytest -m constitutional

# Run integration tests
python3 -m pytest -m integration
```

## Performance Testing

### Run with Coverage

```bash
# Generate coverage report
python3 -m pytest tests/ --cov=. --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Run with Profiling

```bash
# Profile test execution
python3 -m pytest tests/ --profile

# Profile with sorting
python3 -m pytest tests/ --profile-svg
```

## Debugging Tips

### Get Detailed Output

```bash
# Show print statements
python3 -m pytest tests/ -v -s

# Show local variables on failure
python3 -m pytest tests/ -v -l

# Show full traceback
python3 -m pytest tests/ -v --tb=long

# Enter debugger on failure
python3 -m pytest tests/ -v --pdb
```

### Check Test Discovery

```bash
# List all discovered tests
python3 -m pytest tests/ --collect-only

# Show test hierarchy
python3 -m pytest tests/ --collect-only -q
```

## Environment Variables

```bash
# Enable Rust backend for testing
TEST_WITH_RUST=1 python3 -m pytest tests/

# Disable Rust backend (default)
TEST_WITH_RUST=0 python3 -m pytest tests/

# Set custom Redis URL
REDIS_URL=redis://localhost:6379 python3 -m pytest tests/
```

## CI/CD Integration

### GitHub Actions

```yaml
- name: Run Enhanced Agent Bus Tests
  run: |
    cd enhanced_agent_bus
    find . -type f -name "*.pyc" -delete
    python3 -m pytest tests/ -v --tb=short
```

### GitLab CI

```yaml
test:enhanced_agent_bus:
  script:
    - cd enhanced_agent_bus
    - find . -type f -name "*.pyc" -delete
    - python3 -m pytest tests/ -v --tb=short
```

## Additional Resources

- **Full Analysis:** See `ORCH-001-B-ANALYSIS.md`
- **Architecture:** See `../docs/architecture/agent-bus.md`
- **API Docs:** See `../docs/api/message-processor.md`
- **CLAUDE.md:** See `../CLAUDE.md` for complete testing commands

---

**Last Updated:** 2025-01-25
**Constitutional Hash:** cdd01ef066bc6cf2
**Status:** Active ✓
