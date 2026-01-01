# ACGS-2 Code Cleanup Procedures

**Constitutional Hash**: `cdd01ef066bc6cf2`

This document outlines the automated and manual procedures for maintaining code quality and preventing technical debt accumulation in the ACGS-2 project.

## Table of Contents

1. [Automated Cleanup](#automated-cleanup)
2. [Pre-commit Hooks](#pre-commit-hooks)
3. [CI/CD Integration](#cicd-integration)
4. [Quarterly Cleanup Schedule](#quarterly-cleanup-schedule)
5. [Manual Cleanup Procedures](#manual-cleanup-procedures)
6. [Cleanup Tools](#cleanup-tools)
7. [Best Practices](#best-practices)

## Automated Cleanup

### Pre-commit Hooks

ACGS-2 uses pre-commit hooks to automatically validate code quality before commits:

```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run manually on all files
pre-commit run --all-files

# Run specific hook
pre-commit run import-validation --all-files
```

#### Configured Hooks

- **Import Validation**: Detects unused imports automatically
- **Code Formatting**: Black + isort for consistent formatting
- **Linting**: Flake8 for code quality
- **Security**: Gitleaks for secrets detection
- **Constitutional Validation**: Ensures governance files contain required hash

### CI/CD Integration

The Jenkins pipeline includes automated cleanup validation:

```groovy
stage('Code Quality Checks') {
    steps {
        // Import validation
        sh 'python3 tools/import_cleanup.py --check .'

        // Code formatting checks
        sh 'black --check --diff .'
        sh 'isort --check-only --diff .'
        sh 'flake8 --max-line-length=100 --ignore=E501,W503 .'
    }
}
```

## Quarterly Cleanup Schedule

### Automated Quarterly Cleanup

ACGS-2 includes scheduled cleanup operations via GitHub Actions:

```yaml
# .github/workflows/quarterly-cleanup.yml
name: Quarterly Code Cleanup

on:
  schedule:
    # Run quarterly (Jan 1, Apr 1, Jul 1, Oct 1)
    - cron: '0 0 1 1,4,7,10 *'
  workflow_dispatch:

jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Automated Cleanup
        run: |
          python3 tools/import_cleanup.py --fix .
          black .
          isort .
          python3 -m py_compile $(find . -name "*.py")
```

### Manual Quarterly Tasks

Quarterly cleanup should include:

1. **Import Optimization**
   ```bash
   python3 tools/import_cleanup.py --fix .
   ```

2. **Dependency Audit**
   ```bash
   pip-audit --requirement requirements_optimized.txt
   ```

3. **Code Coverage Analysis**
   ```bash
   python3 -m pytest --cov=. --cov-report=html
   ```

4. **Performance Benchmarking**
   ```bash
   python3 testing/performance_test.py
   ```

5. **Security Scanning**
   ```bash
   bandit -r . -f json -o security_report.json
   ```

## Manual Cleanup Procedures

### Import Cleanup

```bash
# Check for unused imports
python3 tools/import_cleanup.py --check [file.py|directory]

# Remove unused imports automatically
python3 tools/import_cleanup.py --fix [file.py|directory]

# Dry run to see what would change
python3 tools/import_cleanup.py --dry-run [file.py|directory]
```

### Code Formatting

```bash
# Format Python code
black .

# Sort imports
isort --profile black .

# Check formatting without changes
black --check --diff .
isort --check-only --diff .
```

### Linting and Quality

```bash
# Run flake8 linting
flake8 --max-line-length=100 --ignore=E501,W503 .

# Run mypy type checking
mypy --strict --ignore-missing-imports .

# Security scanning
bandit -r . -f html -o security_report.html
```

### Architecture Analysis

```bash
# Import dependency analysis
python3 arch_import_analyzer.py

# Dead code detection
python3 -c "
import ast
import os
# Custom dead code analysis script
"

# Complexity analysis
radon cc -a .
```

## Cleanup Tools

### Core Tools

| Tool | Purpose | Command |
|------|---------|---------|
| `import_cleanup.py` | Import validation/removal | `python3 tools/import_cleanup.py --fix .` |
| `black` | Code formatting | `black .` |
| `isort` | Import sorting | `isort --profile black .` |
| `flake8` | Linting | `flake8 --max-line-length=100` |
| `pycln` | Import cleaning | `pycln --config pyproject.toml .` |
| `bandit` | Security scanning | `bandit -r .` |

### Advanced Tools

```bash
# Unused dependency detection
pip install pipdeptree
pipdeptree --warn silence

# Code complexity analysis
pip install radon
radon cc -a .  # Cyclomatic complexity
radon mi -a .  # Maintainability index

# Import graph visualization
pip install pycallgraph
pycallgraph --include 'acgs2_core.*' your_main_function
```

### Custom ACGS-2 Tools

Located in `tools/` directory:

- `import_cleanup.py`: Advanced import analysis and cleanup
- `syntax_repair.py`: Automated syntax error fixing
- `dependency_analyzer.py`: Import dependency mapping

## Best Practices

### Code Standards

1. **Import Organization**
   ```python
   # Standard library imports
   import os
   import sys

   # Third-party imports
   import requests
   import pydantic

   # Local imports
   from .models import Message
   from .validators import validate_hash
   ```

2. **Constitutional Compliance**
   - All governance-related files must include: `Constitutional Hash: cdd01ef066bc6cf2`
   - Critical functions should validate constitutional hash
   - Audit trails must reference the constitutional hash

3. **Error Handling**
   ```python
   # Use typed exceptions from enhanced_agent_bus.exceptions
   from enhanced_agent_bus.exceptions import ConstitutionalError

   try:
       validate_constitutional_hash(message.hash)
   except ConstitutionalError as e:
       logger.error(f"Constitutional validation failed: {e}")
       raise
   ```

### Automated Quality Gates

```python
# Quality gate script example
def quality_gate():
    """Run all quality checks."""
    checks = [
        ('Import validation', 'python3 tools/import_cleanup.py --check .'),
        ('Code formatting', 'black --check .'),
        ('Import sorting', 'isort --check-only .'),
        ('Linting', 'flake8 .'),
        ('Type checking', 'mypy --strict .'),
        ('Security', 'bandit -r .'),
    ]

    for name, cmd in checks:
        result = subprocess.run(cmd, shell=True, capture_output=True)
        if result.returncode != 0:
            print(f"❌ {name} failed")
            print(result.stdout.decode())
            print(result.stderr.decode())
            return False

    print("✅ All quality checks passed")
    return True
```

### Continuous Improvement

1. **Monitor Trends**
   - Track lines of code, complexity metrics, and import counts
   - Set up alerts for quality degradation
   - Regular code review focus on maintainability

2. **Tool Updates**
   - Keep linting and formatting tools updated
   - Review new static analysis tools quarterly
   - Update CI/CD configurations as needed

3. **Team Training**
   - Regular workshops on code quality tools
   - Documentation updates with new procedures
   - Peer reviews focusing on automated checks

## Troubleshooting

### Common Issues

1. **Pre-commit Hook Failures**
   ```bash
   # Skip specific hooks for urgent commits
   SKIP=import-validation git commit -m "urgent fix"

   # Run hooks manually to debug
   pre-commit run import-validation --files changed_file.py
   ```

2. **Import Cleanup False Positives**
   - `__init__.py` files often export symbols for convenience
   - TYPE_CHECKING imports are used for type hints only
   - Some imports may be used in string formatting or dynamic access

3. **CI/CD Pipeline Issues**
   ```bash
   # Debug locally
   docker run -v $(pwd):/app -w /app python:3.12 \
     bash -c "pip install -r requirements.txt && python3 tools/import_cleanup.py --check ."
   ```

### Emergency Procedures

For urgent deployments that fail quality checks:

1. Document the exception with justification
2. Use `SKIP` environment variable for specific hooks
3. Schedule immediate post-deployment cleanup
4. Update procedures if issues are systemic

## Metrics and Monitoring

### Quality Metrics

```python
# Quality metrics collection
metrics = {
    'total_lines': sum(1 for _ in open(f) for f in glob('**/*.py')),
    'unused_imports': count_unused_imports(),
    'complexity_score': calculate_complexity(),
    'test_coverage': get_coverage_percentage(),
    'security_issues': count_security_findings(),
}
```

### Dashboard Integration

Consider integrating with monitoring dashboards:
- Grafana panels for code quality trends
- Slack notifications for quality gate failures
- Automated reports in project documentation

---

**Last Updated**: December 31, 2025
**Version**: 1.0.0
**Constitutional Hash**: cdd01ef066bc6cf2
