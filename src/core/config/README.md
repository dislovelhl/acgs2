# Configuration Directory

This directory contains configuration files for the ACGS-2 core component.

## Contents

### Build Configuration
- `pyproject.toml` - Python project configuration with Poetry-style metadata, dependencies, and build settings
- `requirements_optimized.txt` - Optimized Python dependencies with pinned versions for production

### CI/CD Configuration
- `Jenkinsfile` - Jenkins pipeline configuration for automated builds, tests, and deployments

### Testing Configuration
- `pytest.ini` - Pytest configuration for unit and integration testing

## Usage

### Development Setup
```bash
# Install dependencies
pip install -r config/requirements_optimized.txt

# Or use pyproject.toml with modern Python package managers
pip install -e .
```

### Testing
```bash
# Run tests with pytest configuration
pytest --config-file=config/pytest.ini
```

### CI/CD
The Jenkinsfile defines automated pipelines for:
- Code quality checks
- Unit and integration testing
- Security scanning
- Deployment to staging/production

## Constitutional Compliance

**Constitutional Hash**: `cdd01ef066bc6cf2`

All configuration files must support constitutional governance requirements.

## Maintenance

### Dependency Updates
- Regularly update `requirements_optimized.txt` with security patches
- Test dependency updates in development before committing
- Use `pip-audit` to check for known vulnerabilities

### Configuration Changes
- Document configuration changes and their rationale
- Test configuration changes in CI/CD before deployment
- Maintain backward compatibility where possible

### Security Considerations
- Review dependency licenses and security advisories
- Avoid committing sensitive configuration to version control
- Use environment variables for secrets and sensitive data
