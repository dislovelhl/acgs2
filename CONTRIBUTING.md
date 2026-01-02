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

| Service | Port | Purpose | Health Check |
|---------|------|---------|--------------|
| API Gateway | 8080 | Request routing | `/health` |
| Agent Bus | 8000 | Core processing | `/health` |
| OPA | 8181 | Policy engine | `/health` |
| Redis | 6379 | Caching | `redis-cli ping` |
| Kafka | 9092 | Messaging | Kafka topics |

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

### Test Structure
```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── e2e/           # End-to-end tests
└── fixtures/      # Test data and fixtures
```

### Running Tests
```bash
# All tests
./scripts/run-tests.sh

# Unit tests only
docker-compose -f docker-compose.dev.yml exec agent-bus python -m pytest tests/unit/ -v

# Integration tests
docker-compose -f docker-compose.dev.yml exec agent-bus python -m pytest tests/integration/ -v

# With coverage
docker-compose -f docker-compose.dev.yml exec agent-bus python -m pytest --cov=. --cov-report=html
```

### Test Guidelines
- Write tests for all new functionality
- Aim for >80% code coverage
- Use descriptive test names
- Test both success and failure cases
- Use fixtures for reusable test data

## 🔒 Security Considerations

### Code Security
- Never commit secrets or credentials
- Validate all inputs to prevent injection attacks
- Use parameterized queries for database operations
- Implement proper authentication and authorization

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
- [ ] Tests pass (`./scripts/run-tests.sh`)
- [ ] Code style checks pass (Ruff, Black)
- [ ] Documentation updated
- [ ] No security vulnerabilities
- [ ] Constitutional compliance maintained

### Review Checklist
- [ ] Code is readable and well-documented
- [ ] Tests are comprehensive and passing
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
