# ACGS-2 Semgrep Rules

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

## Overview

This directory contains Semgrep rules for enforcing constitutional AI governance compliance, security best practices, and code quality standards in the ACGS-2 codebase.

## Rule Sets

### 1. Constitutional Compliance (`constitutional.yaml`)

Rules for enforcing constitutional AI governance requirements.

| Rule ID | Severity | Description |
|---------|----------|-------------|
| `acgs-missing-constitutional-hash-docstring` | WARNING | Module docstring should include constitutional hash |
| `acgs-hardcoded-constitutional-hash-wrong-value` | ERROR | Constitutional hash does not match expected value |
| `acgs-constitutional-hash-format-invalid` | ERROR | Constitutional hash has invalid format |
| `acgs-use-constant-not-literal-hash` | WARNING | Use CONSTITUTIONAL_HASH constant instead of literal |
| `acgs-bypass-constitutional-validation` | ERROR | Constitutional validation bypass detected |
| `acgs-conditional-validation-skip` | ERROR | Conditional skipping of validation |
| `acgs-unvalidated-policy-update` | ERROR | Policy update without validation |
| `acgs-direct-policy-modification` | WARNING | Direct policy modification without approval |
| `acgs-database-operation-without-validation` | WARNING | Database operation without constitutional validation |
| `acgs-deprecated-datetime-utcnow` | ERROR | datetime.utcnow() deprecated in Python 3.12+ |
| `acgs-deprecated-utcfromtimestamp` | ERROR | datetime.utcfromtimestamp() deprecated |
| `acgs-missing-audit-log-governance-action` | WARNING | Governance action without audit logging |

### 2. Security Rules (`security.yaml`)

OWASP Top 10 and security best practices.

| Rule ID | Severity | OWASP | Description |
|---------|----------|-------|-------------|
| `acgs-sql-injection-string-format` | ERROR | A03:2021 | SQL injection via string formatting |
| `acgs-command-injection-subprocess` | ERROR | A03:2021 | Command injection via subprocess |
| `acgs-code-injection-eval` | ERROR | A03:2021 | Code injection via eval/exec |
| `acgs-hardcoded-password` | ERROR | A07:2021 | Hardcoded password detected |
| `acgs-hardcoded-api-key` | ERROR | A07:2021 | Hardcoded API key detected |
| `acgs-hardcoded-bearer-token` | ERROR | A07:2021 | Hardcoded Bearer token |
| `acgs-unsafe-pickle-load` | ERROR | A08:2021 | Unsafe pickle deserialization |
| `acgs-unsafe-yaml-load` | ERROR | A08:2021 | Unsafe YAML deserialization |
| `acgs-weak-hash-md5` | ERROR | A02:2021 | MD5 hash algorithm (broken) |
| `acgs-weak-hash-sha1` | ERROR | A02:2021 | SHA-1 hash algorithm (weak) |
| `acgs-insecure-random` | ERROR | A02:2021 | Insecure random for security operations |
| `acgs-jwt-no-verification` | ERROR | A02:2021 | JWT without signature verification |
| `acgs-path-traversal-risk` | ERROR | A01:2021 | Path traversal vulnerability |
| `acgs-fastapi-missing-pydantic-validation` | WARNING | A03:2021 | Missing Pydantic validation |
| `acgs-exception-info-leak` | WARNING | A05:2021 | Exception details exposed |
| `acgs-sensitive-data-logging` | WARNING | A09:2021 | Sensitive data in logs |
| `acgs-missing-rate-limiting` | WARNING | A04:2021 | Missing rate limiting |

### 3. Agent Bus Patterns (`agent-bus.yaml`)

Rules specific to the Enhanced Agent Bus system.

| Rule ID | Severity | Description |
|---------|----------|-------------|
| `acgs-message-missing-hash` | INFO | AgentMessage without explicit constitutional_hash |
| `acgs-message-wrong-hash` | ERROR | AgentMessage with wrong hash value |
| `acgs-message-type-not-specified` | WARNING | AgentMessage without message_type |
| `acgs-bus-missing-await-start` | ERROR | start() called without await |
| `acgs-bus-missing-await-send` | ERROR | send_message() called without await |
| `acgs-bus-missing-await-stop` | ERROR | stop() called without await |
| `acgs-bus-missing-await-register` | ERROR | register_agent() called without await |
| `acgs-processor-missing-await` | ERROR | process() called without await |
| `acgs-bus-not-started-before-use` | WARNING | Bus used without start() |
| `acgs-bus-not-stopped` | WARNING | Bus not stopped for cleanup |
| `acgs-agent-not-registered` | WARNING | Message sent without agent registration |
| `acgs-redis-hardcoded-url` | WARNING | Hardcoded Redis URL |
| `acgs-redis-client-not-closed` | WARNING | Redis client not closed |
| `acgs-redis-missing-error-handling` | WARNING | Redis operation without error handling |
| `acgs-handler-missing-error-handling` | WARNING | Message handler without error handling |
| `acgs-validation-result-not-checked` | ERROR | ValidationResult not checked |
| `acgs-deprecated-core-import` | ERROR | Import from deprecated core module |
| `acgs-relative-import-missing-fallback` | INFO | Relative import without fallback |
| `acgs-heavy-import-without-try` | INFO | Heavy ML import without availability check |
| `acgs-high-impact-without-deliberation` | WARNING | High-impact operation without deliberation |

### 4. Cryptography Rules (`crypto.yaml`)

Rules for Ed25519 signatures and secure key handling.

