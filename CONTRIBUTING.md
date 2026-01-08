# Contributing to ACGS-2

Thank you for your interest in contributing to ACGS-2 (Advanced Constitutional Governance System)! This document provides guidelines and information for contributors.

## 🚀 Quick Start

### Development Environment Setup

1. **Prerequisites**

   - Docker and Docker Compose
   - Python 3.11+
   - Git

2. **Clone and Setup**

   ```bash
   git clone <repository-url>
   cd acgs2
   cp .env.dev .env  # Configure environment variables
   ```

3. **Start Development Environment**

   ```bash
   ./scripts/start-dev.sh
   ```

4. **Verify Setup**
   - API Gateway: http://localhost:8080/health
   - Agent Bus: http://localhost:8000/health
   - OPA: http://localhost:8181/health

## 📋 Development Workflow

### 1. Choose an Issue

- Check [Issues](../../issues) for tasks labeled `good first issue` or `help wanted`
- Comment on the issue to indicate you're working on it

### 2. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-number-description
```

### 3. Make Changes

- Follow the [Code Style Guidelines](#code-style)
- Write tests for new functionality
- Update documentation as needed

### 4. Test Your Changes

```bash
# Run tests
./scripts/run-tests.sh

# Run specific test file
docker-compose -f docker-compose.dev.yml exec agent-bus python -m pytest tests/test_specific.py -v

# Check code quality
docker-compose -f docker-compose.dev.yml exec agent-bus ruff check .
docker-compose -f docker-compose.dev.yml exec agent-bus black --check .
```

### 5. Commit Changes

```bash
git add .
git commit -m "feat: add your feature description

- What was changed
- Why it was changed
- How it was tested"
```

### 6. Create Pull Request

- Push your branch to GitHub
- Create a Pull Request with a clear description
- Reference any related issues

## 🛠️ Development Environment

### Available Services

| Service     | Port | Purpose         | Health Check     |
| ----------- | ---- | --------------- | ---------------- |
| API Gateway | 8080 | Request routing | `/health`        |
| Agent Bus   | 8000 | Core processing | `/health`        |
| OPA         | 8181 | Policy engine   | `/health`        |
| Redis       | 6379 | Caching         | `redis-cli ping` |
| Kafka       | 9092 | Messaging       | Kafka topics     |

### Useful Commands

```bash
# View logs
docker-compose -f docker-compose.dev.yml logs -f [service-name]

# Access service shell
docker-compose -f docker-compose.dev.yml exec [service-name] bash

# Restart service
docker-compose -f docker-compose.dev.yml restart [service-name]

# Stop environment
./scripts/stop-dev.sh

# Clean restart
docker-compose -f docker-compose.dev.yml down -v && ./scripts/start-dev.sh
```

## 💻 Code Style Guidelines

### Python Code Style

- Follow [PEP 8](https://pep8.org/) conventions
- Use [Black](https://black.readthedocs.io/) for code formatting
- Use [Ruff](https://github.com/astral-sh/ruff) for linting
- Maximum line length: 100 characters

### Commit Messages

Follow [Conventional Commits](https://conventionalcommits.org/) format:

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Documentation

- Update docstrings for all public functions/classes
- Add type hints for function parameters and return values
- Update README.md and relevant docs for significant changes

## 🧪 Testing

> For comprehensive testing documentation, see the [Testing Guide](./docs/testing-guide.md).

### Coverage Requirements

**ACGS-2 enforces strict coverage thresholds:**

| Metric              | Minimum | CI Enforcement              |
| ------------------- | ------- | --------------------------- |
| **System-wide**     | 85%     | Build fails below threshold |
| **Critical Paths**  | 95%     | Policy, auth, persistence   |
| **Branch Coverage** | 85%     | Enabled via `--cov-branch`  |
| **Patch Coverage**  | 80%     | PR coverage check           |

### Test Structure

```
src/core/tests/
cd src/core
├── unit/           # Unit tests (isolated components)
├── integration/    # Integration tests (cross-service)
│   ├── conftest.py       # Integration fixtures
│   ├── test_agent_bus.py # Agent Bus API tests
│   ├── test_opa.py       # OPA policy tests
│   ├── test_redis.py     # Redis cache tests
│   └── test_kafka.py     # Kafka messaging tests
├── e2e/           # End-to-end tests
└── fixtures/      # Test data and fixtures
```

### Running Tests

```bash
# Run unified test suite with parallel execution
python scripts/run_unified_tests.py --run --coverage --parallel

