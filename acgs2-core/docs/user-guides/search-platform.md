# Search Platform - User Guide

**Constitutional Hash: `cdd01ef066bc6cf2`**

The Search Platform provides high-performance code and document search capabilities with constitutional compliance awareness. It integrates with ACGS-2's validation framework to detect security vulnerabilities, compliance violations, and enforce coding standards.

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Search Platform Client](#search-platform-client)
4. [Constitutional Code Search](#constitutional-code-search)
5. [Search Domains and Scopes](#search-domains-and-scopes)
6. [Violation Detection](#violation-detection)
7. [Security Scanning](#security-scanning)
8. [Advanced Analysis](#advanced-analysis)
9. [Real-time Monitoring](#real-time-monitoring)
10. [Container Security](#container-security)
11. [API Reference](#api-reference)
12. [Best Practices](#best-practices)

---

## Overview

The Search Platform enables:

- **Code Search**: Fast regex-based code search across repositories
- **Constitutional Compliance**: Automatic detection of compliance violations
- **Security Scanning**: Vulnerability detection with Semgrep and CodeQL integration
- **AST Analysis**: Deep code analysis using Abstract Syntax Trees
- **Container Security**: Trivy-based container image scanning
- **Real-time Dashboards**: Live monitoring of security violations

### Architecture

```
+------------------------+
| Constitutional Code    |
| Search Service         |
+----------+-------------+
           |
    +------+------+---------------+
    |             |               |
+---v---+    +----v----+    +-----v-----+
| Search |    | AST     |    | Semgrep/  |
| Client |    | Analyzer|    | CodeQL    |
+---+---+    +----+----+    +-----+-----+
    |             |               |
    +------+------+---------------+
           |
    +------v------+
    | Violation   |
    | Patterns    |
    +-------------+
```

---

## Quick Start

### Basic Setup

```python
from services.integration.search_platform import (
    SearchPlatformClient,
    SearchPlatformConfig,
    ConstitutionalCodeSearchService,
)

# Create client with default config
client = SearchPlatformClient()

# Or with custom configuration
config = SearchPlatformConfig(
    base_url="http://localhost:9080",
    timeout_seconds=30.0,
    max_connections=100,
    max_retries=3,
)
client = SearchPlatformClient(config)
```

### Simple Code Search

```python
async def search_code():
    async with SearchPlatformClient() as client:
        # Quick search
        results = await client.search_quick(
            pattern="def validate_.*",
            max_results=100
        )

        for match in results.results:
            print(f"{match.file}:{match.line_number}: {match.line_content}")
```

### Constitutional Compliance Search

```python
async def compliance_search():
    async with ConstitutionalCodeSearchService() as service:
        # Search with compliance checking
        result = await service.search(
            pattern="password",
            paths=["src/"],
            check_compliance=True
        )

        if result.has_violations:
            print(f"Found {len(result.violations)} violations!")
            for v in result.violations:
                print(f"  {v.severity}: {v.description} in {v.file}:{v.line_number}")
```

---

## Search Platform Client

### Configuration

Configure the client via environment variables or programmatically:

```python
# From environment variables
config = SearchPlatformConfig.from_env()

# Environment variables:
# SEARCH_PLATFORM_URL=http://localhost:9080
# SEARCH_PLATFORM_TIMEOUT=30.0
# SEARCH_PLATFORM_MAX_CONNECTIONS=100
# SEARCH_PLATFORM_MAX_RETRIES=3
```

### Connection Pooling & Circuit Breaker

The client includes built-in fault tolerance:

```python
config = SearchPlatformConfig(
    max_connections=100,                 # Connection pool size
    max_retries=3,                       # Retry attempts
    retry_delay_seconds=1.0,             # Initial retry delay
    circuit_breaker_threshold=5,         # Failures before opening circuit
    circuit_breaker_timeout=30.0,        # Recovery timeout
)
```

Circuit breaker states:
- **CLOSED**: Normal operation
- **OPEN**: Requests fail fast after threshold failures
- **HALF_OPEN**: Testing if service recovered

### Health Checks

```python
async def check_health():
    client = SearchPlatformClient()

    # Quick boolean check
    is_healthy = await client.is_healthy()

    # Detailed status
    status = await client.health_check()
    print(f"Status: {status.status}")
    print(f"Version: {status.version}")
    print(f"Workers: {status.workers}")

    # Ready check
    is_ready = await client.ready()
```

---

## Constitutional Code Search

The `ConstitutionalCodeSearchService` extends basic search with compliance features.

### Basic Compliance Search

```python
async def compliance_search():
    async with ConstitutionalCodeSearchService() as service:
        result = await service.search(
            pattern=r"api_key|secret|password",
            paths=["src/", "config/"],
            file_types=["py", "js", "ts"],
            check_compliance=True,
            max_results=1000
        )

        print(f"Query: {result.query}")
        print(f"Files searched: {result.total_files_searched}")
        print(f"Total matches: {result.total_matches}")
        print(f"Violations: {len(result.violations)}")
        print(f"Compliant matches: {len(result.compliant_matches)}")
        print(f"Duration: {result.duration_ms}ms")
```

### Scanning for Violations

```python
async def scan_violations():
    async with ConstitutionalCodeSearchService() as service:
        result = await service.scan_for_violations(
            paths=["src/"],
            file_types=["py"],
            severity_filter=["critical", "high"]
        )

        for violation in result.violations:
            print(f"""
Violation: {violation.violation_type.value}
File: {violation.file}:{violation.line_number}
Severity: {violation.severity}
Description: {violation.description}
Content: {violation.match_content}
Remediation: {violation.remediation}
""")
```

### Constitutional Hash Verification

```python
async def verify_hashes():
    async with ConstitutionalCodeSearchService() as service:
        result = await service.verify_constitutional_hash(
            paths=["services/", "enhanced_agent_bus/"]
        )

        print(f"Files with correct hash: {len(result.compliant_matches)}")
        print(f"Files missing hash: {len(result.violations)}")

        for violation in result.violations:
            print(f"  Missing hash: {violation.file}")
```

---

## Search Domains and Scopes

### Search Domains

| Domain | Description |
|--------|-------------|
| `CODE` | Source code files |
| `LOGS` | Log files |
| `DOCUMENTS` | Documentation files |
| `ALL` | Search all domains |

```python
from services.integration.search_platform.models import SearchDomain

# Search specific domain
results = await client.search(
    pattern="error",
    domain=SearchDomain.LOGS
)
```

### Search Scope

Define search boundaries:

```python
from services.integration.search_platform.models import SearchScope, TimeRange
from datetime import datetime, timedelta

scope = SearchScope(
    repos=["main-repo", "lib-repo"],
    paths=["src/", "lib/"],
    file_types=["py", "rs", "go"],
    include_globs=["**/*.py", "**/test_*.py"],
    exclude_globs=["**/node_modules/**", "**/__pycache__/**"],
    time_range=TimeRange(
        start=datetime.now() - timedelta(days=7),
        end=datetime.now()
    )
)
```

### Search Options

```python
from services.integration.search_platform.models import SearchOptions

options = SearchOptions(
    case_sensitive=False,
    whole_word=True,
    regex=True,
    multiline=False,
    max_results=1000,
    context_lines=3,      # Lines before/after match
    include_hidden=False,
    follow_symlinks=False,
    timeout_ms=30000
)

results = await client.search(
    pattern="TODO|FIXME",
    scope=scope,
    options=options
)
```

---

## Violation Detection

### Built-in Violation Patterns

The service includes default patterns for common security issues:

| Pattern | Severity | Description |
|---------|----------|-------------|
| `hardcoded_secrets` | Critical | Hardcoded passwords, API keys, tokens |
| `sql_injection_risk` | Critical | SQL injection vulnerabilities |
| `unsafe_deserialization` | Critical | Pickle/YAML unsafe loading |
| `eval_usage` | High | Use of eval() |
| `subprocess_shell` | High | subprocess with shell=True |
| `missing_constitutional_hash` | Medium | Files missing hash marker |

### Adding Custom Patterns

```python
from services.integration.search_platform.constitutional_search import (
    ConstitutionalPattern,
    ConstitutionalViolationType,
)

custom_pattern = ConstitutionalPattern(
    name="debug_code",
    pattern=r"(pdb\.set_trace|breakpoint\(\)|debugger)",
    violation_type=ConstitutionalViolationType.UNSAFE_PATTERN,
    severity="medium",
    description="Debug code left in production",
    remediation="Remove debugging statements before deployment",
    file_types=["py", "js"]
)

service = ConstitutionalCodeSearchService(
    custom_patterns=[custom_pattern]
)

# Or add after initialization
service.add_custom_pattern(custom_pattern)
```

### Removing Patterns

```python
# Remove a pattern by name
service.remove_pattern("eval_usage")
```

### Violation Types

| Type | Description |
|------|-------------|
| `MISSING_HASH` | Constitutional hash not found |
| `INVALID_HASH` | Constitutional hash incorrect |
| `UNSAFE_PATTERN` | Dangerous code patterns |
| `SECURITY_VIOLATION` | Security vulnerabilities |
| `COMPLIANCE_GAP` | Compliance requirements not met |
| `UNAUTHORIZED_ACCESS` | Access control issues |

---

## Security Scanning

### AST-Based Analysis

Deep Python code analysis using Abstract Syntax Trees:

```python
# AST analysis is automatic during scan_for_violations
result = await service.scan_for_violations(
    paths=["src/"],
    file_types=["py"]
)

# Detects:
# - Taint propagation (user input to sensitive operations)
# - SQL injection via tainted data
# - Command injection risks
# - Dependency injection vulnerabilities
```

### Taint Tracking

The AST analyzer tracks data flow from user inputs:

```python
# Example code that would be flagged:
user_input = request.args.get('query')  # Tainted!
cursor.execute(f"SELECT * FROM users WHERE name = '{user_input}'")
# ^ CRITICAL: Tainted data used in execute
```

### Semgrep Integration

Multi-language static analysis:

```python
from services.integration.search_platform.constitutional_search import SemgrepAnalyzer

analyzer = SemgrepAnalyzer()
violations = await analyzer.scan_file("src/auth.py")
```

### CodeQL Integration

Deep JavaScript/TypeScript analysis:

```python
from services.integration.search_platform.constitutional_search import CodeQLAnalyzer

analyzer = CodeQLAnalyzer()
violations = await analyzer.scan_file("src/api/handler.ts")

# Detects:
# - XSS vulnerabilities
# - SQL injection
# - Command injection
# - Path injection
```

### Finding Security Issues

```python
async def security_scan():
    async with ConstitutionalCodeSearchService() as service:
        result = await service.find_security_issues(
            paths=["src/"]
        )

        critical = [v for v in result.violations if v.severity == "critical"]
        high = [v for v in result.violations if v.severity == "high"]

        print(f"Critical issues: {len(critical)}")
        print(f"High severity: {len(high)}")

        for issue in critical:
            print(f"  CRITICAL: {issue.description}")
            print(f"    File: {issue.file}:{issue.line_number}")
            print(f"    Fix: {issue.remediation}")
```

---

## Advanced Analysis

### Symbol Definition Search

```python
async def find_definitions():
    async with SearchPlatformClient() as client:
        # Find function/class definitions
        results = await client.find_definition(
            symbol="validate_policy",
            paths=["src/"],
            language="python"
        )

        for match in results.results:
            print(f"Found: {match.file}:{match.line_number}")
```

### Reference Search

```python
async def find_references():
    async with SearchPlatformClient() as client:
        # Find all usages of a symbol
        results = await client.find_references(
            symbol="CONSTITUTIONAL_HASH",
            paths=["src/", "services/"]
        )

        print(f"Found {len(results.results)} references")
```

### Streaming Search

For large searches, use streaming to get results incrementally:

```python
async def streaming_search():
    async with SearchPlatformClient() as client:
        async for event in client.search_stream(
            pattern="TODO",
            domain=SearchDomain.CODE
        ):
            if event.event_type == SearchEventType.MATCH:
                match = event.data
                print(f"Found: {match['file']}:{match['line_number']}")
            elif event.event_type == SearchEventType.COMPLETED:
                print(f"Search completed: {event.data}")
            elif event.event_type == SearchEventType.ERROR:
                print(f"Error: {event.data['message']}")
```

---

## Real-time Monitoring

### Dashboard Integration

```python
from services.integration.search_platform.constitutional_search import RealTimeScanDashboard

# Dashboard is automatically created with the service
service = ConstitutionalCodeSearchService()
dashboard = service.dashboard

# Start a background scan
await dashboard.start_scan(
    scan_id="scan-001",
    paths=["src/"],
    file_types=["py"]
)

# Check status
status = dashboard.get_scan_status("scan-001")
print(f"Scan status: {status['status']}")

# Get dashboard summary
data = dashboard.get_dashboard_data()
print(f"""
Dashboard Summary:
- Total scans: {data['total_scans']}
- Total violations: {data['total_violations']}
- Critical violations: {data['critical_violations']}
- Active scans: {data['active_scans']}
""")
```

### False Positive Management

```python
from services.integration.search_platform.constitutional_search import FalsePositiveSuppressor

suppressor = FalsePositiveSuppressor()

# Add feedback for a violation
suppressor.add_feedback(violation, is_false_positive=True)

# Check if similar violations should be suppressed
# (Suppresses if >70% of feedback marks it as false positive)
should_suppress = suppressor.should_suppress(violation)
```

---

## Container Security

### Trivy Container Scanning

```python
from services.integration.search_platform.constitutional_search import TrivyContainerScanner

scanner = TrivyContainerScanner()

# Scan container image
violations = await scanner.scan_image("acgs2:latest")

for v in violations:
    print(f"{v.severity}: {v.description}")
    print(f"  Package: {v.match_content}")
    print(f"  Fix: {v.remediation}")
```

### Dockerfile Analysis

```python
violations = await scanner.scan_dockerfile("Dockerfile")

for v in violations:
    print(f"Line {v.line_number}: {v.description}")
    print(f"  Content: {v.match_content}")
    print(f"  Fix: {v.remediation}")
```

Common Dockerfile issues detected:
- Using `latest` tag in FROM
- Not cleaning package manager cache
- Using ADD with HTTP URLs

### Container Scan Summary

```python
summary = scanner.get_scan_summary()
print(f"""
Container Scan Summary:
- Total scans: {summary['total_scans']}
- Successful: {summary['successful_scans']}
- Total vulnerabilities: {summary['total_violations']}
""")
```

---

## API Reference

### SearchPlatformClient

| Method | Description |
|--------|-------------|
| `search(pattern, domain, scope, options)` | Full-featured search |
| `search_quick(pattern, paths, max_results)` | Quick search |
| `search_stream(pattern, domain, scope, options)` | Streaming search |
| `search_code(pattern, paths, file_types, ...)` | Code-specific search |
| `search_logs(pattern, paths, time_range, ...)` | Log search |
| `find_definition(symbol, paths, language)` | Find symbol definition |
| `find_references(symbol, paths)` | Find symbol references |
| `health_check()` | Get health status |
| `is_healthy()` | Quick health check |
| `ready()` | Readiness check |
| `get_stats()` | Platform statistics |

### ConstitutionalCodeSearchService

| Method | Description |
|--------|-------------|
| `search(pattern, paths, file_types, check_compliance, max_results)` | Search with compliance |
| `scan_for_violations(paths, file_types, severity_filter)` | Full violation scan |
| `verify_constitutional_hash(paths)` | Hash verification |
| `find_security_issues(paths)` | Security-focused scan |
| `add_custom_pattern(pattern)` | Add violation pattern |
| `remove_pattern(name)` | Remove pattern |

### Search Result Classes

| Class | Key Properties |
|-------|----------------|
| `SearchResponse` | `results`, `stats`, `error` |
| `SearchMatch` | `file`, `line_number`, `line_content`, `match_text` |
| `ConstitutionalSearchResult` | `violations`, `compliant_matches`, `has_violations` |
| `ConstitutionalViolation` | `violation_type`, `severity`, `description`, `remediation` |

---

## Best Practices

### 1. Use Async Context Managers

```python
# Good - resources properly cleaned up
async with ConstitutionalCodeSearchService() as service:
    result = await service.search(...)

# Avoid - may leak connections
service = ConstitutionalCodeSearchService()
result = await service.search(...)
# forgot to close!
```

### 2. Filter by Severity in CI/CD

```python
# Fail CI only on critical/high issues
result = await service.scan_for_violations(
    paths=["src/"],
    severity_filter=["critical", "high"]
)

if result.has_violations:
    for v in result.violations:
        print(f"{v.severity}: {v.description}")
    sys.exit(1)  # Fail the build
```

### 3. Use Constitutional Hash Verification

```python
# Add to pre-commit or CI
result = await service.verify_constitutional_hash(
    paths=["services/", "enhanced_agent_bus/"]
)

if result.violations:
    print("Files missing constitutional hash:")
    for v in result.violations:
        print(f"  - {v.file}")
    sys.exit(1)
```

### 4. Regular Security Scans

```python
# Schedule in CI/CD pipeline
async def daily_security_scan():
    async with ConstitutionalCodeSearchService() as service:
        result = await service.find_security_issues(["src/"])

        if result.critical_violations:
            await send_alert(
                "Critical security issues found!",
                result.critical_violations
            )
```

### 5. Container Image Scanning

```python
# Before deployment
async def pre_deploy_check(image_name: str):
    scanner = TrivyContainerScanner()
    violations = await scanner.scan_image(image_name)

    critical = [v for v in violations if v.severity == "critical"]
    if critical:
        raise Exception(f"Cannot deploy: {len(critical)} critical vulnerabilities")
```

---

## Next Steps

- [Enhanced Agent Bus Guide](./enhanced-agent-bus.md) - Messaging infrastructure
- [API Reference](./api-reference.md) - Complete API documentation
- [Constitutional Framework](./constitutional-framework.md) - Governance system
