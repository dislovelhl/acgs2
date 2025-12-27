# Task Completion Checklist

## Before Completing Any Task

### 1. Code Quality
- [ ] Type hints added for all new functions
- [ ] Docstrings with constitutional references
- [ ] Specific exceptions from `exceptions.py` used
- [ ] No hardcoded sensitive information

### 2. Testing
- [ ] Run: `cd enhanced_agent_bus && python3 -m pytest tests/ -v`
- [ ] All 229+ tests passing
- [ ] New functionality has test coverage
- [ ] Constitutional validation tests pass: `pytest -m constitutional`

### 3. Syntax Validation
- [ ] Run: `for f in enhanced_agent_bus/*.py; do python3 -m py_compile "$f"; done`
- [ ] No syntax errors

### 4. Constitutional Compliance
- [ ] Constitutional hash `cdd01ef066bc6cf2` included where required
- [ ] Message processing includes constitutional validation
- [ ] Policy checks implemented for sensitive operations

### 5. Documentation
- [ ] CLAUDE.md updated if commands changed
- [ ] PROJECT_INDEX.md updated if structure changed
- [ ] README.md updated if major features added

### 6. Git
- [ ] Changes committed with descriptive message
- [ ] Branch is up to date with main
