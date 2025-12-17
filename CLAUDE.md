# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ACGS-2** (Advanced Constitutional Governance System 2) is an enterprise platform implementing constitutional AI governance with formal verification, multi-agent coordination, and real-time performance optimization.

**Constitutional Hash**: `cdd01ef066bc6cf2` - Required for all operations. Include in all message processing and file headers.

## Build and Test Commands

### Enhanced Agent Bus (primary package)
```bash
# Navigate to package directory
cd enhanced_agent_bus

# Run all tests (229 tests)
python3 -m pytest tests/ -v --tb=short

# Run with coverage
python3 -m pytest tests/ --cov=. --cov-report=html

# Run a single test file
python3 -m pytest tests/test_core.py -v

# Run a specific test
python3 -m pytest tests/test_core.py::TestMessageProcessor::test_process_valid_message -v

# Run tests with Rust backend enabled
TEST_WITH_RUST=1 python3 -m pytest tests/ -v

# Run only constitutional validation tests
python3 -m pytest -m constitutional

# Verify Python syntax across all files
for f in *.py deliberation_layer/*.py tests/*.py; do python3 -m py_compile "$f"; done
```

### Performance and Integration Testing
```bash
# Performance tests
python testing/performance_test.py

# End-to-end tests
python testing/e2e_test.py

# Load tests
python testing/load_test.py
```

## Project Structure

- `enhanced_agent_bus/`: Core message bus (Python + optional Rust)
  - `core.py`: EnhancedAgentBus, MessageProcessor
  - `models.py`: AgentMessage, MessageType, Priority enums
  - `exceptions.py`: 22 custom exception types
  - `deliberation_layer/`: AI-powered review system
- `services/`: Microservices (Policy Registry, Audit, Search, etc.)
- `policies/`: OPA Rego policies
- `monitoring/`: Production monitoring
- `shared/`: Common utilities

## Code Style Guidelines

- **Naming**: Constitutional references in comments and docstrings.
- **Error Handling**: Use specific exceptions from `enhanced_agent_bus/exceptions.py`.
- **Async/Await**: Comprehensive async support throughout.
- **Type Hints**: Strict typing enforced.
- **Imports**: Absolute imports preferred; relative imports for fallbacks.

## Key Constants

- `CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"`
- `DEFAULT_REDIS_URL = "redis://localhost:6379"`