# Run with pytest directly (parallel execution with coverage)
cd src/core
pytest -n auto --cov=acgs2_core --cov-branch --cov-report=term-missing --cov-fail-under=85

# Unit tests only
pytest tests/unit/ -v

# Integration tests (mock-based, no services required)
pytest tests/integration/ -v -m integration

# Integration tests with live services
SKIP_LIVE_TESTS=false pytest tests/integration/ -v -m integration

# By marker
pytest -m constitutional   # Constitutional compliance tests
pytest -m "not slow"       # Skip slow tests
```

### Coverage Commands

```bash
# Terminal report with missing lines
coverage report --precision=2 --show-missing

# HTML report (opens in browser)
coverage html && open htmlcov/index.html

# Check critical path coverage
coverage report --include="**/opa_*.py,**/policy_*.py,**/kafka_bus.py,**/redis_*.py"
```

### TypeScript Testing

```bash
# claude-flow
cd claude-flow
npm test -- --coverage

# acgs2-neural-mcp
cd acgs2-neural-mcp
npm test -- --coverage
```

### Test Guidelines

- **Coverage Enforcement**: All new code must meet 85% coverage threshold
- **Critical Paths**: Auth, policy, and persistence code requires 95% coverage
- **Write tests first**: Use TDD for complex features
- **Descriptive names**: `test_agent_bus_returns_error_when_policy_validation_fails`
- **One assertion per test**: Focus on single behavior
- **Use fixtures**: Share setup code via pytest fixtures
- **Test edge cases**: Include error conditions and boundary cases
- **Branch coverage**: Ensure all code paths are tested

### Test Markers

| Marker                        | Description                     | Usage                        |
| ----------------------------- | ------------------------------- | ---------------------------- |
| `@pytest.mark.constitutional` | Constitutional compliance tests | Required for governance code |
| `@pytest.mark.integration`    | Integration tests               | Cross-service testing        |
| `@pytest.mark.asyncio`        | Async test functions            | Async code testing           |
| `@pytest.mark.slow`           | Slow-running tests              | Can be skipped in quick runs |

## 🔒 Security Considerations

### Secrets Detection and Protection

ACGS-2 implements **automated secrets detection** to prevent accidental credential commits through a multi-layered pre-commit hook system:

#### 🛡️ What Gets Detected

The pre-commit hooks automatically scan for:

- **AI Provider Credentials**: Anthropic, Claude Code, OpenRouter, HuggingFace, OpenAI API keys
- **Infrastructure Secrets**: AWS keys, JWT secrets, Vault tokens, database passwords
- **Generic Patterns**: 140+ built-in patterns for SSH keys, GitHub tokens, cloud credentials, etc.

#### ✅ What You CAN Commit

**Safe to commit:**

- Development placeholders (e.g., `dev-jwt-secret-min-32-chars-required`, `test-api-key-placeholder`)
- Example configuration files (`.env.example` with placeholder values)
- Test fixtures clearly marked as fake secrets
- Public certificates for testing (e.g., SAML test certificates)

**Example safe values:**

```env
# .env.example
JWT_SECRET=dev-jwt-secret-min-32-chars-required
ANTHROPIC_API_KEY=your-anthropic-api-key-here
POSTGRES_PASSWORD=test-password-123
```

#### ❌ What You CANNOT Commit

**Never commit:**

- Real API keys from any provider (Anthropic, OpenAI, AWS, etc.)
- Production passwords or tokens
- Private keys without `.gitleaksignore` exception
- Actual JWT secrets or session keys
- Real database credentials

#### 🚨 When Pre-commit Hooks Fail

If the secrets detection hooks block your commit:

**1. Is it a real secret?**

- **YES**: Remove it and use `secrets_manager.py` or Vault
- **NO**: Follow the quick-fix guide below

**2. Is it a false positive?**

- Check if it matches placeholder patterns (`dev-*`, `test-*`, `your-*`)
- Add to `.secrets-allowlist.yaml` if it's safe
- Add fingerprint to `.gitleaksignore` if needed

**3. Quick fixes:**

```bash
# Option 1: Use secrets_manager.py for safe storage
from acgs2_core.shared.secrets_manager import secrets_manager
secrets_manager.set("MY_SECRET", "real-value-here")

