# ACGS-2 Suggested Commands

## Testing (Primary)
```bash
# Run all tests (229 tests)
cd enhanced_agent_bus && python3 -m pytest tests/ -v --tb=short

# Run with coverage
python3 -m pytest tests/ --cov=. --cov-report=html

# Run specific test file
python3 -m pytest tests/test_core.py -v

# Run specific test
python3 -m pytest tests/test_core.py::TestMessageProcessor::test_process_valid_message -v

# Run constitutional validation tests only
python3 -m pytest -m constitutional

# Run with Rust backend
TEST_WITH_RUST=1 python3 -m pytest tests/ -v
```

## Syntax Validation
```bash
# Verify Python syntax across all files
for f in enhanced_agent_bus/*.py enhanced_agent_bus/deliberation_layer/*.py enhanced_agent_bus/tests/*.py; do python3 -m py_compile "$f"; done
```

## Performance & Integration
```bash
python testing/performance_test.py   # Performance tests
python testing/e2e_test.py           # End-to-end tests
python testing/load_test.py          # Load tests
```

## Docker
```bash
docker-compose up -d                 # Start all services
docker-compose logs -f               # View logs
docker-compose down                  # Stop services
```

## Git
```bash
git status                           # Check status
git add .                            # Stage changes
git commit -m "message"              # Commit
git push                             # Push to remote
```
