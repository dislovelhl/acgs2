# Cross-Platform Testing Guide

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

> **Version**: 1.0.0
> **Last Updated**: 2025-01-03
> **Purpose**: Cross-platform testing methodology for ACGS-2 Docker Compose setup

## Overview

This guide documents the cross-platform testing methodology for verifying that the ACGS-2 developer onboarding experience works consistently across Linux, macOS, and Windows with Docker Desktop.

## Table of Contents

1. [Platform Requirements](#platform-requirements)
2. [Pre-Flight Checklist](#pre-flight-checklist)
3. [Linux Testing](#linux-testing)
4. [macOS Testing](#macOS-testing)
5. [Windows Testing](#windows-testing)
6. [Cross-Platform Compatibility Notes](#cross-platform-compatibility-notes)
7. [Known Issues and Workarounds](#known-issues-and-workarounds)
8. [Verification Matrix](#verification-matrix)

---

## Platform Requirements

### Minimum Requirements (All Platforms)

| Component | Minimum Version | Recommended |
|-----------|-----------------|-------------|
| Docker | 24.0+ | 25.0+ |
| Docker Compose | 2.20+ | 2.24+ |
| RAM | 4 GB | 8 GB |
| Disk Space | 5 GB | 10 GB |
| Internet | Required for initial pull | N/A |

### Platform-Specific Requirements

#### Linux
- **Distributions**: Ubuntu 20.04+, Debian 11+, Fedora 38+, CentOS Stream 9+
- **Kernel**: 4.18+ (for Docker overlay2 driver)
- **User**: Must be in `docker` group (or run with sudo)

#### macOS
- **Version**: macOS 12 Monterey or newer
- **Chip**: Intel x86_64 or Apple Silicon (ARM64) with Rosetta 2
- **Docker Desktop**: Version 4.25+ recommended

#### Windows
- **Version**: Windows 10 (21H2+) or Windows 11
- **Backend**: WSL 2 (highly recommended) or Hyper-V
- **Docker Desktop**: Version 4.25+ with WSL 2 integration

---

## Pre-Flight Checklist

Run these checks before testing on any platform:

```bash
# 1. Verify Docker is running
docker info > /dev/null 2>&1 && echo "Docker: ✅ Running" || echo "Docker: ❌ Not running"

# 2. Check Docker Compose version
docker compose version

# 3. Verify Docker Compose V2 syntax support
docker compose config --quiet && echo "Compose config: ✅ Valid" || echo "Compose config: ❌ Invalid"

# 4. Check available disk space
df -h . | tail -1 | awk '{print "Disk space: " $4 " available"}'

# 5. Check memory (platform-dependent, see below)
```

### Memory Check by Platform

```bash
# Linux
free -h | grep Mem | awk '{print "Memory: " $2 " total, " $7 " available"}'

# macOS
sysctl -n hw.memsize | awk '{printf "Memory: %.1f GB total\n", $1/1024/1024/1024}'

# Windows (PowerShell)
Get-CimInstance Win32_ComputerSystem | ForEach-Object {
    "Memory: {0:N2} GB total" -f ($_.TotalPhysicalMemory / 1GB)
}
```

---

## Linux Testing

### Test Environment Setup

```bash
# Clone and navigate to repository
git clone <repo-url>
cd acgs2

# Copy environment template
cp .env.example .env

# Ensure proper permissions
chmod +x scripts/*.sh
```

### Test Execution

```bash
# Run comprehensive verification
./scripts/cross-platform-test.sh linux

# Or step-by-step:

# 1. Validate configuration
docker compose config --quiet && echo "✅ Config valid"

# 2. Start services
docker compose up -d

# 3. Wait for services (Kafka takes ~30s)
sleep 45

# 4. Verify all services running
docker compose ps --filter 'status=running' --format '{{.Service}}' | wc -l
# Expected: 5 (opa, jupyter, redis, zookeeper, kafka)

# 5. Test OPA health
curl -sf http://localhost:8181/health && echo "✅ OPA healthy"

# 6. Test Jupyter
curl -sf http://localhost:8888 && echo "✅ Jupyter accessible"

# 7. Run example project
cd examples/01-basic-policy-evaluation
docker compose up -d
python3 evaluate_policy.py
docker compose down
cd ../..

# 8. Cleanup
docker compose down
```

### Linux-Specific Considerations

1. **SELinux (RHEL/CentOS/Fedora)**
   - If SELinux is enabled, volume mounts may need `:Z` or `:z` suffix
   - Current compose.yaml uses `:ro` which is cross-platform compatible

2. **Docker Group Permissions**
   ```bash
   # If permission denied, add user to docker group
   sudo usermod -aG docker $USER
   newgrp docker
   ```

3. **cgroups v2 (Modern Distributions)**
   - Docker 20.10+ supports cgroups v2 natively
   - No additional configuration needed

### Expected Results (Linux)

| Test | Expected | Notes |
|------|----------|-------|
| Config validation | Pass | YAML syntax valid |
| Service startup | 5 services | opa, jupyter, redis, zookeeper, kafka |
| OPA health | HTTP 200 | `{"status": "ok"}` |
| Jupyter access | HTTP 200 | No token required |
| Example project | Success | All test cases pass |

---

## macOS Testing

### Test Environment Setup

```bash
# Ensure Docker Desktop is running
open -a Docker

# Wait for Docker to start
while ! docker info > /dev/null 2>&1; do
    echo "Waiting for Docker..."
    sleep 2
done

# Clone and navigate
git clone <repo-url>
cd acgs2

# Copy environment template
cp .env.example .env
```

### Test Execution

```bash
# Run comprehensive verification
./scripts/cross-platform-test.sh macos

# Or step-by-step (same as Linux):
docker compose config --quiet && echo "✅ Config valid"
docker compose up -d
sleep 45
docker compose ps --filter 'status=running' --format '{{.Service}}' | wc -l
curl -sf http://localhost:8181/health && echo "✅ OPA healthy"
curl -sf http://localhost:8888 && echo "✅ Jupyter accessible"

# Run example
cd examples/01-basic-policy-evaluation
docker compose up -d
python3 evaluate_policy.py
docker compose down
cd ../..

# Cleanup
docker compose down
```

### macOS-Specific Considerations

1. **Docker Desktop Memory Allocation**
   - Default 2 GB may not be enough for Kafka
   - Recommended: 4-6 GB
   - Settings → Resources → Memory

2. **Apple Silicon (M1/M2/M3)**
   - Images used are multi-arch (amd64/arm64)
   - Rosetta 2 may be used for some images (handled automatically)
   - Performance is native for most containers

3. **Port 8000 Conflict (AirPlay Receiver)**
   ```bash
   # Check if port 8000 is in use
   lsof -i :8000

   # If AirPlay Receiver is using it:
   # System Preferences → Sharing → Uncheck "AirPlay Receiver"
   ```

4. **File System Performance**
   - Use `:cached` or `:delegated` for better volume performance
   - Current compose.yaml uses `:ro` for policies (acceptable for read-only)

### Expected Results (macOS)

| Test | Expected | Notes |
|------|----------|-------|
| Config validation | Pass | YAML syntax valid |
| Service startup | 5 services | May take 60s on first run |
| OPA health | HTTP 200 | `{"status": "ok"}` |
| Jupyter access | HTTP 200 | No token required |
| Example project | Success | All test cases pass |
| Apple Silicon | Pass | Multi-arch images work |

---

## Windows Testing

### Test Environment Setup

#### Using WSL 2 (Recommended)

```powershell
# Ensure WSL 2 is enabled
wsl --status

# If not installed
wsl --install

# Open Ubuntu terminal and continue with Linux commands
wsl
```

#### Using PowerShell

```powershell
# Ensure Docker Desktop is running with WSL 2 backend
# Docker Desktop → Settings → General → Use WSL 2 based engine

# Clone repository
git clone <repo-url>
cd acgs2

# Copy environment template
Copy-Item .env.example .env
```

### Test Execution (WSL 2 - Recommended)

```bash
# Inside WSL 2 terminal (Ubuntu/Debian)
cd /mnt/c/path/to/acgs2

# Run comprehensive verification
./scripts/cross-platform-test.sh windows

# Or step-by-step:
docker compose config --quiet && echo "✅ Config valid"
docker compose up -d
sleep 60  # Windows may need more time
docker compose ps --filter 'status=running' --format '{{.Service}}' | wc -l
curl -sf http://localhost:8181/health && echo "✅ OPA healthy"
curl -sf http://localhost:8888 && echo "✅ Jupyter accessible"

# Run example
cd examples/01-basic-policy-evaluation
docker compose up -d
python3 evaluate_policy.py
docker compose down
cd ../..

# Cleanup
docker compose down
```

### Test Execution (PowerShell)

```powershell
# Validate configuration
docker compose config 2>$null
if ($LASTEXITCODE -eq 0) { Write-Host "✅ Config valid" -ForegroundColor Green }

# Start services
docker compose up -d

# Wait for services
Start-Sleep -Seconds 60

# Check running services
$services = docker compose ps --filter 'status=running' --format '{{.Service}}'
Write-Host "Running services: $($services.Count)"

# Test OPA
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8181/health" -ErrorAction Stop
    Write-Host "✅ OPA healthy" -ForegroundColor Green
} catch {
    Write-Host "❌ OPA not responding" -ForegroundColor Red
}

# Test Jupyter
try {
    $null = Invoke-WebRequest -Uri "http://localhost:8888" -ErrorAction Stop
    Write-Host "✅ Jupyter accessible" -ForegroundColor Green
} catch {
    Write-Host "❌ Jupyter not responding" -ForegroundColor Red
}

# Cleanup
docker compose down
```

### Windows-Specific Considerations

1. **WSL 2 Backend (Required)**
   - Docker Desktop must use WSL 2 backend, not Hyper-V
   - Settings → General → Use WSL 2 based engine
   - Much better performance than Hyper-V

2. **Line Endings (CRLF vs LF)**
   ```bash
   # Configure Git for Unix line endings
   git config --global core.autocrlf input

   # Fix existing files in WSL
   apt-get install dos2unix
   find . -name "*.sh" -exec dos2unix {} \;
   find . -name "*.rego" -exec dos2unix {} \;
   ```

3. **Path Syntax**
   - Use Unix paths in WSL 2: `/mnt/c/Users/...`
   - Use Windows paths in PowerShell: `C:\Users\...`
   - Volume mounts work from both

4. **File Permissions**
   - WSL 2 handles permissions correctly
   - Scripts may need `chmod +x` after clone

5. **Port Conflicts**
   ```powershell
   # Check what's using a port
   netstat -ano | findstr :8181

   # Find process by PID
   tasklist /fi "pid eq <PID>"
   ```

6. **Firewall**
   - Windows Firewall may block container access
   - Docker Desktop usually adds exceptions automatically
   - If blocked: Allow Docker Desktop through firewall

### Expected Results (Windows)

| Test | Expected | Notes |
|------|----------|-------|
| Config validation | Pass | YAML syntax valid |
| Service startup | 5 services | May take 90s on first run |
| OPA health | HTTP 200 | `{"status": "ok"}` |
| Jupyter access | HTTP 200 | No token required |
| Example project | Success | All test cases pass |
| WSL 2 | Pass | Best performance |

---

## Cross-Platform Compatibility Notes

### Volume Mounts

The compose.yaml uses relative paths that work on all platforms:

```yaml
volumes:
  - ./policies:/policies:ro     # Works on all platforms
  - ./notebooks:/home/jovyan/notebooks  # Works on all platforms
```

**Key considerations:**
- Avoid absolute Windows paths (`C:\path`)
- Use forward slashes, not backslashes
- Relative paths (`./ `) are platform-agnostic

### Environment Variables

Environment variables syntax is consistent:

```yaml
environment:
  - OPA_URL=http://opa:8181
  - MPLBACKEND=Agg
```

**Port Override:**
```bash
# All platforms
OPA_PORT=8182 docker compose up -d

# Windows PowerShell
$env:OPA_PORT=8182; docker compose up -d
```

### Health Checks

All health checks use Docker-native commands:

```yaml
healthcheck:
  test: ["CMD", "wget", "-q", "--spider", "http://localhost:8181/health"]
```

**Cross-platform notes:**
- `CMD` is preferred over `CMD-SHELL` for portability
- Shell commands (`CMD-SHELL`) use `/bin/sh` on Linux/macOS, compatible with WSL on Windows

### Network Configuration

Bridge network works identically across platforms:

```yaml
networks:
  acgs-onboarding:
    driver: bridge
```

---

## Known Issues and Workarounds

### Issue 1: Kafka Takes Long to Start on Windows

**Symptom:** Kafka health check fails initially on Windows

**Workaround:**
```bash
# Increase wait time
sleep 90  # Instead of 30

# Or wait for health check
while ! docker compose exec -T kafka kafka-topics --bootstrap-server localhost:29092 --list 2>/dev/null; do
    echo "Waiting for Kafka..."
    sleep 5
done
```

### Issue 2: Volume Permissions on SELinux

**Symptom:** Permission denied on Linux with SELinux

**Workaround:**
```bash
# Add :Z to volume mounts for SELinux
# Or run in permissive mode for testing
sudo setenforce 0
```

### Issue 3: Slow File Sync on macOS

**Symptom:** Jupyter notebook saves slowly

**Workaround:**
- Use named volumes for data that doesn't need host access
- Accept the trade-off for development convenience

### Issue 4: WSL 2 Memory Limits

**Symptom:** Containers killed (OOM) on Windows

**Workaround:**
Create `~/.wslconfig` (in Windows home directory):
```ini
[wsl2]
memory=6GB
swap=2GB
```
Then restart WSL: `wsl --shutdown`

---

## Verification Matrix

### Test Results Template

Use this table to record test results:

| Test Case | Linux | macOS (Intel) | macOS (Apple Silicon) | Windows (WSL 2) |
|-----------|-------|---------------|----------------------|-----------------|
| Docker version | | | | |
| Compose version | | | | |
| Config validation | | | | |
| Services start (5) | | | | |
| OPA health | | | | |
| Jupyter accessible | | | | |
| Redis ping | | | | |
| Kafka topics | | | | |
| Example 01 | | | | |
| Example 02 | | | | |
| Example 03 | | | | |
| Notebook 01 | | | | |
| Notebook 02 | | | | |
| Startup time | | | | |

### Pass Criteria

- All services start successfully
- All health checks pass
- All example projects run
- All notebooks execute without errors
- Startup time < 2 minutes

---

## Running the Cross-Platform Test Script

A comprehensive test script is provided:

```bash
# Linux
./scripts/cross-platform-test.sh linux

# macOS
./scripts/cross-platform-test.sh macos

# Windows (in WSL 2)
./scripts/cross-platform-test.sh windows

# All platforms (runs appropriate tests)
./scripts/cross-platform-test.sh
```

The script:
1. Detects the current platform
2. Runs platform-appropriate checks
3. Validates all services
4. Runs example projects
5. Generates a test report

---

## Contributing Test Results

If you've tested on a new platform or configuration, please contribute your results:

1. Run the test script and save output
2. Fill in the verification matrix
3. Note any issues encountered and workarounds used
4. Submit a pull request updating this document

---

**Constitutional Hash**: `cdd01ef066bc6cf2`
**Version**: 1.0.0
**Last Updated**: 2025-01-03