# Option 2: Add to allow-list for safe placeholders
# Edit .secrets-allowlist.yaml and add your pattern

# Option 3: Emergency bypass (use sparingly!)
git commit --no-verify -m "message"  # Only for verified safe content
```

#### 📖 Documentation

For comprehensive guidance:

- **[Migration Guide](./docs/SECRETS_DETECTION_MIGRATION.md)** - **If you're an existing developer**, start here to update your hooks
- **[Secrets Detection Guide](./docs/SECRETS_DETECTION.md)** - Complete documentation on what's detected and how it works
- **[Quick-Fix Guide](./docs/SECRETS_QUICK_FIX.md)** - Step-by-step solutions for common issues
- **[Secrets Manager Integration](./docs/SECRETS_DETECTION.md#integration-with-secrets_managerpy)** - How to use the safe storage system

#### 🔧 Setup

**For new developers**, the secrets detection hooks are automatically installed when you run:

```bash
pre-commit install  # One-time setup
```

**For existing developers**, follow the [Migration Guide](./docs/SECRETS_DETECTION_MIGRATION.md) to update your hooks and scan existing work.

After installation, every commit is automatically scanned. The hooks run quickly (<5s) and provide actionable error messages if secrets are detected.

### Code Security

- Never commit secrets or credentials (enforced by automated hooks)
- Validate all inputs to prevent injection attacks
- Use parameterized queries for database operations
- Implement proper authentication and authorization
- Use `secrets_manager.py` for credential storage and validation

### Reporting Security Issues

- **DO NOT** create public GitHub issues for security vulnerabilities
- Email security concerns to [security@acgs2.org](mailto:security@acgs2.org)
- Include detailed reproduction steps and potential impact

## 📚 Architecture Overview

### Core Components

1. **Enhanced Agent Bus**: Core message processing and routing
2. **Constitutional Validation**: Ensures all operations comply with governance rules
3. **Policy Engine (OPA)**: External policy decision point
4. **Audit Service**: Blockchain-anchored audit logging
5. **API Gateway**: Request routing and load balancing

### Key Design Principles

- **Constitutional Compliance**: All operations must pass constitutional validation
- **Zero Trust**: Assume breach and verify everything
- **Immutable Audit Trail**: All actions are logged to blockchain
- **Fail-Safe Defaults**: System fails securely when components fail

## 🤝 Code Review Process

### Pull Request Requirements

- [ ] Tests pass (`python scripts/run_unified_tests.py --run --coverage`)
- [ ] Code coverage meets thresholds (85% system-wide, 95% critical paths)
- [ ] Code style checks pass (Ruff, Black)
- [ ] Documentation updated
- [ ] No security vulnerabilities
- [ ] Constitutional compliance maintained

### Review Checklist

- [ ] Code is readable and well-documented
- [ ] Tests are comprehensive and passing
- [ ] Coverage thresholds met (check Codecov PR comment)
- [ ] No breaking changes without migration plan
- [ ] Performance impact assessed
- [ ] Security implications reviewed

## 📞 Getting Help

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and discussions
- **Documentation**: Check docs/ directory first

### Finding Your Way Around

- **README.md**: High-level project overview
- **docs/**: Detailed documentation
- **ARCHITECTURE.md**: System architecture details
- **C4-Documentation/**: Component diagrams and documentation

## 🎯 Areas for Contribution

### High Priority

- Performance optimization
- Security hardening
- Test coverage improvement
- Documentation enhancement

### Medium Priority

- New blockchain network support
- Additional policy templates
- UI/UX improvements
- Internationalization

### Future Opportunities

- Mobile app development
- Advanced analytics dashboard
- Machine learning integration
- Constitutional AI research

## 📄 License

By contributing to ACGS-2, you agree that your contributions will be licensed under the same MIT License that covers the project.

## 🙏 Recognition

Contributors are recognized in:

- GitHub repository contributors list
- CHANGELOG.md for significant contributions
- Project documentation acknowledgments

Thank you for contributing to ACGS-2! 🚀
