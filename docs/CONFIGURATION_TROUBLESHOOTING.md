# ACGS-2 Configuration Troubleshooting Runbook

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

> **Version**: 1.0.0
> **Last Updated**: 2025-01-02

This runbook helps diagnose and resolve common configuration issues in ACGS-2.

## Quick Diagnostic Commands

```bash
# Validate Python config loading
python -c "from shared.config import settings; print('Config loaded:', settings.env)"

# Check environment file syntax
python -c "from dotenv import dotenv_values; print(dotenv_values('.env'))"

# Verify Docker Compose config
docker compose -f docker-compose.dev.yml config --quiet && echo "Valid"

# Test Redis connection
redis-cli -h localhost -p 6379 ping

# Test OPA connection
curl -s http://localhost:8181/health | jq .
```

---

## Issue: Configuration Import Errors

### Symptom
```
ImportError: No module named 'shared.config'
ModuleNotFoundError: No module named 'shared'
```

### Diagnosis
```bash
# Check if shared module exists
ls -la src/core/shared/config.py

# Check PYTHONPATH
echo $PYTHONPATH
```

### Solution
```bash
# Set PYTHONPATH to include src/core
export PYTHONPATH=/path/to/acgs2/src/core:$PYTHONPATH

# Or run with explicit path
PYTHONPATH=src/core python your_script.py

# For Docker, ensure volume mount includes shared folder
```

---

## Issue: Missing Environment Variables

### Symptom
```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
jwt_secret
  Field required [type=missing]
```

### Diagnosis
```bash
# Check if .env file exists
ls -la .env

# Check specific variable
grep JWT_SECRET .env

# Validate environment file
python -c "
from dotenv import dotenv_values
config = dotenv_values('.env')
required = ['JWT_SECRET', 'REDIS_URL', 'CONSTITUTIONAL_HASH']
for key in required:
    if key not in config:
        print(f'MISSING: {key}')
    else:
        print(f'OK: {key}')
"
```

### Solution
```bash
# Copy development defaults
cp .env.dev .env

# Or set minimum required variables
cat >> .env << 'EOF'
JWT_SECRET=dev-jwt-secret-min-32-chars-required
API_KEY_INTERNAL=dev-api-key-min-32-chars-required
CONSTITUTIONAL_HASH=cdd01ef066bc6cf2
REDIS_URL=redis://localhost:6379/0
EOF
```

---

## Issue: Redis Connection Failed

### Symptom
```
ConnectionRefusedError: [Errno 111] Connection refused
redis.exceptions.ConnectionError: Error 111 connecting to redis:6379
```

### Diagnosis
```bash
# Check if Redis is running
docker ps | grep redis

# Test connection
redis-cli -h localhost -p 6379 ping

# Check environment URL
grep REDIS_URL .env
```

### Solution

**If using Docker:**
```bash
# Start Redis
docker compose -f docker-compose.dev.yml up -d redis

# Check logs
docker compose -f docker-compose.dev.yml logs redis
```

**If running locally:**
```bash
# Update URL to localhost
sed -i 's/redis:6379/localhost:6379/g' .env

# Or set explicitly
export REDIS_URL=redis://localhost:6379/0
```

---

## Issue: OPA Connection Failed

### Symptom
```
aiohttp.client_exceptions.ClientConnectorError: Cannot connect to host opa:8181
requests.exceptions.ConnectionError: HTTPConnectionPool
```

### Diagnosis
```bash
# Check if OPA is running
docker ps | grep opa

# Test health endpoint
curl http://localhost:8181/health

# Check environment URL
grep OPA_URL .env
```

### Solution
```bash
# Start OPA
docker compose -f docker-compose.dev.yml up -d opa

# For local development, update URL
export OPA_URL=http://localhost:8181
```

---

## Issue: Constitutional Hash Mismatch

### Symptom
```
ConstitutionalValidationError: Hash mismatch
Expected: cdd01ef066bc6cf2, Got: [different hash]
```

### Diagnosis
```bash
# Check configured hash
grep CONSTITUTIONAL_HASH .env

# Check in Python config
python -c "from shared.config import settings; print(settings.ai.constitutional_hash)"

# Check code hash
grep -r "cdd01ef066bc6cf2" src/core/shared/config.py
```

### Solution
```bash
# The constitutional hash is IMMUTABLE
# Always use: cdd01ef066bc6cf2

echo "CONSTITUTIONAL_HASH=cdd01ef066bc6cf2" >> .env
```

**IMPORTANT**: The constitutional hash `cdd01ef066bc6cf2` is immutable and must not be changed. If you see a different hash, investigate the source of the change.

---

## Issue: JWT Secret Validation Error

