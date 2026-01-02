# ACGS-2 Troubleshooting Guide

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

> **Version**: 1.0.0
> **Last Updated**: 2025-01-02
> **Purpose**: Comprehensive troubleshooting for common ACGS-2 issues

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Docker and Container Issues](#docker-and-container-issues)
3. [OPA (Policy Engine) Issues](#opa-policy-engine-issues)
4. [Agent Bus Issues](#agent-bus-issues)
5. [Redis Issues](#redis-issues)
6. [Kafka Issues](#kafka-issues)
7. [Network and Port Issues](#network-and-port-issues)
8. [Policy and Rego Issues](#policy-and-rego-issues)
9. [Configuration Issues](#configuration-issues)
10. [Platform-Specific Issues](#platform-specific-issues)
11. [Performance Issues](#performance-issues)
12. [Getting Help](#getting-help)

---

## Quick Diagnostics

### Automated Health Check

Run this comprehensive diagnostic script to quickly identify issues:

```bash
#!/bin/bash
# ACGS-2 Diagnostic Script
# Save as: diagnose.sh
# Run with: bash diagnose.sh

set -e

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║               ACGS-2 Diagnostic Report                           ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "Generated: $(date)"
echo ""

# Function to check service
check_service() {
    local name=$1
    local url=$2
    local expected=$3

    printf "%-20s" "$name:"
    if response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null); then
        if [ "$response" == "$expected" ]; then
            echo "✅ OK (HTTP $response)"
            return 0
        else
            echo "⚠️  Unexpected (HTTP $response)"
            return 1
        fi
    else
        echo "❌ Not responding"
        return 1
    fi
}

echo "=== Docker Status ==="
if docker info > /dev/null 2>&1; then
    echo "Docker daemon:      ✅ Running"
    echo "Docker version:     $(docker --version | cut -d' ' -f3 | tr -d ',')"
    echo "Compose version:    $(docker compose version --short 2>/dev/null || echo 'N/A')"
else
    echo "Docker daemon:      ❌ Not running"
    echo ""
    echo "FIX: Start Docker Desktop or run 'sudo systemctl start docker'"
    exit 1
fi

echo ""
echo "=== Container Status ==="
docker compose -f docker-compose.dev.yml ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "No containers found"

echo ""
echo "=== Service Health ==="
check_service "OPA" "http://localhost:8181/health" "200" || true
check_service "Agent Bus" "http://localhost:8000/health" "200" || true
check_service "API Gateway" "http://localhost:8080/health" "200" || true

echo ""
echo "=== Port Availability ==="
for port in 8181 8000 8080 6379 19092 2181; do
    if lsof -i :$port > /dev/null 2>&1; then
        printf "Port %-5s: ✅ In use\n" "$port"
    else
        printf "Port %-5s: ⚠️  Not bound\n" "$port"
    fi
done

echo ""
echo "=== Resource Usage ==="
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null || echo "No stats available"

echo ""
echo "=== Recent Errors (last 10 lines per service) ==="
for service in opa redis kafka agent-bus api-gateway; do
    echo "--- $service ---"
    docker compose -f docker-compose.dev.yml logs --tail=10 "$service" 2>/dev/null | grep -i "error\|fail\|exception" | tail -5 || echo "No errors found"
done

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    Diagnostic Complete                           ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
```

### Quick Status Check

For a quick status check, run:

```bash
# Check if all containers are running
docker compose -f docker-compose.dev.yml ps

# Check service health
curl -s http://localhost:8181/health && echo "OPA: OK"
curl -s http://localhost:8000/health && echo "Agent Bus: OK"
```

---

## Docker and Container Issues

### Docker Daemon Not Running

**Symptoms:**
- `Cannot connect to the Docker daemon`
- `Error response from daemon: Bad response from Docker engine`

**Solutions:**

```bash
# Linux
sudo systemctl start docker
sudo systemctl enable docker  # Start on boot

# macOS / Windows
# Open Docker Desktop application

# Verify Docker is running
docker info
```

### Container Fails to Start

**Symptoms:**
- Container status shows "Exited" or "Restarting"
- Health check fails

**Diagnosis:**

```bash
# Check container logs
docker compose -f docker-compose.dev.yml logs <service-name>

# Check container status
docker compose -f docker-compose.dev.yml ps

# Inspect container
docker inspect <container-id>
```

**Common Causes and Fixes:**

| Cause | Fix |
|-------|-----|
| Missing environment variables | Check `.env` file exists and is complete |
| Port conflict | Change ports in `.env` or stop conflicting service |
| Volume mount error | Check paths exist and have correct permissions |
| Image not found | Run `docker compose pull` to update images |
| Out of memory | Increase Docker memory allocation |

### Container Keeps Restarting

**Diagnosis:**

```bash
# Watch container logs in real-time
docker compose -f docker-compose.dev.yml logs -f <service-name>

# Check restart count
docker inspect --format='{{.RestartCount}}' <container-id>

# Check exit code
docker inspect --format='{{.State.ExitCode}}' <container-id>
```

**Common Exit Codes:**

| Exit Code | Meaning | Solution |
|-----------|---------|----------|
| 0 | Normal exit | Check if service should stay running |
| 1 | Application error | Check logs for error message |
| 137 | OOM killed | Increase memory allocation |
| 143 | SIGTERM received | Check if another process is killing it |

### Image Pull Failures

**Symptoms:**
- `Error pulling image`
- `manifest unknown`

**Solutions:**

```bash
# Check internet connection
ping hub.docker.com

# Manually pull images
docker pull openpolicyagent/opa:latest
docker pull redis:7-alpine
docker pull confluentinc/cp-kafka:7.4.0

# If behind proxy, configure Docker proxy
# Edit ~/.docker/config.json
```

---

## OPA (Policy Engine) Issues

### OPA Not Responding

**Symptoms:**
- `Connection refused` when querying http://localhost:8181
- `curl: (7) Failed to connect to localhost port 8181`

**Diagnosis:**

```bash
# Check if OPA container is running
docker compose -f docker-compose.dev.yml ps opa

# Check OPA logs
docker compose -f docker-compose.dev.yml logs opa

# Test from inside Docker network
docker exec -it acgs2-agent-bus-1 curl http://opa:8181/health
```

**Solutions:**

```bash
# Restart OPA
docker compose -f docker-compose.dev.yml restart opa

# If policies are corrupt, rebuild
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up -d opa

# Check policy volume mount
docker compose -f docker-compose.dev.yml exec opa ls -la /policies
```

### Policy Query Returns `undefined`

**Symptoms:**
- Query returns `{"result": undefined}` or empty result
- No error message but no decision

**Common Causes:**

1. **Wrong policy path**
   ```bash
   # List available policies
   curl -s http://localhost:8181/v1/policies | python3 -m json.tool

   # Correct path format: package.name/rule
   # If package is "acgs.constitutional" and rule is "allow"
   # Query: /v1/data/acgs/constitutional/allow
   ```

2. **Missing input**
   ```bash
   # Wrong: no input wrapper
   curl -X POST http://localhost:8181/v1/data/acgs/constitutional/allow \
     -d '{"constitutional_hash": "xyz"}'

   # Correct: input wrapper required
   curl -X POST http://localhost:8181/v1/data/acgs/constitutional/allow \
     -d '{"input": {"constitutional_hash": "xyz"}}'
   ```

3. **Policy not loaded**
   ```bash
   # Check if policy file is in volume
   docker exec -it acgs2-opa-1 cat /policies/constitutional.rego
   ```

### Policy Syntax Errors

**Symptoms:**
- OPA fails to start
- `rego_parse_error` in logs

**Diagnosis:**

```bash
# Validate policy syntax
docker run --rm -v $(pwd)/policies:/policies openpolicyagent/opa:latest check /policies/

# Or use the built-in OPA test
docker run --rm -v $(pwd)/policies:/policies openpolicyagent/opa:latest test /policies/
```

**Common Syntax Issues:**

| Issue | Example | Fix |
|-------|---------|-----|
| Missing package | `allow { ... }` | Add `package mypolicy` at top |
| Wrong assignment | `allow = true` | Use `allow := true` for rules |
| Unclosed brace | `allow { input.x` | Add closing `}` |
| String in rule body | `allow { "yes" }` | Use boolean: `allow { true }` |

### OPA High Memory Usage

**Symptoms:**
- OPA container using excessive memory
- OOM kills

**Solutions:**

```bash
# Check memory usage
docker stats acgs2-opa-1

# Limit OPA memory in docker-compose
# Add to opa service:
#   mem_limit: 512m
#   memswap_limit: 512m

# Clear OPA decision cache
curl -X DELETE http://localhost:8181/v1/data/system/bundles
```

---

## Agent Bus Issues

### Agent Bus Not Starting

**Symptoms:**
- Agent Bus container exits immediately
- Port 8000 not accessible

**Diagnosis:**

```bash
# Check logs for Python errors
docker compose -f docker-compose.dev.yml logs agent-bus

# Common issues:
# - ImportError: module not found
# - Environment variable missing
# - Port already in use
```

**Solutions:**

```bash
# Ensure dependencies are satisfied
docker compose -f docker-compose.dev.yml up -d opa redis kafka

# Check environment variables
docker compose -f docker-compose.dev.yml config | grep agent-bus -A 30

# Rebuild if code changed
docker compose -f docker-compose.dev.yml build agent-bus
docker compose -f docker-compose.dev.yml up -d agent-bus
```

### Constitutional Validation Failing

**Symptoms:**
- All requests return `false` or rejected
- Logs show "Constitutional hash mismatch"

**Fix:**

```bash
# Verify constitutional hash in .env
grep CONSTITUTIONAL_HASH .env

# Should be: CONSTITUTIONAL_HASH=cdd01ef066bc6cf2

# If wrong, fix and restart
echo "CONSTITUTIONAL_HASH=cdd01ef066bc6cf2" >> .env
docker compose -f docker-compose.dev.yml restart agent-bus
```

### Connection to OPA Failing

**Symptoms:**
- Agent Bus logs show OPA connection errors
- Governance decisions failing

**Diagnosis:**

```bash
# Check Agent Bus can reach OPA
docker exec -it acgs2-agent-bus-1 curl http://opa:8181/health

# Check environment variable
docker exec -it acgs2-agent-bus-1 env | grep OPA_URL
```

**Fix:**

```bash
# Ensure OPA_URL uses Docker network name (not localhost)
# In .env:
OPA_URL=http://opa:8181  # Correct for Docker
# NOT: OPA_URL=http://localhost:8181
```

---

## Redis Issues

### Redis Connection Refused

**Symptoms:**
- `ConnectionRefusedError: Redis`
- `Could not connect to Redis`

**Diagnosis:**

```bash
# Check Redis is running
docker compose -f docker-compose.dev.yml ps redis

# Test Redis connection
docker exec -it acgs2-redis-1 redis-cli -a dev_password ping
```

**Solutions:**

```bash
# Restart Redis
docker compose -f docker-compose.dev.yml restart redis

# Check Redis logs
docker compose -f docker-compose.dev.yml logs redis

# Verify password matches
grep REDIS_PASSWORD .env
```

### Redis Authentication Failed

**Symptoms:**
- `NOAUTH Authentication required`
- `invalid password`

**Fix:**

```bash
# Ensure password is consistent
# In .env:
REDIS_PASSWORD=dev_password
REDIS_URL=redis://:dev_password@redis:6379/0

# Restart all services
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up -d
```

---

## Kafka Issues

### Kafka Not Ready

**Symptoms:**
- `Kafka broker not available`
- Messages not being published

**Diagnosis:**

```bash
# Check Kafka and Zookeeper status
docker compose -f docker-compose.dev.yml ps kafka zookeeper

# Check Kafka logs
docker compose -f docker-compose.dev.yml logs kafka

# List topics
docker exec -it acgs2-kafka-1 kafka-topics --list --bootstrap-server localhost:19092
```

**Solutions:**

```bash
# Restart Kafka (and Zookeeper)
docker compose -f docker-compose.dev.yml restart zookeeper kafka

# If corrupt, recreate
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up -d
```

### Kafka Connection From Host

**Note:** Kafka uses different listeners for internal (Docker) and external (host) access.

```bash
# From host machine:
KAFKA_BOOTSTRAP=localhost:19092

# From inside Docker container:
KAFKA_BOOTSTRAP=kafka:29092
```

---

## Network and Port Issues

### Port Already in Use

**Symptoms:**
- `Bind for 0.0.0.0:8181 failed: port is already allocated`

**Diagnosis:**

```bash
# Find what's using the port
# Linux/macOS:
lsof -i :8181
netstat -tulpn | grep 8181

# Windows:
netstat -ano | findstr 8181
```

**Solutions:**

```bash
# Option 1: Stop the conflicting service
kill <pid>  # Linux/macOS
taskkill /PID <pid> /F  # Windows

# Option 2: Change the port in .env
# Add to .env:
OPA_PORT=8182

# Update docker-compose.dev.yml to use the variable
# ports:
#   - "${OPA_PORT:-8181}:8181"
```

### Cannot Access Services from Host

**Symptoms:**
- Services work inside Docker but not from host
- `Connection refused` from browser

**Diagnosis:**

```bash
# Check port bindings
docker compose -f docker-compose.dev.yml port opa 8181

# Test from inside container
docker exec -it acgs2-agent-bus-1 curl http://opa:8181/health
```

**Solutions:**

```bash
# Ensure ports are exposed in docker-compose
# ports:
#   - "8181:8181"  # Host:Container

# Check firewall (Linux)
sudo ufw allow 8181
```

---

## Policy and Rego Issues

### Rego Compilation Errors

**Common Errors and Fixes:**

| Error | Cause | Fix |
|-------|-------|-----|
| `rego_parse_error: unexpected token` | Syntax error | Check braces, quotes, operators |
| `rego_type_error: undefined ref` | Missing import | Add `import rego.v1` or check path |
| `rego_unsafe_var_error` | Unbound variable | Ensure variable is defined |

**Validate Before Deploying:**

```bash
# Check syntax
docker run --rm -v $(pwd)/policies:/policies \
  openpolicyagent/opa:latest check /policies/

# Run tests
docker run --rm -v $(pwd)/policies:/policies \
  openpolicyagent/opa:latest test /policies/

# Format policies
docker run --rm -v $(pwd)/policies:/policies \
  openpolicyagent/opa:latest fmt -w /policies/
```

### Policy Returns Wrong Result

**Debugging Steps:**

```bash
# 1. Enable trace
curl -X POST http://localhost:8181/v1/data/acgs/constitutional/allow?explain=full \
  -d '{"input": {"constitutional_hash": "xyz"}}' | python3 -m json.tool

# 2. Check intermediate values
curl -X POST http://localhost:8181/v1/data/acgs/constitutional \
  -d '{"input": {"constitutional_hash": "xyz"}}' | python3 -m json.tool

# 3. Use OPA playground for testing
# https://play.openpolicyagent.org/
```

---

## Configuration Issues

### Missing Environment Variables

**Symptoms:**
- `ValidationError: field required`
- Service fails to start with config error

**Diagnosis:**

```bash
# Check what's in .env
cat .env

# Check what Docker Compose sees
docker compose -f docker-compose.dev.yml config

# Check inside container
docker exec -it acgs2-agent-bus-1 env
```

**Fix:**

```bash
# Reset to defaults
cp .env.dev .env

# Or add missing variables
cat >> .env << EOF
REDIS_URL=redis://redis:6379/0
OPA_URL=http://opa:8181
CONSTITUTIONAL_HASH=cdd01ef066bc6cf2
EOF
```

### Wrong URL Scheme (Docker vs Host)

**Problem:** Using `localhost` inside Docker containers.

| Context | Use |
|---------|-----|
| Host machine | `http://localhost:8181` |
| Inside Docker | `http://opa:8181` |
| docker-compose.yml | `http://opa:8181` |
| From browser | `http://localhost:8181` |

---

## Platform-Specific Issues

### Windows Issues

**WSL2 Recommended:**

```powershell
# Enable WSL2
wsl --install

# Use WSL2 backend in Docker Desktop
# Settings > General > Use the WSL 2 based engine
```

**Path Issues:**

```bash
# Use Unix-style paths in WSL2
cd /mnt/c/Users/yourname/projects/acgs2

# Or use Windows paths in PowerShell
cd C:\Users\yourname\projects\acgs2
```

**Line Ending Issues:**

```bash
# Configure Git to use LF
git config --global core.autocrlf input

# Fix existing files
dos2unix .env
```

### macOS Issues

**Docker Desktop Memory:**

```bash
# Increase memory allocation
# Docker Desktop > Settings > Resources > Memory: 4GB+
```

**Port 8000 Conflict:**

```bash
# Check what's using port 8000
lsof -i :8000

# Common culprits: Airplay Receiver
# Disable in System Preferences > Sharing > Airplay Receiver
```

### Linux Issues

**Docker Permission Denied:**

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in, or:
newgrp docker
```

**SELinux Issues:**

```bash
# If using SELinux, add :Z to volume mounts
# volumes:
#   - ./policies:/policies:ro,Z
```

---

## Performance Issues

### Slow Policy Evaluation

**Diagnosis:**

```bash
# Measure query time
time curl -s -X POST http://localhost:8181/v1/data/acgs/constitutional/allow \
  -d '{"input": {"constitutional_hash": "cdd01ef066bc6cf2", "tenant_id": "t1", "features": []}}' > /dev/null

# Check OPA metrics
curl -s http://localhost:8181/metrics | grep opa_
```

**Optimizations:**

- Use partial evaluation for complex policies
- Enable decision caching
- Reduce policy complexity
- Use indexed rules

### High Memory Usage

**Diagnosis:**

```bash
# Check container stats
docker stats --no-stream

# Check specific container
docker exec -it acgs2-agent-bus-1 ps aux
```

**Solutions:**

```bash
# Limit container memory
# In docker-compose.dev.yml:
services:
  agent-bus:
    mem_limit: 512m

# Clear caches
curl -X DELETE http://localhost:8181/v1/data/system/bundles
```

---

## Getting Help

### Log Collection

Before asking for help, collect these logs:

```bash
# Collect all logs
docker compose -f docker-compose.dev.yml logs > acgs2_logs.txt 2>&1

# Collect diagnostic info
bash diagnose.sh > diagnostic_report.txt 2>&1

# Include configuration (remove secrets!)
docker compose -f docker-compose.dev.yml config > compose_config.txt
```

### Where to Get Help

| Resource | When to Use |
|----------|-------------|
| [GitHub Issues](https://github.com/ACGS-Project/ACGS-2/issues) | Bug reports, feature requests |
| [Community Forum](https://forum.acgs2.org) | General questions, discussions |
| [Stack Overflow](https://stackoverflow.com/questions/tagged/acgs2) | Specific technical questions |
| [Enterprise Support](mailto:enterprise@acgs2.org) | Production issues, SLA support |

### Issue Template

When reporting issues, include:

```markdown
## Environment
- OS: [e.g., Ubuntu 22.04, macOS 14, Windows 11]
- Docker version: [output of `docker --version`]
- Docker Compose version: [output of `docker compose version`]

## Description
[Clear description of the issue]

## Steps to Reproduce
1. [First step]
2. [Second step]
3. [See error]

## Expected Behavior
[What you expected to happen]

## Actual Behavior
[What actually happened]

## Logs
```
[Relevant log output]
```

## Screenshots
[If applicable]
```

---

## Appendix: Error Reference

### Exit Codes

| Code | Name | Description |
|------|------|-------------|
| 0 | SUCCESS | Normal exit |
| 1 | GENERAL | General error |
| 2 | MISUSE | Shell command misuse |
| 126 | CANNOTEXEC | Command cannot execute |
| 127 | NOTFOUND | Command not found |
| 128+N | SIGNAL | Killed by signal N |
| 137 | SIGKILL | OOM or manual kill |
| 143 | SIGTERM | Graceful termination |

### HTTP Status Codes

| Code | Meaning | ACGS-2 Context |
|------|---------|----------------|
| 200 | OK | Request successful |
| 400 | Bad Request | Invalid input |
| 401 | Unauthorized | Auth required |
| 403 | Forbidden | Policy denied |
| 404 | Not Found | Policy/resource missing |
| 429 | Too Many Requests | Rate limited |
| 500 | Server Error | Internal error |
| 502 | Bad Gateway | Service unavailable |
| 503 | Service Unavailable | OPA/Agent Bus down |

---

**Constitutional Hash**: `cdd01ef066bc6cf2`
**Version**: 1.0.0
**Last Updated**: 2025-01-02
