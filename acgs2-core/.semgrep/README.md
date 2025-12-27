# ACGS-2 Semgrep Rules

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

This directory contains Semgrep rule files for code governance and security scanning in the ACGS-2 project.

## Rule Files

### 1. constitutional-compliance.yaml (10 rules)
Enforces constitutional AI governance compliance:
- Constitutional hash validation in docstrings and messages
- Hardcoded credentials detection
- Database access validation requirements
- Policy update validation
- Deprecated API usage (datetime.utcnow)
- Redis configuration consistency
- Constitutional validation bypass detection

**Example violations:**
```python
# Missing constitutional hash
"""Module without hash"""

# Hardcoded credentials
API_KEY = "sk-1234567890"

# Direct DB access without validation
cursor.execute("DELETE FROM users")
```

### 2. security-rules.yaml (13 rules)
Security-focused rules aligned with OWASP Top 10:
- SQL injection detection
- Command injection patterns
- Unsafe deserialization (pickle, YAML)
- Missing input validation in FastAPI endpoints
- JWT verification bypass
- Weak cryptographic algorithms
- Insecure random number generation
- eval() usage detection
- Path traversal vulnerabilities
- Rate limiting enforcement
- Information exposure in exceptions
- Sensitive data logging

**Example violations:**
```python
# SQL injection
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# Command injection
subprocess.run(f"ls {user_input}", shell=True)

# Unsafe deserialization
data = pickle.loads(user_data)
```

### 3. code-quality.yaml (15 rules)
Python best practices and code quality:
- Async function without await
- Missing error handling
- Deprecated API usage
- Bare except clauses
- Missing type hints
- Mutable default arguments
- Inefficient logging patterns
- Synchronous sleep in async functions
- Missing docstrings
- Complex boolean expressions
- Redundant comprehensions

**Example violations:**
```python
# Async without await
async def process():
    return data.upper()

# Mutable default argument
def add_item(item, items=[]):
    items.append(item)

# time.sleep in async
async def wait():
    time.sleep(1)
```

### 4. agent-bus-patterns.yaml (16 rules)
ACGS-specific architectural patterns:
- Message constitutional hash validation
- Direct agent communication bypass detection
- Missing message validation
- Agent bus lifecycle (start/stop)
- Message priority settings
- Deliberation layer usage for high-impact operations
- Agent registration requirements
- Message status checking
- Policy client initialization
- Resource cleanup (Redis connections)
- Import fallback patterns
- Deprecated module imports
- Shared configuration usage

**Example violations:**
```python
# Missing constitutional hash
msg = AgentMessage(from_agent="a", to_agent="b", content={})

# Direct agent communication
agent1.send_to(agent2, message)

# Deprecated import
from enhanced_agent_bus.core_rust import EnhancedAgentBus
```

## Installation

### Install Semgrep
```bash
# Using pip
pip install semgrep

# Using Homebrew (macOS)
brew install semgrep

# Using Docker
docker pull returntocorp/semgrep
```

### Verify Installation
```bash
semgrep --version
```

## Usage

### Scan Entire Project
```bash
# From project root
cd /home/dislove/document/acgs2
semgrep --config .semgrep/ .
```

### Scan Specific Directory
```bash
# Scan enhanced_agent_bus only
semgrep --config .semgrep/ enhanced_agent_bus/

# Scan services only
semgrep --config .semgrep/ services/
```

### Scan with Specific Rule File
```bash
# Constitutional compliance only
semgrep --config .semgrep/constitutional-compliance.yaml .

# Security rules only
semgrep --config .semgrep/security-rules.yaml .

# Code quality only
semgrep --config .semgrep/code-quality.yaml .

# Agent bus patterns only
semgrep --config .semgrep/agent-bus-patterns.yaml enhanced_agent_bus/
```

### Filter by Severity
```bash
# Show only ERROR level issues
semgrep --config .semgrep/ --severity ERROR .

# Show ERROR and WARNING
semgrep --config .semgrep/ --severity ERROR --severity WARNING .
```