### Symptom
```
ValueError: JWT_SECRET must be at least 32 characters
pydantic_core._pydantic_core.ValidationError: jwt_secret min_length
```

### Diagnosis
```bash
# Check secret length
grep JWT_SECRET .env | wc -c
```

### Solution
```bash
# Generate a proper secret (32+ characters)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Update .env with the generated secret
# JWT_SECRET=your-generated-secret-here
```

---

## Issue: Docker Compose Environment Not Loading

### Symptom
Services start but use default values instead of `.env` file values.

### Diagnosis
```bash
# Check if env_file directive is present
grep "env_file" docker-compose.dev.yml

# Verify variable substitution
docker compose -f docker-compose.dev.yml config | grep REDIS
```

### Solution
```bash
# Use explicit env-file flag
docker compose -f docker-compose.dev.yml --env-file .env.dev up -d

# Or ensure .env is in same directory as docker-compose.yml
cp .env.dev .env
```

---

## Issue: MACI Enforcement Failures

### Symptom
```
MACIEnforcementError: Strict mode requires agent role
AgentPermissionDenied: No role configured for agent
```

### Diagnosis
```bash
# Check MACI configuration
grep MACI .env

# Verify in Python
python -c "from shared.config import settings; print(settings.maci.strict_mode)"
```

### Solution

**Option 1: Disable strict mode for development:**
```bash
echo "MACI_STRICT_MODE=false" >> .env
```

**Option 2: Configure agent roles:**
```bash
cat >> .env << 'EOF'
MACI_STRICT_MODE=true
MACI_AGENT_my_agent=researcher,analyst
MACI_AGENT_other_agent=executor
EOF
```

---

## Issue: Vault Connection Failed

### Symptom
```
hvac.exceptions.VaultError: ConnectionError
vault.VaultError: Unable to connect to Vault
```

### Diagnosis
```bash
# Check Vault configuration
grep VAULT .env

# Test connection
curl http://localhost:8200/v1/sys/health
```

### Solution

**If Vault not required:**
```bash
# Leave VAULT_TOKEN empty (graceful fallback)
echo "VAULT_TOKEN=" >> .env
```

**If Vault required:**
```bash
# Start development Vault
docker run -d --name vault -p 8200:8200 \
  -e 'VAULT_DEV_ROOT_TOKEN_ID=dev-token' \
  vault:latest

# Configure environment
cat >> .env << 'EOF'
VAULT_ADDR=http://localhost:8200
VAULT_TOKEN=dev-token
EOF
```

---

## Issue: Kafka Connection Failed

### Symptom
```
kafka.errors.NoBrokersAvailable: NoBrokersAvailable
KafkaConnectionError: Unable to connect to bootstrap servers
```

### Diagnosis
```bash
# Check Kafka and Zookeeper
docker ps | grep -E "kafka|zookeeper"

# Check bootstrap servers
grep KAFKA_BOOTSTRAP .env
```

### Solution
```bash
# Start Kafka with Zookeeper
docker compose -f docker-compose.dev.yml up -d zookeeper kafka

# Wait for Kafka to be ready
docker compose -f docker-compose.dev.yml logs -f kafka

# For local development
export KAFKA_BOOTSTRAP=localhost:19092
```

---

## Issue: Pydantic-Settings Not Installed

### Symptom
```
ImportError: pydantic-settings is not installed
Using fallback configuration (dataclass)
```

### Diagnosis
```bash
# Check if pydantic-settings is installed
pip list | grep pydantic-settings
```

### Solution
```bash
# Install pydantic-settings
pip install pydantic-settings

# Or install full development dependencies
pip install -e ./src/core[dev]
```

Note: The system includes a dataclass fallback for environments without pydantic-settings, but pydantic-settings is recommended for production.

---

## Validation Checklist

Use this checklist when debugging configuration issues:

- [ ] `.env` file exists and is readable
- [ ] `CONSTITUTIONAL_HASH=cdd01ef066bc6cf2` is set correctly
- [ ] `PYTHONPATH` includes `src/core` directory
- [ ] Required services (Redis, OPA) are running
- [ ] URLs use correct hostnames (localhost vs Docker service names)
- [ ] Secrets meet minimum length requirements (32+ chars)
- [ ] Docker Compose uses `--env-file` flag
- [ ] No syntax errors in `.env` file (no spaces around `=`)

---

## Getting Help

If issues persist after following this runbook:

1. **Check logs**: `docker compose logs -f [service-name]`
2. **Verify config**: `python -c "from shared.config import settings; print(settings.model_dump())"`
3. **Review documentation**: [Development Guide](./DEVELOPMENT.md)
4. **File an issue**: Include config dump (redact secrets) and error messages

---

*Constitutional Hash: cdd01ef066bc6cf2*