| Rule ID | Severity | Description |
|---------|----------|-------------|
| `acgs-prefer-ed25519-over-rsa` | WARNING | RSA detected, prefer Ed25519 |
| `acgs-prefer-ed25519-over-ecdsa` | INFO | ECDSA detected, prefer Ed25519 |
| `acgs-weak-dsa-detected` | ERROR | DSA is deprecated |
| `acgs-hardcoded-private-key` | ERROR | Hardcoded private key |
| `acgs-hardcoded-secret-key` | ERROR | Hardcoded secret key |
| `acgs-private-key-logged` | ERROR | Private key in logs |
| `acgs-key-in-source-control` | WARNING | Key file reference in code |
| `acgs-signature-not-verified` | ERROR | Signature verification missing |
| `acgs-signature-verification-exception-not-handled` | WARNING | InvalidSignature not handled |
| `acgs-policy-signature-not-validated` | ERROR | Policy loaded without signature validation |
| `acgs-ed25519-key-generation` | INFO | Key generation detected (audit) |
| `acgs-key-size-too-small` | WARNING | Weak key size |
| `acgs-base64-key-decode-unvalidated` | WARNING | Base64 decode without validation |
| `acgs-ssl-verify-disabled` | ERROR | SSL verification disabled |
| `acgs-insecure-ssl-context` | ERROR | Insecure SSL context |

## Usage

### Basic Scan

Scan the entire codebase:

```bash
cd /home/dislove/document/acgs2
semgrep --config .semgrep/.semgrep.yml
```

### Scan Specific Directory

```bash
# Scan only enhanced_agent_bus
semgrep --config .semgrep/.semgrep.yml enhanced_agent_bus/

# Scan only services
semgrep --config .semgrep/.semgrep.yml services/
```

### Scan with Specific Rule Set

```bash
# Constitutional rules only
semgrep --config .semgrep/rules/constitutional.yaml

# Security rules only
semgrep --config .semgrep/rules/security.yaml

# Agent bus rules only
semgrep --config .semgrep/rules/agent-bus.yaml

# Crypto rules only
semgrep --config .semgrep/rules/crypto.yaml
```

### Output Formats

```bash
# JSON output
semgrep --config .semgrep/.semgrep.yml --json > results.json

# SARIF output (for GitHub/GitLab integration)
semgrep --config .semgrep/.semgrep.yml --sarif > results.sarif

# JUnit XML (for CI integration)
semgrep --config .semgrep/.semgrep.yml --junit-xml > results.xml
```

### Severity Filtering

```bash
# Only errors
semgrep --config .semgrep/.semgrep.yml --severity ERROR

# Errors and warnings
semgrep --config .semgrep/.semgrep.yml --severity ERROR --severity WARNING
```

### Verbose Output

```bash
semgrep --config .semgrep/.semgrep.yml --verbose
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Semgrep
on: [push, pull_request]

jobs:
  semgrep:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: .semgrep/.semgrep.yml
```

### GitLab CI

```yaml
semgrep:
  image: returntocorp/semgrep
  script:
    - semgrep --config .semgrep/.semgrep.yml --sarif > semgrep.sarif
  artifacts:
    reports:
      sast: semgrep.sarif
```

### Pre-commit Hook

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/returntocorp/semgrep
    rev: v1.45.0
    hooks:
      - id: semgrep
        args: ['--config', '.semgrep/.semgrep.yml']
```

## Rule Development

### Creating New Rules

1. Choose the appropriate rule file based on category
2. Follow the rule ID convention: `acgs-<category>-<description>`
3. Include required metadata fields
4. Add test cases

### Rule Template

```yaml
- id: acgs-category-rule-name
  message: |
    Brief description of the issue.

    Explanation of why this is a problem.

    Fix: How to resolve the issue
  severity: ERROR  # ERROR, WARNING, INFO
  languages: [python]
  pattern-either:
    - pattern: bad_pattern_1(...)
    - pattern: bad_pattern_2(...)
  patterns:
    - pattern-not: good_pattern(...)
  paths:
    exclude:
      - "**/*test*.py"
  metadata:
    category: constitutional-compliance  # or security, acgs-patterns, cryptography
    cwe: "CWE-345: Insufficient Verification of Data Authenticity"
    owasp: "AXX:2021 - Description"  # if applicable
    confidence: HIGH  # HIGH, MEDIUM, LOW
    likelihood: HIGH
    impact: CRITICAL  # CRITICAL, HIGH, MEDIUM, LOW
    subcategory:
      - vuln  # or audit, correctness, maintainability
    technology:
      - python
    acgs-rule-type: hash-validation  # custom type
    references:
      - https://example.com/reference
```

### Testing Rules

```bash
# Test a specific rule file
semgrep --config .semgrep/rules/constitutional.yaml --test

# Validate rule syntax
semgrep --config .semgrep/rules/constitutional.yaml --validate
```

## Constitutional Hash Reference

The ACGS-2 constitutional hash is: `cdd01ef066bc6cf2`

This hash must be:
- Present in module docstrings for audit compliance
- Used via the CONSTITUTIONAL_HASH constant from models.py
- Validated in all message processing
- Never bypassed in production code

## Performance Targets

These rules support ACGS-2 performance requirements:

| Metric | Target | Description |
|--------|--------|-------------|
| P99 Latency | <5ms | Message processing latency |
| Throughput | >100 RPS | Request handling capacity |
| Cache Hit Rate | >85% | Redis caching efficiency |
| Constitutional Compliance | 100% | All messages validated |

## Support

For questions or issues with these rules:

1. Check the rule metadata for references
2. Review the CLAUDE.md file for ACGS-2 patterns
3. Consult the ACGS-2 documentation in `/docs`

---

Constitutional Hash: cdd01ef066bc6cf2
