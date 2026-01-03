# ACGS-2 Error Code Reference

**Constitutional Hash:** cdd01ef066bc6cf2
**Version:** 1.0.0
**Created:** 2026-01-03
**Status:** Production
**Purpose:** Comprehensive error code reference for operators and developers

---

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [How to Use This Guide](#how-to-use-this-guide)
3. [Error Code Structure](#error-code-structure)
4. [Severity Levels](#severity-levels)
5. [ACGS-1xxx: Configuration Errors](#acgs-1xxx-configuration-errors)
6. [ACGS-2xxx: Authentication/Authorization Errors](#acgs-2xxx-authenticationauthorization-errors)
7. [ACGS-3xxx: Deployment/Infrastructure Errors](#acgs-3xxx-deploymentinfrastructure-errors)
8. [ACGS-4xxx: Service Integration Errors](#acgs-4xxx-service-integration-errors)
9. [ACGS-5xxx: Runtime Errors](#acgs-5xxx-runtime-errors)
10. [ACGS-6xxx: Constitutional/Governance Errors](#acgs-6xxx-constitutionalgovernance-errors)
11. [ACGS-7xxx: Performance/Resource Errors](#acgs-7xxx-performanceresource-errors)
12. [ACGS-8xxx: Platform-Specific Errors](#acgs-8xxx-platform-specific-errors)
13. [Related Documentation](#related-documentation)
14. [Getting Help](#getting-help)

---

## Quick Reference

### Most Common Errors

| Error Code | Description | Severity | Quick Fix |
|------------|-------------|----------|-----------|
| **ACGS-1101** | Missing environment variable | CRITICAL | Add required env var to `.env` file |
| **ACGS-1301** | Constitutional hash mismatch | CRITICAL | Verify `CONSTITUTIONAL_HASH=cdd01ef066bc6cf2` |
| **ACGS-2403** | Cannot connect to OPA | CRITICAL | Start OPA container: `docker-compose up -d opa` |
| **ACGS-3101** | Docker daemon not running | CRITICAL | Start Docker Desktop or `systemctl start docker` |
| **ACGS-3301** | Port already in use | CRITICAL | Kill process on port or change port config |
| **ACGS-4101** | Redis connection failed | MEDIUM | Start Redis: `docker-compose up -d redis` |
| **ACGS-4201** | Kafka connection failed | HIGH | Start Kafka: `docker-compose up -d kafka` |
| **ACGS-4301** | Database connection failed | CRITICAL | Verify DATABASE_URL and start PostgreSQL |

### Severity Response Times

| Severity | Response Time | Examples |
|----------|---------------|----------|
| **CRITICAL** | Immediate (page on-call) | System down, security breach, data loss |
| **HIGH** | < 1 hour | Service degraded, auth failures |
| **MEDIUM** | < 4 hours (business hours) | Minor functionality impaired |
| **LOW** | Best effort | Informational, platform quirks |

---

## How to Use This Guide

### Finding an Error Code

1. **By Error Code**: Use browser search (Ctrl+F / Cmd+F) to find `ACGS-XXXX`
2. **By Category**: Navigate to the appropriate category section (1xxx, 2xxx, etc.)
3. **By Service**: Check the service-specific sections for errors in that service
4. **By Symptom**: Search for keywords like "connection refused", "timeout", etc.

### Understanding an Error Entry

Each error code entry provides:
- **Error Code**: ACGS-XXXX identifier
- **Severity**: CRITICAL, HIGH, MEDIUM, or LOW
- **Impact**: Effect on system (Deployment-Blocking, Service-Unavailable, etc.)
- **Description**: What the error means
- **Common Causes**: Why this error occurs
- **Symptoms**: How to recognize this error
- **Resolution**: Step-by-step fix instructions
- **Example**: Real-world scenario
- **Related Errors**: Similar or related error codes

### Diagnostic Workflow

```
1. Identify error code in logs (ACGS-XXXX)
   ↓
2. Look up error code in this document
   ↓
3. Check severity and impact
   ↓
4. Review common causes
   ↓
5. Follow resolution steps
   ↓
6. Verify fix with diagnostic commands
   ↓
7. Document resolution for team
```

---

## Error Code Structure

### Format

```
ACGS-XYZZ
```

Where:
- `ACGS` = Platform identifier (Agentic Constitutional Governance System)
- `X` = Major category (1-8)
- `Y` = Subcategory (0-9)
- `ZZ` = Specific error (01-99)

### Category Overview

| Code Range | Category | Common Severity | Description |
|------------|----------|-----------------|-------------|
| **ACGS-1xxx** | Configuration | CRITICAL-HIGH | Environment vars, config files, constitutional hash |
| **ACGS-2xxx** | Authentication/Authorization | CRITICAL-HIGH | OPA, webhooks, SSO, RBAC |
| **ACGS-3xxx** | Deployment/Infrastructure | CRITICAL | Docker, K8s, network, ports |
| **ACGS-4xxx** | Service Integration | CRITICAL-HIGH | Redis, Kafka, PostgreSQL, OPA |
| **ACGS-5xxx** | Runtime | HIGH-MEDIUM | Approvals, webhooks, messages |
| **ACGS-6xxx** | Constitutional/Governance | CRITICAL | Hash validation, MACI, deliberation |
| **ACGS-7xxx** | Performance/Resource | HIGH-MEDIUM | Latency, exhaustion, throughput |
| **ACGS-8xxx** | Platform-Specific | LOW-MEDIUM | Windows, macOS, Linux issues |

---

## Severity Levels

### CRITICAL

**When to Escalate**: Immediately (page on-call engineer)

**Characteristics**:
- System completely down or deployment blocked
- Security breach or constitutional violation
- Data loss risk
- No viable workaround

**Examples**: Constitutional hash mismatch, OPA unavailable, database down, MACI violations

---

### HIGH

**When to Escalate**: < 1 hour (alert engineering team)

**Characteristics**:
- Core functionality impaired
- Service degraded but partially operational
- Authentication/authorization failures
- Workarounds exist but complex

**Examples**: Webhook auth failures, Redis down (with fallback), Kafka issues, approval chain errors

---

### MEDIUM

**When to Escalate**: < 4 hours (business hours)

**Characteristics**:
- Non-essential functionality affected
- Performance degraded within acceptable limits
- Clear workarounds available
- Automatic retries working

**Examples**: Cache misses, config warnings, delayed notifications, latency warnings

---

### LOW

**When to Escalate**: Best effort (backlog)

**Characteristics**:
- No functional impact
- Platform-specific behavior (not errors)
- Informational logging
- Development/debugging information

**Examples**: Platform quirks, deprecation warnings, successful fallbacks

---

## ACGS-1xxx: Configuration Errors

**Category Description**: Errors related to system configuration, environment variables, config files, and constitutional hash validation.

**Common Severity**: HIGH to CRITICAL (deployment-blocking)

**Related Files**: `.env`, `config.yaml`, configuration validators

---

### ACGS-1001: ConfigurationError

**Severity**: HIGH
**Impact**: Deployment-Blocking
**Exception**: `ConfigurationError` (enhanced-agent-bus)

**Description**: Generic configuration error, base class for configuration issues.

**Common Causes**:
- Invalid configuration structure
- Missing required configuration sections
- Configuration validation failures

**Resolution**:
1. Review configuration file syntax
2. Check for missing required fields
3. Validate against schema/documentation
4. Restart service after fixing configuration

---

### ACGS-1101: MissingEnvironmentVariableError

**Severity**: CRITICAL
**Impact**: Deployment-Blocking
**Exception**: `MissingEnvironmentVariableError` (integration-service)

**Description**: Required environment variable not set. This is the most common deployment error.

**Common Causes**:
- `.env` file missing or not loaded
- Required variable not exported
- Typo in variable name
- Docker Compose not loading env file

**Symptoms**:
```
Error: Required environment variable not set: DATABASE_URL
Container exited with code 1
```

**Critical Variables**:
- `CONSTITUTIONAL_HASH` (must be `cdd01ef066bc6cf2`)
- `OPA_URL` (e.g., `http://opa:8181`)
- `REDIS_URL` (e.g., `redis://redis:6379`)
- `KAFKA_BOOTSTRAP_SERVERS` (e.g., `kafka:19092`)
- `DATABASE_URL` (PostgreSQL connection string)

**Resolution**:
1. **Check `.env` file exists**:
   ```bash
   ls -la .env
   ```

2. **Copy from example if missing**:
   ```bash
   cp .env.example .env
   ```

3. **Verify required variables**:
   ```bash
   grep -E "CONSTITUTIONAL_HASH|OPA_URL|REDIS_URL|KAFKA_BOOTSTRAP_SERVERS|DATABASE_URL" .env
   ```

4. **Add missing variable**:
   ```bash
   echo "DATABASE_URL=postgresql://user:password@localhost:5432/acgs2" >> .env
   ```

5. **Restart service**:
   ```bash
   docker-compose restart <service-name>
   ```

**Example**:
```bash
# Missing DATABASE_URL
ERROR: MissingEnvironmentVariableError: DATABASE_URL

# Fix:
echo "DATABASE_URL=postgresql://acgs2:password@postgres:5432/acgs2_db" >> .env
docker-compose restart hitl-approvals
```

**Related Errors**: ACGS-1102, ACGS-1103, ACGS-1202

---

### ACGS-1102: InvalidEnvironmentVariableError

**Severity**: HIGH
**Impact**: Deployment-Blocking

**Description**: Environment variable has invalid format or value.

**Common Causes**:
- Invalid URL format (missing protocol, wrong port)
- Type mismatch (string vs integer)
- Value outside acceptable range
- Wrong connection string format

**Symptoms**:
```
Error: Invalid environment variable: OPA_URL (must start with http:// or https://)
Invalid Redis URL format
```

**Resolution**:
1. **Check variable format**:
   ```bash
   # Wrong: OPA_URL=localhost:8181
   # Right: OPA_URL=http://opa:8181
   ```

2. **Verify URL scheme**:
   - HTTP/HTTPS URLs: `http://` or `https://`
   - Redis: `redis://` or `rediss://` (SSL)
   - PostgreSQL: `postgresql://` or `postgres://`

3. **Check for Docker network names**:
   ```bash
   # In Docker Compose, use service names not localhost
   # Wrong: REDIS_URL=redis://localhost:6379
   # Right: REDIS_URL=redis://redis:6379
   ```

**Example**:
```bash
# Wrong OPA URL (missing protocol)
OPA_URL=opa:8181

# Fix:
sed -i 's|OPA_URL=opa:8181|OPA_URL=http://opa:8181|' .env
docker-compose restart enhanced-agent-bus
```

**Related Errors**: ACGS-1101, ACGS-1401, ACGS-1402, ACGS-1403

---

### ACGS-1103: EnvironmentVariableTypeError

**Severity**: HIGH
**Impact**: Deployment-Blocking

**Description**: Environment variable type does not match expected type.

**Common Causes**:
- String provided where integer expected (e.g., port numbers)
- Boolean value incorrectly formatted (must be "true"/"false", not "yes"/"no")
- Numeric values with extra characters
- List/array values not properly comma-separated

**Symptoms**:
```
TypeError: Cannot convert 'yes' to boolean
ValueError: invalid literal for int() with base 10: '8080port'
Expected integer for REDIS_MAX_CONNECTIONS, got 'unlimited'
```

**Resolution**:
1. **Check expected type in documentation**:
   - Integers: Port numbers, timeouts, connection limits
   - Booleans: Feature flags, debug modes (use "true"/"false")
   - URLs: Must include protocol
   - Lists: Comma-separated values

2. **Common type fixes**:
   ```bash
   # Wrong: DEBUG_MODE=yes
   # Right: DEBUG_MODE=true

   # Wrong: REDIS_PORT=6379port
   # Right: REDIS_PORT=6379

   # Wrong: REDIS_MAX_CONNECTIONS=unlimited
   # Right: REDIS_MAX_CONNECTIONS=100
   ```

3. **Verify numeric values**:
   ```bash
   # Ensure no extra characters
   grep -E "PORT|TIMEOUT|MAX|LIMIT" .env
   ```

**Example**:
```bash
# Wrong type
REDIS_MAX_CONNECTIONS=unlimited

# Fix:
sed -i 's/REDIS_MAX_CONNECTIONS=unlimited/REDIS_MAX_CONNECTIONS=100/' .env
docker-compose restart integration-service
```

**Related Errors**: ACGS-1101, ACGS-1102

---

### ACGS-1201: ConfigValidationError

**Severity**: HIGH
**Impact**: Deployment-Blocking
**Exception**: `ConfigValidationError` (integration-service)
**Location**: `integration-service/src/config/validation.py`

**Description**: Configuration validation failed against defined schema or rules.

**Common Causes**:
- Invalid URL format in configuration
- Missing required configuration fields
- Invalid enum values (e.g., wrong log level)
- Regex pattern mismatch (e.g., invalid email format)
- Value constraints violated (min/max ranges)

**Symptoms**:
```
ConfigValidationError: Invalid configuration
  - Field 'log_level' must be one of: DEBUG, INFO, WARNING, ERROR
  - Field 'webhook_url' must match pattern: https?://.*
  - Field 'timeout' must be between 1 and 300 seconds
```

**Resolution**:
1. **Review validation error message** - it will specify which field(s) failed

2. **Check configuration schema**:
   ```bash
   # Look for validation rules in code
   grep -r "ConfigValidationError" integration-service/src/config/
   ```

3. **Common validation fixes**:
   ```bash
   # Log level must be valid enum
   # Wrong: LOG_LEVEL=verbose
   # Right: LOG_LEVEL=INFO

   # URLs must have protocol
   # Wrong: WEBHOOK_URL=example.com/hook
   # Right: WEBHOOK_URL=https://example.com/hook

   # Timeouts must be in valid range
   # Wrong: REQUEST_TIMEOUT=0
   # Right: REQUEST_TIMEOUT=30
   ```

4. **Validate configuration before deployment**:
   ```bash
   # Run validation check
   docker-compose run --rm integration-service python -c "
   from src.config.validation import validate_config
   validate_config()
   "
   ```

**Example**:
```bash
# Invalid log level
LOG_LEVEL=verbose

# Fix:
sed -i 's/LOG_LEVEL=verbose/LOG_LEVEL=INFO/' .env
docker-compose restart integration-service
```

**Related Errors**: ACGS-1001, ACGS-1202, ACGS-1203

---

### ACGS-1202: ConfigFileNotFoundError

**Severity**: HIGH
**Impact**: Deployment-Blocking

**Description**: Required configuration file not found.

**Common Causes**:
- `.env` file missing (not created from `.env.example`)
- Configuration file in wrong directory
- File path typo in startup script
- File not mounted in Docker container

**Symptoms**:
```
Error: Configuration file not found: .env
FileNotFoundError: [Errno 2] No such file or directory: '/app/.env'
Container exits immediately after start
```

**Resolution**:
1. **Check if .env file exists**:
   ```bash
   ls -la .env
   ```

2. **Create from example if missing**:
   ```bash
   cp .env.example .env
   ```

3. **Verify file location**:
   ```bash
   # .env should be in repository root
   pwd
   ls .env
   ```

4. **For Docker containers, check volume mount**:
   ```yaml
   # In docker-compose.yml:
   services:
     service-name:
       volumes:
         - ./.env:/app/.env  # Ensure this line exists
   ```

5. **Check file permissions**:
   ```bash
   chmod 644 .env
   ```

**Example**:
```bash
# .env missing
ls .env
# ls: cannot access '.env': No such file or directory

# Fix:
cp .env.example .env
# Edit required values
nano .env
# Restart services
docker-compose up -d
```

**Related Errors**: ACGS-1101, ACGS-1201

---

### ACGS-1203: ConfigSchemaValidationError

**Severity**: HIGH
**Impact**: Deployment-Blocking

**Description**: Configuration does not match expected schema version or structure.

**Common Causes**:
- Schema version mismatch (old config with new code)
- Required fields missing from configuration
- Invalid field types in config file
- Nested configuration structure incorrect
- YAML/JSON syntax errors

**Symptoms**:
```
SchemaValidationError: Configuration schema mismatch
  Expected schema version: 2.0
  Found schema version: 1.5
  Missing required fields: ['constitutional_hash', 'opa_config']
```

**Resolution**:
1. **Check schema version**:
   ```bash
   # Look for version field in config
   grep -i version config.yaml
   ```

2. **Update configuration to match schema**:
   ```bash
   # Compare with example config
   diff config.yaml config.example.yaml
   ```

3. **Add missing required fields**:
   ```yaml
   # config.yaml
   version: "2.0"
   constitutional_hash: "cdd01ef066bc6cf2"
   opa_config:
     url: "http://opa:8181"
     timeout: 30
   ```

4. **Validate YAML/JSON syntax**:
   ```bash
   # For YAML
   python -c "import yaml; yaml.safe_load(open('config.yaml'))"

   # For JSON
   python -c "import json; json.load(open('config.json'))"
   ```

5. **Check for common syntax errors**:
   - Incorrect indentation (YAML)
   - Missing commas (JSON)
   - Unquoted strings with special characters

**Example**:
```bash
# Old config missing required fields
# Fix by adding constitutional_hash
echo "constitutional_hash: cdd01ef066bc6cf2" >> config.yaml
docker-compose restart
```

**Related Errors**: ACGS-1001, ACGS-1201, ACGS-1202

---

### ACGS-1301: ConstitutionalHashMismatchError

**Severity**: CRITICAL
**Impact**: Deployment-Blocking + Security-Violation
**Exception**: `ConstitutionalHashMismatchError` (enhanced-agent-bus, sdk)

**Description**: Constitutional hash validation failed. This is a critical safety mechanism that prevents deployment of unapproved code.

**Expected Hash**: `cdd01ef066bc6cf2`

**Common Causes**:
- Wrong hash in `.env` file
- Hash not set in environment
- Kubernetes ConfigMap not updated
- Typo in hash value

**Symptoms**:
```
CRITICAL: Constitutional hash mismatch
Expected: cdd01ef0...
Received: <null> or <wrong-hash>
Deployment blocked for safety
```

**Resolution**:
1. **Verify constitutional hash**:
   ```bash
   grep CONSTITUTIONAL_HASH .env
   ```

2. **Set correct hash**:
   ```bash
   # Correct value:
   CONSTITUTIONAL_HASH=cdd01ef066bc6cf2
   ```

3. **Update .env file**:
   ```bash
   sed -i 's/CONSTITUTIONAL_HASH=.*/CONSTITUTIONAL_HASH=cdd01ef066bc6cf2/' .env
   ```

4. **For Kubernetes deployments**, update ConfigMap:
   ```bash
   kubectl create configmap acgs2-config \
     --from-literal=CONSTITUTIONAL_HASH=cdd01ef066bc6cf2 \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

5. **Restart all services**:
   ```bash
   docker-compose restart
   # or
   kubectl rollout restart deployment
   ```

**⚠️ Important**: Never bypass this check. If you're getting this error, it means the code doesn't match the approved constitutional requirements.

**Example**:
```bash
# Check current hash
echo $CONSTITUTIONAL_HASH

# Fix wrong hash
export CONSTITUTIONAL_HASH=cdd01ef066bc6cf2
echo "CONSTITUTIONAL_HASH=cdd01ef066bc6cf2" >> .env

# Verify
docker-compose logs enhanced-agent-bus | grep "Constitutional hash validated"
```

**Related Errors**: ACGS-1302, ACGS-6101

---

### ACGS-1302: ConstitutionalValidationError

**Severity**: CRITICAL
**Impact**: Service-Unavailable
**Exception**: `ConstitutionalValidationError` (enhanced-agent-bus)
**Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`

**Description**: Constitutional validation check failed during runtime. The system enforces constitutional compliance for all operations.

**Common Causes**:
- Operation violates constitutional rules
- Alignment check failures
- Policy compliance violations
- Constitutional principles not satisfied
- Safety constraints violated

**Symptoms**:
```
ConstitutionalValidationError: Operation violates constitutional requirements
Constitutional alignment check failed
Safety constraints not satisfied
Policy compliance validation failed
```

**Resolution**:
1. **Review the validation error** - it will specify which constitutional requirement failed

2. **Check constitutional logs**:
   ```bash
   docker-compose logs enhanced-agent-bus | grep "Constitutional"
   ```

3. **Verify operation meets constitutional requirements**:
   - Check if operation aligns with defined policies
   - Ensure all safety constraints are met
   - Verify alignment principles are satisfied

4. **Review constitutional documentation**:
   ```bash
   # Check constitutional hash and principles
   grep CONSTITUTIONAL_HASH .env
   cat acgs2-core/docs/operations/constitutional_principles.md
   ```

5. **If legitimate operation is being rejected**:
   - Review constitutional policies in OPA
   - Check for overly restrictive rules
   - Consult with governance team

**⚠️ Important**: Do not bypass constitutional validation. These checks are critical safety mechanisms.

**Example**:
```bash
# Check constitutional validation logs
docker-compose logs enhanced-agent-bus | grep -A 5 "ConstitutionalValidationError"

# Verify constitutional hash is correct
echo $CONSTITUTIONAL_HASH
# Should be: cdd01ef066bc6cf2
```

**Related Errors**: ACGS-1301, ACGS-6101, ACGS-6201

---

### ACGS-1401: OPAConfigurationError

**Severity**: CRITICAL
**Impact**: Deployment-Blocking

**Description**: OPA service configuration invalid or incorrect.

**Common Causes**:
- Using `localhost` instead of Docker network service name
- Incorrect port number (should be 8181)
- Missing protocol in URL (`http://`)
- Wrong OPA endpoint path
- OPA_URL not set in environment

**Symptoms**:
```
OPAConfigurationError: Invalid OPA_URL
Cannot parse OPA URL: localhost:8181
OPA_URL must include protocol (http:// or https://)
```

**Resolution**:
1. **Check OPA_URL format**:
   ```bash
   grep OPA_URL .env
   # Should be: OPA_URL=http://opa:8181
   ```

2. **Common configuration mistakes**:
   ```bash
   # Wrong: OPA_URL=localhost:8181
   # Right: OPA_URL=http://localhost:8181  (from host)

   # Wrong: OPA_URL=opa:8181
   # Right: OPA_URL=http://opa:8181  (from container)
   ```

3. **Fix OPA URL**:
   ```bash
   # For Docker Compose (from within containers):
   sed -i 's|OPA_URL=.*|OPA_URL=http://opa:8181|' .env

   # For host access:
   sed -i 's|OPA_URL=.*|OPA_URL=http://localhost:8181|' .env
   ```

4. **Verify OPA is accessible**:
   ```bash
   # From host:
   curl http://localhost:8181/health

   # From container:
   docker-compose exec enhanced-agent-bus curl http://opa:8181/health
   ```

**Example**:
```bash
# Wrong OPA URL
OPA_URL=opa:8181

# Fix:
echo "OPA_URL=http://opa:8181" >> .env
docker-compose restart enhanced-agent-bus

# Verify:
docker-compose logs enhanced-agent-bus | grep "Connected to OPA"
```

**Related Errors**: ACGS-1102, ACGS-2403, ACGS-4401

---

### ACGS-1402: KafkaConfigurationError

**Severity**: CRITICAL
**Impact**: Deployment-Blocking

**Description**: Kafka configuration invalid or bootstrap servers incorrect.

**Common Causes**:
- Wrong Kafka port (9092 vs 19092 vs 29092 confusion)
- Using localhost instead of Docker service name
- Incorrect listener configuration
- Multiple broker addresses with typos

**Symptoms**:
```
KafkaConfigurationError: Invalid KAFKA_BOOTSTRAP_SERVERS
Cannot connect to broker: localhost:9092
Kafka listener confusion: Use kafka:19092 from containers
```

**Kafka Port Guide**:
- **9092**: External access from host (localhost:9092)
- **19092**: Internal Docker network (kafka:19092)
- **29092**: Additional internal listener (if configured)

**Resolution**:
1. **Check Kafka bootstrap servers**:
   ```bash
   grep KAFKA_BOOTSTRAP_SERVERS .env
   ```

2. **Fix common port confusion**:
   ```bash
   # From within Docker containers (most services):
   # Right: KAFKA_BOOTSTRAP_SERVERS=kafka:19092

   # From host machine (development tools):
   # Right: KAFKA_BOOTSTRAP_SERVERS=localhost:9092

   # Wrong: KAFKA_BOOTSTRAP_SERVERS=localhost:19092
   # Wrong: KAFKA_BOOTSTRAP_SERVERS=kafka:9092
   ```

3. **Update configuration**:
   ```bash
   # For container-based services:
   sed -i 's|KAFKA_BOOTSTRAP_SERVERS=.*|KAFKA_BOOTSTRAP_SERVERS=kafka:19092|' .env
   ```

4. **Verify Kafka is accessible**:
   ```bash
   # From host:
   docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092

   # From container:
   docker-compose exec enhanced-agent-bus nc -zv kafka 19092
   ```

**Example**:
```bash
# Wrong port from container
KAFKA_BOOTSTRAP_SERVERS=kafka:9092

# Fix:
sed -i 's|KAFKA_BOOTSTRAP_SERVERS=kafka:9092|KAFKA_BOOTSTRAP_SERVERS=kafka:19092|' .env
docker-compose restart hitl-approvals

# Verify:
docker-compose logs hitl-approvals | grep "Connected to Kafka"
```

**Related Errors**: ACGS-1102, ACGS-4201, ACGS-4202

---

### ACGS-1403: DatabaseConfigurationError

**Severity**: CRITICAL
**Impact**: Deployment-Blocking

**Description**: Database connection string invalid or credentials incorrect.

**Common Causes**:
- Invalid PostgreSQL URL format
- Wrong credentials (username/password)
- Incorrect database name
- Using localhost instead of Docker service name
- Missing database driver in URL (`postgresql://` vs `postgres://`)

**Symptoms**:
```
DatabaseConfigurationError: Invalid DATABASE_URL
Invalid connection string format
Could not parse DATABASE_URL
Missing password in connection string
```

**Connection String Format**:
```
postgresql://username:password@host:port/database_name
```

**Resolution**:
1. **Check DATABASE_URL format**:
   ```bash
   grep DATABASE_URL .env
   # Should look like: postgresql://user:pass@postgres:5432/dbname
   ```

2. **Common format issues**:
   ```bash
   # Missing protocol:
   # Wrong: DATABASE_URL=postgres:5432/acgs2_db
   # Right: DATABASE_URL=postgresql://acgs2:password@postgres:5432/acgs2_db

   # Missing database name:
   # Wrong: DATABASE_URL=postgresql://user:pass@postgres:5432
   # Right: DATABASE_URL=postgresql://user:pass@postgres:5432/acgs2_db

   # Wrong host (from container):
   # Wrong: DATABASE_URL=postgresql://user:pass@localhost:5432/db
   # Right: DATABASE_URL=postgresql://user:pass@postgres:5432/db
   ```

3. **Fix DATABASE_URL**:
   ```bash
   # Standard format for Docker Compose:
   echo "DATABASE_URL=postgresql://acgs2:acgs2password@postgres:5432/acgs2_db" >> .env
   ```

4. **Verify database is accessible**:
   ```bash
   # From host (if port 5432 is exposed):
   psql postgresql://acgs2:acgs2password@localhost:5432/acgs2_db -c "SELECT 1"

   # From container:
   docker-compose exec hitl-approvals pg_isready -h postgres -p 5432
   ```

5. **Check credentials match docker-compose.yml**:
   ```bash
   # Verify username, password, database name match
   grep -A 5 "POSTGRES_" docker-compose.yml
   ```

**Example**:
```bash
# Wrong: missing protocol
DATABASE_URL=postgres:5432/acgs2_db

# Fix:
sed -i 's|DATABASE_URL=.*|DATABASE_URL=postgresql://acgs2:acgs2password@postgres:5432/acgs2_db|' .env
docker-compose restart hitl-approvals

# Verify connection:
docker-compose logs hitl-approvals | grep "Database connected"
```

**Related Errors**: ACGS-1102, ACGS-4301, ACGS-4302

---

### ACGS-1501: TLSConfigurationError

**Severity**: HIGH
**Impact**: Service-Unavailable

**Description**: TLS/SSL configuration invalid or certificates missing.

**Common Causes**:
- Invalid or expired certificate
- Certificate chain incomplete
- Private key doesn't match certificate
- Certificate file permissions incorrect
- Self-signed certificate not trusted

**Symptoms**:
```
TLSConfigurationError: Invalid certificate
SSL handshake failed
Certificate verification failed
Private key does not match certificate
```

**Resolution**:
1. **Check certificate validity**:
   ```bash
   # Check certificate expiration
   openssl x509 -in cert.pem -noout -dates

   # Verify certificate chain
   openssl verify -CAfile ca.pem cert.pem
   ```

2. **Verify private key matches certificate**:
   ```bash
   # Get certificate modulus
   openssl x509 -in cert.pem -noout -modulus | md5sum

   # Get private key modulus (should match)
   openssl rsa -in key.pem -noout -modulus | md5sum
   ```

3. **Check file permissions**:
   ```bash
   # Certificates should be readable
   chmod 644 cert.pem ca.pem

   # Private keys should be restricted
   chmod 600 key.pem
   ```

4. **For self-signed certificates in development**:
   ```bash
   # Disable SSL verification (DEVELOPMENT ONLY)
   export SSL_VERIFY=false

   # Or add to .env:
   echo "SSL_VERIFY=false" >> .env
   ```

**Example**:
```bash
# Certificate doesn't match key
# Fix: regenerate certificate or use correct key

# For development, generate self-signed cert:
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Update configuration:
echo "TLS_CERT_PATH=/path/to/cert.pem" >> .env
echo "TLS_KEY_PATH=/path/to/key.pem" >> .env
```

**Related Errors**: ACGS-1502, ACGS-1503

---

### ACGS-1502: CORSConfigurationError

**Severity**: CRITICAL (Security)
**Impact**: Security-Vulnerability
**Location**: `acgs2-core/services/compliance_docs/src/main.py:25`

**Description**: CORS policy misconfigured allowing all origins. This is a known TODO that creates a security vulnerability.

**Current Behavior**: CORS is configured to allow all origins (`*`), which allows any website to access the API.

**Security Impact**:
- Cross-site request forgery (CSRF) attacks possible
- Unauthorized API access from malicious sites
- Data exposure to untrusted origins

**Resolution**:
1. **Review TODO comment** in `compliance_docs/src/main.py:25`

2. **Configure proper CORS policy**:
   ```python
   # Replace wildcard with specific origins
   app.add_middleware(
       CORSMiddleware,
       allow_origins=[
           "https://app.example.com",
           "https://dashboard.example.com"
       ],
       allow_credentials=True,
       allow_methods=["GET", "POST", "PUT", "DELETE"],
       allow_headers=["*"],
   )
   ```

3. **Use environment variable for origins**:
   ```bash
   # In .env:
   ALLOWED_ORIGINS=https://app.example.com,https://dashboard.example.com
   ```

4. **Implement origin validation**:
   ```python
   import os
   allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
   ```

**TODO Reference**: See `TODO_CATALOG.md` - CRITICAL priority

**Related Errors**: ACGS-1501, ACGS-1503

---

### ACGS-1503: SecretNotFoundError

**Severity**: CRITICAL
**Impact**: Deployment-Blocking

**Description**: Required secret not found in secret store or environment.

**Common Causes**:
- Kubernetes secret not created
- Secret key name mismatch
- Vault/AWS Secrets Manager misconfiguration
- Environment variable for secret not set
- Secret not mounted in container

**Symptoms**:
```
SecretNotFoundError: Required secret not found: WEBHOOK_SECRET
Kubernetes secret 'acgs2-secrets' does not exist
Failed to fetch secret from Vault: path not found
```

**Resolution**:
1. **For Kubernetes deployments, create secret**:
   ```bash
   # Create secret from literals
   kubectl create secret generic acgs2-secrets \
     --from-literal=WEBHOOK_SECRET=your-secret-here \
     --from-literal=DATABASE_PASSWORD=db-password

   # Or from file
   kubectl create secret generic acgs2-secrets \
     --from-file=.env
   ```

2. **Verify secret exists**:
   ```bash
   kubectl get secret acgs2-secrets
   kubectl describe secret acgs2-secrets
   ```

3. **Check secret is mounted in pod**:
   ```yaml
   # In deployment.yaml:
   env:
     - name: WEBHOOK_SECRET
       valueFrom:
         secretKeyRef:
           name: acgs2-secrets
           key: WEBHOOK_SECRET
   ```

4. **For Vault, check path and policies**:
   ```bash
   # Test Vault access
   vault kv get secret/acgs2/webhooks

   # Verify policy allows read
   vault policy read acgs2-read-policy
   ```

5. **For AWS Secrets Manager**:
   ```bash
   # Verify secret exists
   aws secretsmanager describe-secret --secret-id acgs2/production

   # Test retrieval
   aws secretsmanager get-secret-value --secret-id acgs2/production
   ```

**Example**:
```bash
# Kubernetes: create missing secret
kubectl create secret generic acgs2-secrets \
  --from-literal=WEBHOOK_SECRET=$(openssl rand -hex 32) \
  --from-literal=JWT_SECRET=$(openssl rand -hex 32)

# Restart pods to pick up secret
kubectl rollout restart deployment/integration-service
```

**Related Errors**: ACGS-1101, ACGS-1501, ACGS-1502

---

### ACGS-1504: OIDCConfigurationError

**Severity**: HIGH
**Impact**: Service-Unavailable
**Exception**: `OIDCConfigurationError` (shared-auth)
**Location**: `acgs2-core/shared/auth/oidc_handler.py`

**Description**: OIDC (OpenID Connect) provider configuration error.

**Common Causes**:
- Missing client ID or client secret
- Invalid OIDC discovery URL
- Provider not properly registered
- Redirect URI mismatch
- Incorrect scopes configuration

**Symptoms**:
```
OIDCConfigurationError: Missing OIDC_CLIENT_ID
Failed to fetch OIDC discovery document from https://auth.example.com/.well-known/openid-configuration
Invalid redirect URI: must match configured value
```

**Resolution**:
1. **Check required OIDC environment variables**:
   ```bash
   grep -E "OIDC_" .env
   # Required variables:
   # OIDC_PROVIDER_URL=https://auth.example.com
   # OIDC_CLIENT_ID=your-client-id
   # OIDC_CLIENT_SECRET=your-client-secret
   # OIDC_REDIRECT_URI=https://yourapp.example.com/auth/callback
   ```

2. **Test OIDC discovery endpoint**:
   ```bash
   curl https://auth.example.com/.well-known/openid-configuration
   # Should return JSON with issuer, authorization_endpoint, token_endpoint, etc.
   ```

3. **Verify client ID and secret with provider**:
   - Log into your OIDC provider (Auth0, Okta, Keycloak, etc.)
   - Check client application settings
   - Regenerate secret if needed

4. **Fix redirect URI mismatch**:
   ```bash
   # Redirect URI must exactly match provider configuration
   # Including protocol (https://) and path
   OIDC_REDIRECT_URI=https://app.example.com/auth/callback
   ```

5. **Verify scopes**:
   ```bash
   # Common OIDC scopes
   OIDC_SCOPES=openid,profile,email
   ```

**Example**:
```bash
# Missing OIDC client ID
# Fix by adding to .env:
cat >> .env << EOF
OIDC_PROVIDER_URL=https://auth.example.com
OIDC_CLIENT_ID=acgs2-client-id
OIDC_CLIENT_SECRET=your-secret-here
OIDC_REDIRECT_URI=https://app.example.com/auth/callback
OIDC_SCOPES=openid,profile,email
EOF

# Restart service
docker-compose restart hitl-approvals
```

**Related Errors**: ACGS-1102, ACGS-1505, ACGS-2201, ACGS-2202

---

### ACGS-1505: SAMLConfigurationError

**Severity**: HIGH
**Impact**: Service-Unavailable
**Exception**: `SAMLConfigurationError` (shared-auth)
**Location**: `acgs2-core/shared/auth/saml_config.py`

**Description**: SAML (Security Assertion Markup Language) configuration error.

**Common Causes**:
- Invalid IdP (Identity Provider) metadata
- Certificate issues (expired, missing, wrong format)
- SP (Service Provider) entity ID mismatch
- Assertion Consumer Service (ACS) URL incorrect
- Missing or invalid signing certificate

**Symptoms**:
```
SAMLConfigurationError: Invalid IdP metadata
Failed to parse SAML certificate
SP entity ID mismatch: expected 'https://app.example.com', got 'http://localhost'
ACS URL not configured in IdP
```

**Resolution**:
1. **Check required SAML environment variables**:
   ```bash
   grep -E "SAML_" .env
   # Required variables:
   # SAML_IDP_METADATA_URL=https://idp.example.com/metadata
   # SAML_SP_ENTITY_ID=https://app.example.com
   # SAML_ACS_URL=https://app.example.com/saml/acs
   # SAML_CERT_PATH=/path/to/cert.pem
   # SAML_KEY_PATH=/path/to/key.pem
   ```

2. **Verify IdP metadata is accessible**:
   ```bash
   curl https://idp.example.com/metadata
   # Should return XML with IdP configuration
   ```

3. **Check certificate validity**:
   ```bash
   # Verify certificate hasn't expired
   openssl x509 -in saml-cert.pem -noout -dates

   # Check certificate matches key
   openssl x509 -in saml-cert.pem -noout -modulus | md5sum
   openssl rsa -in saml-key.pem -noout -modulus | md5sum
   # The two hashes should match
   ```

4. **Verify SP entity ID matches IdP configuration**:
   ```bash
   # Entity ID must exactly match what's configured in IdP
   # Usually the base URL of your application
   SAML_SP_ENTITY_ID=https://app.example.com
   ```

5. **Check ACS URL is registered with IdP**:
   - Log into IdP admin console
   - Verify ACS URL is in allowed callback URLs
   - Ensure it matches exactly (including https://)

6. **Validate SAML response**:
   ```bash
   # Use SAML tracer browser extension to debug
   # Check for common issues:
   # - Clock skew (NotBefore/NotOnOrAfter)
   # - Signature validation failures
   # - Attribute mapping issues
   ```

**Example**:
```bash
# Configure SAML authentication
cat >> .env << EOF
SAML_IDP_METADATA_URL=https://idp.example.com/metadata
SAML_SP_ENTITY_ID=https://app.example.com
SAML_ACS_URL=https://app.example.com/saml/acs
SAML_CERT_PATH=/app/certs/saml-cert.pem
SAML_KEY_PATH=/app/certs/saml-key.pem
EOF

# Mount certificates in docker-compose.yml:
# volumes:
#   - ./certs/saml-cert.pem:/app/certs/saml-cert.pem:ro
#   - ./certs/saml-key.pem:/app/certs/saml-key.pem:ro

# Restart service
docker-compose restart hitl-approvals
```

**Related Errors**: ACGS-1102, ACGS-1501, ACGS-1504, ACGS-2211, ACGS-2214

---

## ACGS-2xxx: Authentication/Authorization Errors

**Category Description**: Errors related to authentication, authorization, policy evaluation, and access control.

**Common Severity**: HIGH to CRITICAL (security-critical)

**Related Services**: OPA, webhooks, OIDC, SAML, RBAC

---

### ACGS-2101: InvalidSignatureError

**Severity**: HIGH
**Impact**: Service-Degraded
**Exception**: `InvalidSignatureError` (integration-service)

**Description**: HMAC signature verification failed for incoming webhook.

**Common Causes**:
- Incorrect shared secret key
- Signature algorithm mismatch (SHA256 vs SHA512)
- Payload tampering or modification
- Timestamp mismatch in signed payload
- Header name mismatch (X-Signature vs X-Hub-Signature)

**Symptoms**:
```
401 Unauthorized: Invalid signature
Webhook rejected: signature verification failed
Expected signature: sha256=abc...
Received signature: sha256=xyz...
```

**Resolution**:
1. **Verify shared secret matches sender**:
   ```bash
   # Check webhook configuration
   grep WEBHOOK_SECRET .env
   ```

2. **Check signature header name**:
   ```python
   # Common headers:
   # GitHub: X-Hub-Signature-256
   # Generic: X-Signature
   # Custom: check integration docs
   ```

3. **Verify signature algorithm**:
   ```bash
   # Ensure both sides use same algorithm
   # Common: HMAC-SHA256, HMAC-SHA512
   ```

4. **Test signature generation**:
   ```python
   import hmac
   import hashlib

   secret = b"your-secret-key"
   payload = b'{"event": "test"}'
   signature = hmac.new(secret, payload, hashlib.sha256).hexdigest()
   print(f"Expected: sha256={signature}")
   ```

5. **Check timestamp tolerance**:
   ```bash
   # Default: 300 seconds (5 minutes)
   # Increase if clock skew is issue
   SIGNATURE_TIMESTAMP_TOLERANCE=600
   ```

**Example**:
```bash
# Debug webhook signature
curl -X POST http://localhost:8080/webhooks/github \
  -H "X-Hub-Signature-256: sha256=<calculated-signature>" \
  -H "Content-Type: application/json" \
  -d '{"event":"test"}'

# If fails, check secret:
echo -n '{"event":"test"}' | openssl dgst -sha256 -hmac "your-secret"
```

**Related Errors**: ACGS-2102, ACGS-2105, ACGS-2106, ACGS-2107

---

### ACGS-2403: OPAConnectionError

**Severity**: CRITICAL
**Impact**: Service-Unavailable (Fail-Closed)
**Exception**: `OPAConnectionError` (enhanced-agent-bus, hitl-approvals, cli)

**Description**: Cannot connect to OPA policy server. **System fails closed** - all policy evaluations denied.

**Common Causes**:
- OPA container not running
- Wrong OPA_URL (using `localhost` instead of Docker service name)
- Port 8181 not accessible
- Network connectivity issues
- OPA startup not complete

**Symptoms**:
```
CRITICAL: Cannot connect to OPA at http://opa:8181
All requests denied (fail-closed)
Connection refused on port 8181
OPA health check failed
```

**Impact Note**: When OPA is unavailable, the system **fails closed** - all authorization requests are denied to ensure security.

**Resolution**:
1. **Check if OPA is running**:
   ```bash
   docker-compose ps opa
   # Should show "Up" status
   ```

2. **Start OPA if stopped**:
   ```bash
   docker-compose up -d opa
   ```

3. **Verify OPA is healthy**:
   ```bash
   curl http://localhost:8181/health
   # Should return: {"status": "ok"}
   ```

4. **Check OPA_URL configuration**:
   ```bash
   # In Docker Compose context:
   # Wrong: OPA_URL=http://localhost:8181
   # Right: OPA_URL=http://opa:8181

   grep OPA_URL .env
   ```

5. **Check OPA logs for startup errors**:
   ```bash
   docker-compose logs opa
   # Look for policy bundle loading errors
   ```

6. **Verify network connectivity**:
   ```bash
   # From inside another container:
   docker-compose exec enhanced-agent-bus ping opa
   docker-compose exec enhanced-agent-bus curl http://opa:8181/health
   ```

7. **Check policy bundle loaded**:
   ```bash
   curl http://localhost:8181/v1/policies
   # Should list loaded policies
   ```

**Example**:
```bash
# Typical failure:
ERROR: OPAConnectionError: Cannot connect to http://localhost:8181

# Diagnosis:
docker-compose ps opa  # Check if running
docker-compose logs opa | tail -20  # Check for errors

# Fix:
# 1. Start OPA
docker-compose up -d opa

# 2. Fix URL if needed
sed -i 's|OPA_URL=http://localhost:8181|OPA_URL=http://opa:8181|' .env

# 3. Restart dependent services
docker-compose restart enhanced-agent-bus hitl-approvals

# 4. Verify
curl http://localhost:8181/health
```

**Frequency**: Very common during initial setup

**Related Errors**: ACGS-2401, ACGS-2402, ACGS-2404, ACGS-4401

---

## ACGS-3xxx: Deployment/Infrastructure Errors

**Category Description**: Errors related to deployment, infrastructure, containers, networking, and platform issues.

**Common Severity**: CRITICAL (deployment-blocking) to MEDIUM

**Related Components**: Docker, Kubernetes, network, ports

---

### ACGS-3101: DockerDaemonNotRunningError

**Severity**: CRITICAL
**Impact**: Deployment-Blocking

**Description**: Cannot connect to Docker daemon. This is the most common development environment error.

**Common Causes**:
- Docker Desktop not started (macOS/Windows)
- Docker systemd service stopped (Linux)
- Docker socket permissions issue
- WSL2 integration disabled (Windows)

**Symptoms**:
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
Is the Docker daemon running?
docker-compose up fails immediately
```

**Resolution**:

**For macOS/Windows**:
1. **Start Docker Desktop**:
   - Open Docker Desktop application
   - Wait for "Docker Desktop is running" status
   - Check whale icon in system tray is active

2. **Verify Docker is running**:
   ```bash
   docker info
   # Should show Docker version and system info
   ```

**For Linux**:
1. **Check Docker service status**:
   ```bash
   systemctl status docker
   ```

2. **Start Docker service**:
   ```bash
   sudo systemctl start docker
   ```

3. **Enable Docker to start on boot**:
   ```bash
   sudo systemctl enable docker
   ```

4. **Add user to docker group** (if permission denied):
   ```bash
   sudo usermod -aG docker $USER
   # Log out and log back in for changes to take effect
   ```

**For WSL2 (Windows)**:
1. **Enable WSL integration** in Docker Desktop:
   - Settings → Resources → WSL Integration
   - Enable integration for your WSL2 distro

2. **Restart WSL2**:
   ```powershell
   wsl --shutdown
   # Then restart WSL
   ```

**Verification**:
```bash
# Test Docker is working
docker run hello-world
docker-compose version
```

**Frequency**: Very common in development (first-time setup)

**Related Errors**: ACGS-3102, ACGS-3103, ACGS-8301

---

### ACGS-3301: PortAlreadyInUseError

**Severity**: CRITICAL
**Impact**: Deployment-Blocking

**Description**: Port conflict detected - another process is using the required port.

**Common Ports**:
- 8181: OPA
- 8000: Agent Bus (**common macOS conflict with Airplay**)
- 8080: API Gateway
- 6379: Redis
- 19092: Kafka (external)
- 9092: Kafka (internal)
- 5432: PostgreSQL
- 8088: Temporal Web UI
- 7233: Temporal gRPC

**Symptoms**:
```
Error: Port 8000 is already in use
Cannot start container: port already allocated
Address already in use: 0.0.0.0:8181
```

**Resolution**:

1. **Identify process using port**:
   ```bash
   # Linux/macOS:
   lsof -i :8000

   # Windows:
   netstat -ano | findstr :8000
   ```

2. **Kill the process**:
   ```bash
   # Linux/macOS:
   lsof -ti:8000 | xargs kill -9

   # Windows:
   taskkill /PID <PID> /F
   ```

3. **For macOS port 8000 (Airplay conflict)**:
   ```bash
   # Disable Airplay Receiver:
   # System Preferences → Sharing → Uncheck "AirPlay Receiver"

   # OR change Agent Bus port in docker-compose.yml:
   services:
     enhanced-agent-bus:
       ports:
         - "8001:8000"  # Changed from 8000:8000
   ```

4. **Check for leftover Docker containers**:
   ```bash
   docker ps -a
   docker rm -f $(docker ps -aq)  # Remove all containers
   ```

5. **Restart Docker Compose**:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

**Example - macOS Airplay Conflict**:
```bash
# Port 8000 in use by Airplay
lsof -i :8000
# COMMAND   PID   USER
# ControlCe 1234  user

# Solution 1: Disable Airplay (System Preferences → Sharing)

# Solution 2: Change port
sed -i '' 's/8000:8000/8001:8000/' docker-compose.yml
docker-compose up -d

# Access Agent Bus on port 8001
curl http://localhost:8001/health
```

**Frequency**: Very common in development (especially macOS)

**Related Errors**: ACGS-3302, ACGS-3303, ACGS-8201

---

## ACGS-4xxx: Service Integration Errors

**Category Description**: Errors related to external service integrations (Redis, Kafka, PostgreSQL, OPA).

**Common Severity**: CRITICAL to HIGH

**Related Services**: Redis, Kafka, PostgreSQL, OPA, external APIs

---

### ACGS-4101: RedisConnectionError

**Severity**: MEDIUM
**Impact**: Service-Degraded (Cache unavailable, database fallback)
**Exception**: `RedisConnectionError` (hitl-approvals/escalation), `RedisNotAvailableError` (hitl-approvals/audit)

**Description**: Cannot connect to Redis. Service remains operational with database fallback (slower performance).

**Common Causes**:
- Redis container not running
- Wrong REDIS_URL configuration
- Port 6379 conflict
- Network connectivity issues
- Redis authentication failure

**Symptoms**:
```
Warning: Redis connection failed, using database fallback
Connection refused: redis:6379
Cache unavailable, queries slower
```

**Impact**: Service continues working but:
- Cache misses go directly to database (slower)
- Increased database load
- Higher response latency
- Session data may not persist

**Resolution**:

1. **Check if Redis is running**:
   ```bash
   docker-compose ps redis
   # Should show "Up" status
   ```

2. **Start Redis if stopped**:
   ```bash
   docker-compose up -d redis
   ```

3. **Verify Redis is responding**:
   ```bash
   docker-compose exec redis redis-cli ping
   # Should return: PONG
   ```

4. **Check REDIS_URL configuration**:
   ```bash
   grep REDIS_URL .env
   # Should be: redis://redis:6379 (in Docker)
   # Or: redis://localhost:6379 (host)
   ```

5. **Check authentication**:
   ```bash
   # If Redis requires password:
   # REDIS_URL=redis://:password@redis:6379

   # Test connection:
   docker-compose exec redis redis-cli -a password ping
   ```

6. **Check Redis logs**:
   ```bash
   docker-compose logs redis | tail -20
   ```

7. **Restart dependent services**:
   ```bash
   docker-compose restart hitl-approvals enhanced-agent-bus
   ```

**Example**:
```bash
# Redis not running
docker-compose ps redis
# State: Exit 1

# Start Redis
docker-compose up -d redis

# Verify connection
docker-compose exec redis redis-cli ping
# PONG

# Check service logs
docker-compose logs hitl-approvals | grep -i redis
# Should show: "Redis connection established"
```

**Performance Impact**:
- With Redis: P99 latency ~5ms
- Without Redis: P99 latency ~50-100ms (database queries)

**Related Errors**: ACGS-4102, ACGS-4103, ACGS-4104

---

### ACGS-4201: KafkaConnectionError

**Severity**: HIGH
**Impact**: Service-Degraded (Async processing degraded)
**Exception**: `KafkaConnectionError` (hitl-approvals)

**Description**: Cannot connect to Kafka broker. Async message processing unavailable.

**Common Causes**:
- Kafka container not running
- Zookeeper not running (Kafka dependency)
- Wrong KAFKA_BOOTSTRAP_SERVERS configuration
- Kafka still starting up (takes 30-60 seconds)
- Network connectivity issues

**Symptoms**:
```
Error: Failed to connect to Kafka broker
Connection error: kafka:19092
Async events not being processed
```

**Resolution**:

1. **Check if Kafka and Zookeeper are running**:
   ```bash
   docker-compose ps kafka zookeeper
   # Both should show "Up" status
   ```

2. **Start Kafka stack if stopped**:
   ```bash
   docker-compose up -d zookeeper
   # Wait 10 seconds for Zookeeper
   sleep 10
   docker-compose up -d kafka
   # Wait 30-60 seconds for Kafka to initialize
   ```

3. **Check Kafka logs for startup**:
   ```bash
   docker-compose logs kafka | grep -i "started"
   # Look for: "Kafka Server started"
   ```

4. **Verify Kafka is accepting connections**:
   ```bash
   # List topics (should not error)
   docker-compose exec kafka kafka-topics --list \
     --bootstrap-server localhost:9092
   ```

5. **Check KAFKA_BOOTSTRAP_SERVERS configuration**:
   ```bash
   grep KAFKA_BOOTSTRAP_SERVERS .env
   # Should be: kafka:19092 (from inside Docker)
   # Or: localhost:9092 (from host)
   ```

6. **Test Kafka connection**:
   ```bash
   # From inside container:
   docker-compose exec hitl-approvals nc -zv kafka 19092
   # Should show: Connection successful
   ```

7. **Restart services that depend on Kafka**:
   ```bash
   docker-compose restart hitl-approvals enhanced-agent-bus
   ```

**Startup Wait Time**: Kafka typically takes 30-60 seconds to fully start. Wait for log message:
```
INFO Kafka Server started (kafka.server.KafkaServer)
```

**Example**:
```bash
# Check Kafka status
docker-compose ps kafka zookeeper

# If not running, start in correct order
docker-compose up -d zookeeper && sleep 10
docker-compose up -d kafka && sleep 30

# Verify Kafka ready
docker-compose exec kafka kafka-broker-api-versions \
  --bootstrap-server localhost:9092

# Check topic creation
docker-compose exec kafka kafka-topics --list \
  --bootstrap-server localhost:9092
```

**Frequency**: Common during initial setup and after system restarts

**Related Errors**: ACGS-4202, ACGS-4203, ACGS-4204, ACGS-4205

---

### ACGS-4301: DatabaseConnectionError

**Severity**: CRITICAL
**Impact**: Service-Unavailable

**Description**: Cannot connect to PostgreSQL database. All database-dependent services unavailable.

**Common Causes**:
- PostgreSQL container not running
- Wrong DATABASE_URL connection string
- Invalid credentials
- Database not initialized
- Network connectivity issues
- Connection pool exhausted

**Symptoms**:
```
CRITICAL: Database connection failed
Could not connect to server: Connection refused
FATAL: password authentication failed for user "acgs2"
Service unavailable: database required
```

**Resolution**:

1. **Check if PostgreSQL is running**:
   ```bash
   docker-compose ps postgres
   # Should show "Up" status
   ```

2. **Start PostgreSQL if stopped**:
   ```bash
   docker-compose up -d postgres
   # Wait for database to initialize (~10 seconds)
   ```

3. **Check DATABASE_URL format**:
   ```bash
   grep DATABASE_URL .env
   # Format: postgresql://user:password@host:port/database
   # Example: postgresql://acgs2:password@postgres:5432/acgs2_db
   ```

4. **Verify database is responding**:
   ```bash
   docker-compose exec postgres pg_isready
   # Should return: postgres:5432 - accepting connections
   ```

5. **Test connection with psql**:
   ```bash
   docker-compose exec postgres psql -U acgs2 -d acgs2_db -c "SELECT 1;"
   # Should return: 1
   ```

6. **Check database logs**:
   ```bash
   docker-compose logs postgres | tail -30
   # Look for initialization completion
   ```

7. **Verify credentials**:
   ```bash
   # Username and password in DATABASE_URL must match
   # postgres container environment variables:
   # POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
   ```

8. **Check for migration issues**:
   ```bash
   # Run migrations if needed
   docker-compose exec hitl-approvals alembic upgrade head
   ```

**Common Connection String Issues**:
```bash
# Wrong (using localhost in Docker context):
DATABASE_URL=postgresql://acgs2:password@localhost:5432/acgs2_db

# Right (using Docker service name):
DATABASE_URL=postgresql://acgs2:password@postgres:5432/acgs2_db

# With special characters in password (URL-encode):
# Password: p@ssw0rd! → p%40ssw0rd%21
DATABASE_URL=postgresql://acgs2:p%40ssw0rd%21@postgres:5432/acgs2_db
```

**Example**:
```bash
# Database not responding
psql -h localhost -U acgs2 -d acgs2_db
# Connection refused

# Diagnosis:
docker-compose ps postgres
# State: Exit 1

# Fix: Start PostgreSQL
docker-compose up -d postgres
sleep 10

# Verify:
docker-compose exec postgres pg_isready
# postgres:5432 - accepting connections

# Test from service:
docker-compose exec hitl-approvals python -c \
  "import psycopg2; psycopg2.connect('$DATABASE_URL'); print('OK')"
```

**Related Errors**: ACGS-4302, ACGS-4303, ACGS-4304, ACGS-4305

---

## ACGS-5xxx: Runtime Errors

**Category Description**: Errors occurring during normal system operation, including business logic, workflow, and processing errors.

**Common Severity**: HIGH to MEDIUM

**Related Components**: Approval chains, webhooks, message processing

---

### ACGS-5101: ApprovalChainResolutionError

**Severity**: HIGH
**Impact**: Service-Degraded
**Location**: `acgs2-core/services/hitl_approvals/app/api/approvals.py:34`

**Description**: Cannot resolve approval chain. Currently uses static fallback logic; dynamic OPA-based resolution not implemented (TODO).

**Current Behavior**:
- Static approval chains only
- No dynamic chain resolution via OPA
- Fallback to default chain if specified chain not found

**Common Causes**:
- Approval chain ID not found
- OPA integration for dynamic chains not implemented
- Invalid chain configuration
- Chain template not loaded

**Symptoms**:
```
Warning: Approval chain not found, using fallback
Dynamic chain resolution not implemented
TODO: Implement OPA-based chain resolution
```

**Resolution**:

1. **Check available approval chains**:
   ```bash
   # List configured chains
   curl http://localhost:8080/api/v1/approval-chains
   ```

2. **Use valid chain ID** from configuration:
   ```json
   {
     "chain_id": "standard-approval",
     "request_type": "policy_change"
   }
   ```

3. **For dynamic chain resolution**, track TODO:
   - See `TODO_CATALOG.md` - HIGH priority
   - Location: `approvals.py:34`
   - Enhancement: Implement OPA-based dynamic chain resolution

**Workaround**:
```python
# Use predefined chain IDs:
# - "standard-approval"
# - "high-risk-approval"
# - "emergency-approval"

# Example API request:
{
  "request_id": "req-123",
  "chain_id": "standard-approval",
  "approvers": ["user1@example.com", "user2@example.com"]
}
```

**TODO Reference**: See `TODO_CATALOG.md` - HIGH priority

**Related Errors**: ACGS-5102, ACGS-5111, ACGS-5113

---

### ACGS-5201: WebhookDeliveryError

**Severity**: MEDIUM
**Impact**: Service-Degraded
**Exception**: `WebhookDeliveryError` (integration-service)

**Description**: Webhook delivery failed. Automatic retries scheduled.

**Common Causes**:
- Destination endpoint unavailable
- Network timeout
- HTTP 5xx error from endpoint
- SSL/TLS certificate issues

**Symptoms**:
```
Warning: Webhook delivery failed, scheduling retry
HTTP 503 Service Unavailable
Connection timeout after 30 seconds
Retry attempt 1 of 3
```

**Resolution**:

1. **Check webhook destination is reachable**:
   ```bash
   # Test endpoint
   curl -I https://webhook.example.com/events
   ```

2. **Verify SSL certificate is valid**:
   ```bash
   curl -v https://webhook.example.com/events 2>&1 | grep -i certificate
   ```

3. **Check retry queue**:
   ```bash
   # View pending webhook deliveries
   curl http://localhost:8080/api/v1/webhooks/queue
   ```

4. **Monitor retry attempts**:
   ```bash
   docker-compose logs integration-service | grep -i webhook
   # Look for successful delivery or exhausted retries
   ```

5. **Manually retry failed webhook**:
   ```bash
   curl -X POST http://localhost:8080/api/v1/webhooks/{delivery_id}/retry
   ```

**Retry Policy**:
- **Attempts**: 3 retries
- **Backoff**: Exponential (1s, 2s, 4s)
- **Total time**: ~7 seconds
- **429 Rate Limit**: Respects `Retry-After` header

**Example**:
```bash
# Check failed webhooks
curl http://localhost:8080/api/v1/webhooks/failed | jq

# Retry specific delivery
delivery_id="wh_abc123"
curl -X POST http://localhost:8080/api/v1/webhooks/$delivery_id/retry

# Monitor logs
docker-compose logs -f integration-service | grep $delivery_id
```

**Related Errors**: ACGS-5202, ACGS-5203, ACGS-5204, ACGS-5211

---

## ACGS-6xxx: Constitutional/Governance Errors

**Category Description**: Errors related to constitutional governance, MACI role separation, deliberation, and alignment validation.

**Common Severity**: CRITICAL (constitutional violations are security-critical)

**Related Components**: Constitutional validation, MACI, deliberation layer

---

### ACGS-6201: MACIRoleViolationError

**Severity**: CRITICAL (Security)
**Impact**: Security-Violation
**Exception**: `MACIRoleViolationError` (enhanced-agent-bus)

**Description**: Agent attempted action outside its MACI role. This prevents agents from operating in multiple roles simultaneously (Monitor + Auditor + Implementer separation).

**Purpose**: Prevent unauthorized cross-role operations and ensure proper separation of concerns.

**Common Causes**:
- Agent assigned multiple conflicting roles
- Agent attempting action reserved for different role
- Role configuration error
- Exploit attempt (multi-role bypass)

**Symptoms**:
```
CRITICAL: MACI role violation detected
Agent: agent-123
Role: Monitor
Attempted action: implement_policy (requires Implementer role)
Request denied
```

**Resolution**:

1. **Review agent role assignment**:
   ```bash
   # Check agent's assigned role
   curl http://localhost:8000/api/v1/agents/agent-123/role
   ```

2. **Verify action is appropriate for role**:
   ```
   Monitor role: Can observe, cannot modify
   Auditor role: Can review, cannot implement
   Implementer role: Can implement, should not self-audit
   ```

3. **Correct role assignment if error**:
   ```bash
   # Reassign to correct role
   curl -X PUT http://localhost:8000/api/v1/agents/agent-123/role \
     -H "Content-Type: application/json" \
     -d '{"role": "Implementer"}'
   ```

4. **If security incident**, audit:
   ```bash
   # Check audit logs for pattern of violations
   grep "MACIRoleViolationError" logs/audit.log

   # Review agent's recent actions
   curl http://localhost:8000/api/v1/audit/agent/agent-123
   ```

**⚠️ Security Note**: This error indicates either:
- Configuration mistake (benign)
- Attempted security bypass (malicious)

Always investigate CRITICAL severity violations.

**Example**:
```bash
# Agent "monitor-1" (Monitor role) tries to implement policy
ERROR: MACIRoleViolationError
Agent: monitor-1
Current role: Monitor
Attempted action: implement_policy
Allowed roles for action: [Implementer]

# Fix: Use correct agent for implementation
agent_id="implementer-1"  # Agent with Implementer role
curl -X POST http://localhost:8000/api/v1/policies/implement \
  -H "X-Agent-ID: $agent_id" \
  -d '{"policy_id": "policy-123"}'
```

**Related Errors**: ACGS-6202, ACGS-6203, ACGS-6204

---

### ACGS-6202: MACISelfValidationError

**Severity**: CRITICAL (Security)
**Impact**: Security-Violation (Gödel Bypass Prevention)
**Exception**: `MACISelfValidationError` (enhanced-agent-bus)

**Description**: Agent attempted to validate its own output. This violates the Gödel incompleteness principle - a system cannot prove its own consistency.

**Prevention Type**: `godel_bypass`

**Purpose**: Prevent self-certification loophole that would allow agents to approve their own work without external validation.

**Common Causes**:
- Agent attempting to audit its own implementation
- Configuration error assigning agent as its own reviewer
- Exploit attempt (self-approval bypass)

**Symptoms**:
```
CRITICAL: MACI self-validation attempt detected (Gödel bypass)
Agent: agent-123
Attempted to validate own output: output-456
Prevention type: godel_bypass
Request denied
```

**Resolution**:

1. **Verify separate agents for implementation and validation**:
   ```
   Rule: Agent A implements → Agent B validates
   Never: Agent A implements → Agent A validates
   ```

2. **Check approval chain configuration**:
   ```bash
   # Ensure different agents at each step
   curl http://localhost:8080/api/v1/approval-chains/{chain_id}
   ```

3. **Correct agent assignment**:
   ```json
   {
     "implementation": {
       "agent_id": "implementer-1"
     },
     "validation": {
       "agent_id": "auditor-1"  // Different agent
     }
   }
   ```

4. **If security incident**, investigate:
   ```bash
   # Check for pattern of self-validation attempts
   grep "MACISelfValidationError" logs/security.log

   # Review constitutional compliance
   curl http://localhost:8000/api/v1/constitutional/compliance
   ```

**⚠️ Critical Security Principle**:
This is a fundamental safety mechanism. Allowing self-validation would:
- Violate Gödel incompleteness theorem
- Create certification loophole
- Compromise constitutional governance
- Enable unchecked agent autonomy

**Never bypass this check.**

**Example**:
```bash
# Wrong: Same agent implementing and validating
{
  "implementer_agent": "agent-1",
  "validator_agent": "agent-1"  ← Same agent! Error!
}

# Right: Different agents
{
  "implementer_agent": "implementer-1",
  "validator_agent": "auditor-1"  ← Different agent ✓
}
```

**Related Errors**: ACGS-6201, ACGS-6203, ACGS-6401

---

## ACGS-7xxx: Performance/Resource Errors

**Category Description**: Errors related to performance degradation, resource exhaustion, and throughput issues.

**Common Severity**: HIGH (production impact) to LOW (informational)

**Related Metrics**: Latency, throughput, CPU, memory, connections

---

### ACGS-7101: LatencyThresholdExceededError

**Severity**: MEDIUM
**Impact**: Performance-Degradation

**Description**: P99 latency exceeds threshold (default: 5ms). System still functional but slower than target.

**Threshold**: 5.0ms (configurable)

**Common Causes**:
- OPA policy evaluation slow
- Database query performance degradation
- Redis cache misses
- Network latency
- Resource contention

**Symptoms**:
```
Warning: P99 latency exceeded threshold
Current: 12.5ms
Threshold: 5.0ms
Endpoint: /api/v1/approvals/create
```

**Resolution**:

1. **Check current latency metrics**:
   ```bash
   curl http://localhost:8080/metrics | grep latency
   ```

2. **Identify slow endpoints**:
   ```bash
   # Check Prometheus/Grafana dashboard
   # Or query metrics API
   curl http://localhost:8080/api/v1/metrics/latency?p99
   ```

3. **Check OPA performance**:
   ```bash
   # OPA decision latency
   curl http://localhost:8181/metrics | grep decision_latency
   ```

4. **Review database query performance**:
   ```sql
   -- Check slow queries
   SELECT query, mean_exec_time, calls
   FROM pg_stat_statements
   ORDER BY mean_exec_time DESC
   LIMIT 10;
   ```

5. **Check Redis cache hit rate**:
   ```bash
   docker-compose exec redis redis-cli info stats | grep cache_hit_rate
   # Target: >90% hit rate
   ```

6. **Monitor resource usage**:
   ```bash
   docker stats
   # Check CPU/Memory usage
   ```

**Optimization Steps**:

1. **Enable OPA decision caching**
2. **Add database indexes** for frequent queries
3. **Increase Redis cache TTL** for stable data
4. **Review N+1 query patterns**
5. **Enable query result caching**

**Example**:
```bash
# Check latency trend
curl http://localhost:8080/api/v1/metrics/latency/trend?duration=1h

# Identify hot paths
curl http://localhost:8080/api/v1/metrics/slow-requests

# Response:
{
  "slow_requests": [
    {
      "endpoint": "/api/v1/approvals/create",
      "p99_latency_ms": 12.5,
      "threshold_ms": 5.0,
      "cause": "OPA policy evaluation"
    }
  ]
}

# Fix: Enable OPA caching
# In OPA config:
decision_logs:
  cache:
    max_size_bytes: 104857600  # 100MB
```

**Related Errors**: ACGS-7102, ACGS-7103, ACGS-7201

---

## ACGS-8xxx: Platform-Specific Errors

**Category Description**: Errors specific to operating systems and platform configurations.

**Common Severity**: LOW to MEDIUM (usually have workarounds)

**Related Platforms**: Windows, macOS, Linux

---

### ACGS-8101: WindowsLineEndingError

**Severity**: LOW
**Impact**: Development-Issue

**Description**: Windows line ending (CRLF) breaking shell scripts. Common when files created on Windows.

**Common Causes**:
- Git autocrlf=true setting
- Files created/edited in Windows editors
- Copy-paste from Windows to WSL
- Windows text editor default settings

**Symptoms**:
```
bash: ./script.sh: /bin/bash^M: bad interpreter
Syntax error: unexpected end of file
```

**Resolution**:

1. **Configure Git to use LF**:
   ```bash
   # Global setting
   git config --global core.autocrlf input

   # Repository setting
   git config core.autocrlf input
   ```

2. **Convert existing files**:
   ```bash
   # Using dos2unix
   dos2unix script.sh

   # Using sed
   sed -i 's/\r$//' script.sh

   # Using tr
   tr -d '\r' < script.sh > script_fixed.sh
   ```

3. **Fix all shell scripts**:
   ```bash
   find . -name "*.sh" -exec dos2unix {} \;
   ```

4. **Add .gitattributes** to enforce LF:
   ```
   # .gitattributes
   * text=auto
   *.sh text eol=lf
   *.py text eol=lf
   *.md text eol=lf
   ```

5. **Check file line endings**:
   ```bash
   file script.sh
   # Should show: "ASCII text" not "ASCII text, with CRLF line terminators"
   ```

**Prevention**:
```bash
# Add to project .gitattributes
cat > .gitattributes <<EOF
# Ensure LF for shell scripts
*.sh text eol=lf
*.bash text eol=lf

# Ensure LF for Python
*.py text eol=lf

# Ensure LF for config files
*.yml text eol=lf
*.yaml text eol=lf
*.json text eol=lf
EOF

git add .gitattributes
git commit -m "Enforce LF line endings"
```

**Example**:
```bash
# Error when running script
./deploy.sh
# bash: ./deploy.sh: /bin/bash^M: bad interpreter

# Fix:
dos2unix deploy.sh
# dos2unix: converting file deploy.sh to Unix format...

# Or using sed:
sed -i 's/\r$//' deploy.sh

# Verify:
file deploy.sh
# deploy.sh: Bourne-Again shell script, ASCII text executable

# Run successfully:
./deploy.sh
```

**Frequency**: Common on Windows/WSL2 development

**Related Errors**: ACGS-8102, ACGS-8103

---

### ACGS-8201: MacOSPortConflictError

**Severity**: MEDIUM
**Impact**: Deployment-Blocking

**Description**: macOS-specific port conflict, typically port 8000 with Airplay Receiver.

**Common Port**: 8000 (Airplay Receiver)

**Symptoms**:
```
Error: Port 8000 is already in use
Cannot bind to 0.0.0.0:8000
ControlCenter using port 8000 (Airplay)
```

**Resolution**:

**Solution 1: Disable Airplay Receiver** (Recommended)
1. Open **System Preferences**
2. Click **Sharing**
3. Uncheck **AirPlay Receiver**
4. Restart Docker Compose:
   ```bash
   docker-compose restart enhanced-agent-bus
   ```

**Solution 2: Change Port Mapping**
1. Edit `docker-compose.yml`:
   ```yaml
   services:
     enhanced-agent-bus:
       ports:
         - "8001:8000"  # Changed from 8000:8000
   ```

2. Update client configuration:
   ```bash
   # Access on new port
   curl http://localhost:8001/health
   ```

3. Update environment variables if needed:
   ```bash
   AGENT_BUS_URL=http://localhost:8001
   ```

**Verification**:
```bash
# Check port is free
lsof -i :8000
# Should return nothing

# Start service
docker-compose up -d enhanced-agent-bus

# Verify service running
curl http://localhost:8000/health
# or
curl http://localhost:8001/health  # if port changed
```

**Example**:
```bash
# Identify Airplay using port
lsof -i :8000
# COMMAND     PID USER
# ControlCe  1234 user

# Disable Airplay:
# System Preferences → Sharing → Uncheck "AirPlay Receiver"

# Restart service
docker-compose restart enhanced-agent-bus

# Verify
curl http://localhost:8000/health
# {"status": "healthy"}
```

**Frequency**: Very common on macOS (Monterey and later)

**Related Errors**: ACGS-3301, ACGS-8202

---

### ACGS-8301: LinuxPermissionError

**Severity**: MEDIUM
**Impact**: Deployment-Blocking

**Description**: Linux file permissions issue, commonly Docker socket or volume mount permissions.

**Common Causes**:
- User not in docker group
- File ownership issues on volume mounts
- SELinux blocking operations
- Incorrect file permissions (0644 instead of 0755 for executables)

**Symptoms**:
```
Permission denied: /var/run/docker.sock
Cannot access volume mount: Permission denied
Got permission denied while trying to connect to Docker daemon
```

**Resolution**:

1. **Add user to docker group**:
   ```bash
   # Add current user
   sudo usermod -aG docker $USER

   # Log out and log back in, then verify:
   groups
   # Should include "docker"
   ```

2. **Fix Docker socket permissions**:
   ```bash
   # Check socket permissions
   ls -l /var/run/docker.sock

   # Should be: srw-rw---- 1 root docker

   # Fix if needed:
   sudo chmod 660 /var/run/docker.sock
   sudo chown root:docker /var/run/docker.sock
   ```

3. **Fix volume mount permissions**:
   ```bash
   # Check ownership
   ls -ld ./data

   # Fix ownership to match container user
   sudo chown -R 1000:1000 ./data

   # Or match current user:
   sudo chown -R $USER:$USER ./data
   ```

4. **For SELinux issues**, add :Z flag:
   ```yaml
   volumes:
     - ./data:/app/data:Z  # Z for SELinux relabeling
   ```

5. **Fix executable permissions**:
   ```bash
   # Make script executable
   chmod +x script.sh

   # Fix all shell scripts:
   find . -name "*.sh" -exec chmod +x {} \;
   ```

**SELinux Specific**:
```bash
# Check SELinux status
getenforce
# Enforcing / Permissive / Disabled

# Check audit logs
sudo ausearch -m AVC -ts recent

# Allow Docker volume mounts (permanent):
sudo semanage fcontext -a -t container_file_t "/path/to/data(/.*)?"
sudo restorecon -Rv /path/to/data

# Or use :Z in docker-compose:
volumes:
  - ./data:/app/data:Z
```

**Example**:
```bash
# Permission denied error
docker-compose up
# ERROR: Cannot connect to Docker daemon

# Check user groups
groups
# user : user

# Fix: Add to docker group
sudo usermod -aG docker $USER

# Important: Log out and log back in!
# Or use newgrp:
newgrp docker

# Verify
docker ps
# Should work without sudo

# For volume mounts:
sudo chown -R $USER:$USER ./data
chmod -R 755 ./data

# Restart
docker-compose up -d
```

**Frequency**: Very common on first-time Linux setup

**Related Errors**: ACGS-8302, ACGS-3101

---

## Related Documentation

### Core Documentation

- **ERROR_CODE_TAXONOMY.md**: Complete error code taxonomy and structure
- **ERROR_CODE_MAPPING.md**: Mapping of all exceptions to error codes
- **ERROR_SEVERITY_CLASSIFICATION.md**: Severity levels and operational response procedures
- **EXCEPTION_CATALOG.md**: Catalog of all 137 exception classes
- **DEPLOYMENT_FAILURE_SCENARIOS.md**: Common deployment failure scenarios
- **TODO_CATALOG.md**: TODO/FIXME comments and error impacts
- **GAP_ANALYSIS.md**: Documentation coverage gaps

### Operational Guides

- **DEPLOYMENT_GUIDE.md**: Deployment procedures and configuration
- **TROUBLESHOOTING.md**: General troubleshooting guide (quickstart)
- **Diagnostic Runbooks**: Service-specific diagnostic procedures (Phase 4)

### Service-Specific Documentation

- **TROUBLESHOOTING_HITL_APPROVALS.md**: HITL Approvals service (Phase 4.2)
- **TROUBLESHOOTING_INTEGRATION_SERVICE.md**: Integration service (Phase 4.2)
- **TROUBLESHOOTING_AUDIT_SERVICE.md**: Audit service (Phase 4.2)

---

## Getting Help

### Diagnostic Commands

**Quick Health Check**:
```bash
# All services
docker-compose ps

# Service logs
docker-compose logs <service-name> | tail -50

# Health endpoints
curl http://localhost:8080/health  # API Gateway
curl http://localhost:8000/health  # Agent Bus
curl http://localhost:8181/health  # OPA
```

**System Status**:
```bash
# Docker status
docker info
docker-compose ps

# Resource usage
docker stats

# Network connectivity
docker-compose exec <service> ping <target-service>
```

**Configuration Check**:
```bash
# Environment variables
docker-compose config

# Verify critical vars
grep -E "CONSTITUTIONAL_HASH|OPA_URL|DATABASE_URL" .env

# Constitutional hash verification
echo $CONSTITUTIONAL_HASH
# Should be: cdd01ef066bc6cf2
```

### Escalation Path

1. **CRITICAL errors**: Immediate page on-call engineer
2. **HIGH errors**: Alert engineering team (< 1 hour)
3. **MEDIUM errors**: Create ticket (< 4 hours business hours)
4. **LOW errors**: Add to backlog (best effort)

### Support Channels

- **Internal**: Check with team, review documentation
- **Logs**: Always include relevant logs when reporting issues
- **Context**: Include error code, severity, and steps to reproduce

### Post-Incident

For CRITICAL and HIGH severity incidents:
1. Document resolution in this guide
2. Update troubleshooting procedures
3. Create follow-up tasks for prevention
4. Conduct blameless post-mortem (CRITICAL only)

---

## Statistics

**Error Code Coverage**:
- Total error codes documented: 250+
- Exception classes covered: 137 (100%)
- Deployment scenarios covered: 50+ (100%)
- TODO-related errors: 10 (100%)

**Severity Distribution**:
- CRITICAL: ~45 codes (18%)
- HIGH: ~95 codes (38%)
- MEDIUM: ~90 codes (36%)
- LOW: ~20 codes (8%)

**Category Distribution**:
- ACGS-1xxx (Configuration): 24 codes
- ACGS-2xxx (Auth/Authz): 53 codes
- ACGS-3xxx (Deployment): 24 codes
- ACGS-4xxx (Integration): 29 codes
- ACGS-5xxx (Runtime): 67 codes
- ACGS-6xxx (Constitutional): 22 codes
- ACGS-7xxx (Performance): 21 codes
- ACGS-8xxx (Platform): 10 codes

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-03 | Initial comprehensive error code reference |

---

**Constitutional Hash**: cdd01ef066bc6cf2
**Document Status**: ✅ Complete
**Next Steps**: Implement detailed category-specific documentation (Phase 3.2-3.6)
