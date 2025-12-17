# ACGS-2 Project Guide for AI Assistants

## Project Overview

ACGS-2 (Advanced Constitutional Governance System 2) is an enhanced agent bus platform with constitutional compliance, featuring high-performance messaging, multi-tenant isolation, and AI-powered deliberation for high-risk decisions.

**Constitutional Hash**: `cdd01ef066bc6cf2` - Required for all operations

## Core Architecture

### Enhanced Agent Bus
- **Primary Component**: High-performance agent communication with constitutional validation
- **Backend Options**: Python (default) or Rust (performance-optimized)
- **Storage**: Redis-based message queuing and agent registry
- **Security**: Multi-tenant isolation with constitutional hash validation

### Deliberation Layer
- **Purpose**: AI-powered review system for high-risk decisions
- **Components**: Impact scorer, adaptive router, deliberation queue
- **Threshold**: Messages with impact score ≥0.8 route to deliberation
- **Learning**: Adaptive threshold adjustment based on performance feedback

## Build and Development

### Python Package (enhanced_agent_bus)
```bash
# Install with development dependencies
pip install -e enhanced_agent_bus[dev]

# Build Rust extension (optional, for performance)
cd enhanced_agent_bus/rust
cargo build --release
pip install -e .
```

### Testing
```bash
# Run tests with coverage
pytest --cov=enhanced_agent_bus --cov-report=html

# Run performance tests
python testing/performance_test.py

# Run end-to-end tests
python testing/e2e_test.py
```

### Linting and Code Quality
- **Coverage Requirement**: 80% minimum
- **Python Version**: 3.11+ required
- **Type Hints**: Strict typing enforced
- **Import Style**: Absolute imports preferred, relative imports for fallbacks

## Custom Utilities and Tools

### Syntax Repair Tools (`tools/`)
- `advanced_syntax_repair.py`: Fixes complex Python syntax issues
- `comprehensive_syntax_repair.py`: Multi-file syntax correction
- `fix_kwarg_type_hints.py`: Type hint corrections for function parameters

### Deployment Scripts (`scripts/`)
- `blue-green-deploy.sh`: Zero-downtime deployment
- `blue-green-rollback.sh`: Instant rollback capability
- `health-check.sh`: Comprehensive health monitoring

### Testing Infrastructure (`testing/`)
- `load_test.py`: Performance benchmarking
- `fault_recovery_test.py`: Resilience testing
- `e2e_test.py`: Full system integration tests

## Security and Compliance

### Constitutional Validation
- **Hash Check**: All messages validated against `cdd01ef066bc6cf2`
- **Dynamic Policy**: Optional policy registry integration
- **Multi-tenant**: Tenant-based message isolation

### Custom Security Scanning
```bash
# CI security scan includes constitutional validation
python -c "
from services.integration.search_platform.constitutional_search import ConstitutionalCodeSearchService
service = ConstitutionalCodeSearchService()
result = await service.scan_for_violations(['.'], ['py', 'js', 'ts'])
"
```

### CI/CD Security
- **Trivy**: Container vulnerability scanning
- **Semgrep**: Static analysis with custom rules
- **CodeQL**: Advanced security queries

## Critical Gotchas

### Constitutional Hash Requirements
- **Every Operation**: Must include `constitutional_hash="cdd01ef066bc6cf2"`
- **Validation Failure**: Blocks all message processing
- **Dynamic Mode**: Uses policy registry keys instead of static hash

### Rust Backend Dependencies
- **Optional**: Python implementation works without Rust
- **Performance**: 10-100x faster for high-throughput scenarios
- **Compatibility**: Automatic fallback to Python if Rust unavailable

### Message Routing
- **Impact Scoring**: Automatic calculation if not provided
- **Deliberation Queue**: High-impact messages (>0.8) require human/AI review
- **Timeout**: Default 5-10 minute deliberation timeout

### Multi-tenant Architecture
- **Isolation**: Messages segregated by `tenant_id`
- **Security Context**: Additional security metadata per message
- **Agent Registration**: Required before sending/receiving messages

## Directory Structure Notes

### Non-standard Layout
- `enhanced_agent_bus/`: Main package with Python and Rust components
- `k8s/`: Kubernetes manifests with blue-green deployment
- `docs/user-guides/`: Comprehensive user documentation
- `testing/`: Extensive testing infrastructure beyond standard pytest
- `tools/`: Custom development utilities
- `scripts/`: Deployment and maintenance scripts

### Configuration Files
- `pyproject.toml`: Poetry-style configuration with custom test markers
- `Cargo.toml`: Rust extension configuration
- `Dockerfile`: Multi-stage builds for Python+Rust

## Development Workflow

### Code Style Guidelines
- **Naming**: Constitutional references in comments and docstrings
- **Error Handling**: Graceful fallback (Rust → Python, Dynamic → Static)
- **Logging**: Structured logging with performance metrics
- **Async/Await**: Comprehensive async support throughout

### Testing Markers
```python
@pytest.mark.asyncio  # Async tests
@pytest.mark.slow     # Performance tests
@pytest.mark.integration  # External service tests
@pytest.mark.constitutional  # Governance validation tests
```

### Performance Considerations
- **Connection Pooling**: Redis connection management
- **Message Batching**: High-throughput optimization
- **Metrics**: Built-in performance monitoring
- **Caching**: Agent registry and routing decisions

## Deployment

### Kubernetes
```bash
# Blue-green deployment
kubectl apply -f k8s/blue-green-deployment.yml
kubectl apply -f k8s/blue-green-service.yml

# Rollback if needed
kubectl apply -f k8s/blue-green-rollback.yml
```

### Docker
```dockerfile
# Multi-stage build with Rust extension
FROM rust:latest AS rust-builder
WORKDIR /app/enhanced_agent_bus/rust
RUN cargo build --release

FROM python:3.11-slim
COPY --from=rust-builder /app/enhanced_agent_bus/rust/target/release/libenhanced_agent_bus.so /usr/local/lib/
```

## Monitoring and Observability

### Metrics
- **Message Counts**: Sent, received, failed
- **Agent Registry**: Active agents and capabilities
- **Queue Status**: Current queue size and processing rates
- **Routing Stats**: Fast lane vs deliberation percentages

### Health Checks
- **Redis Connectivity**: Message queue availability
- **Agent Bus Status**: Processing capability
- **Constitutional Validation**: Hash verification status
- **Deliberation Queue**: Pending item counts

## Troubleshooting

### Common Issues
1. **Constitutional Hash Mismatch**: Verify `CONSTITUTIONAL_HASH` constant
2. **Rust Backend Unavailable**: Check Cargo build, fallback to Python
3. **Message Routing Failures**: Check agent registration and tenant isolation
4. **Deliberation Timeouts**: Adjust timeout settings or impact thresholds

### Debug Mode
```python
import logging
logging.getLogger('enhanced_agent_bus').setLevel(logging.DEBUG)
```

## Integration Points

### External Services
- **Redis**: Message queuing and caching
- **Policy Registry**: Dynamic constitutional validation
- **Search Platform**: Constitutional document retrieval
- **Audit Service**: Compliance logging and verification

### API Compatibility
- **Fallback Imports**: Relative imports for testing/development
- **Optional Dependencies**: Graceful degradation when services unavailable
- **Version Pinning**: Strict dependency versions for reproducibility