### Output Formats
```bash
# JSON output
semgrep --config .semgrep/ --json . > semgrep-results.json

# SARIF format (for GitHub)
semgrep --config .semgrep/ --sarif . > semgrep-results.sarif

# JUnit XML (for CI)
semgrep --config .semgrep/ --junit-xml . > semgrep-results.xml

# GitHub Actions format
semgrep --config .semgrep/ --github-actions-output .
```

### Autofix
```bash
# Preview fixes
semgrep --config .semgrep/ --autofix --dryrun .

# Apply fixes automatically
semgrep --config .semgrep/ --autofix .
```

## CI/CD Integration

### GitHub Actions
Create `.github/workflows/semgrep.yml`:
```yaml
name: Semgrep

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  semgrep:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: returntocorp/semgrep-action@v1
        with:
          config: .semgrep/
          generateSarif: true
```

### GitLab CI
Add to `.gitlab-ci.yml`:
```yaml
semgrep:
  image: returntocorp/semgrep
  script:
    - semgrep --config .semgrep/ --json . > semgrep-results.json
  artifacts:
    reports:
      sast: semgrep-results.json
```

### Pre-commit Hook
Add to `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/returntocorp/semgrep
    rev: v1.50.0
    hooks:
      - id: semgrep
        args: ['--config', '.semgrep/', '--error']
```

## Rule Statistics

| Rule File | Rules | ERROR | WARNING | INFO |
|-----------|-------|-------|---------|------|
| constitutional-compliance.yaml | 10 | 6 | 3 | 0 |
| security-rules.yaml | 13 | 10 | 3 | 0 |
| code-quality.yaml | 15 | 3 | 4 | 8 |
| agent-bus-patterns.yaml | 16 | 5 | 8 | 3 |
| **Total** | **54** | **24** | **18** | **11** |

## Customization

### Ignoring False Positives
Add `# nosemgrep` comment:
```python
# nosemgrep: sql-injection-risk
cursor.execute(f"SELECT * FROM {table_name}")  # table_name is validated
```

### Project-wide Ignores
Create `.semgrepignore`:
```
# Test files
tests/
*_test.py

# Generated files
*_pb2.py
migrations/

# Vendor dependencies
venv/
node_modules/
```

### Custom Rules
Add new rules to existing files or create new rule files:
```yaml
rules:
  - id: my-custom-rule
    message: Custom rule message
    severity: WARNING
    languages: [python]
    pattern: |
      def $FUNC(...):
          ...
    metadata:
      category: custom
```

## Performance Tips

1. **Scan incrementally**: Use `--baseline-commit` to scan only changed files
2. **Parallel execution**: Semgrep automatically uses multiple cores
3. **Cache results**: Use `--metrics off` to disable telemetry
4. **Focus scans**: Target specific directories or files

```bash
# Scan only changed files since main
semgrep --config .semgrep/ --baseline-commit main .

# Disable metrics for faster scans
semgrep --config .semgrep/ --metrics off .
```

## Troubleshooting

### Common Issues

**Issue: Too many false positives**
- Use `# nosemgrep` comments for known safe patterns
- Adjust rule patterns or add pattern-not clauses
- Configure .semgrepignore

**Issue: Slow scans**
- Use --baseline-commit for incremental scans
- Exclude test and vendor directories
- Run specific rule files instead of all

**Issue: Pattern not matching**
- Check pattern syntax in Semgrep playground: https://semgrep.dev/playground
- Use --debug flag to see pattern matching details
- Verify language and pattern alignment

## Resources

- **Semgrep Documentation**: https://semgrep.dev/docs/
- **Semgrep Registry**: https://semgrep.dev/r
- **Semgrep Playground**: https://semgrep.dev/playground
- **ACGS-2 Documentation**: /home/dislove/document/acgs2/CLAUDE.md

## Contributing

When adding new rules:

1. Include proper metadata (id, message, severity, languages)
2. Add test_cases in metadata
3. Provide fix suggestions where possible
4. Document in this README
5. Validate with `semgrep --validate --config .semgrep/`

## License

These rules are part of the ACGS-2 project and follow the same license.

---

**Constitutional Hash**: cdd01ef066bc6cf2
**Last Updated**: 2025-12-17
**Total Rules**: 54 (24 ERROR, 18 WARNING, 11 INFO)
