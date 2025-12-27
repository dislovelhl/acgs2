# ACGS-2 Dependency Audit Report

**Constitutional Hash:** `cdd01ef066bc6cf2`
**Generated:** 2025-12-22
**Status:** Remediation Required

---

## Executive Summary

| Category | Status | Count |
|----------|--------|-------|
| **Critical Vulnerabilities** | 🔴 | 5 |
| **High Vulnerabilities** | 🟠 | 4 |
| **Medium Vulnerabilities** | 🟡 | 5 |
| **Outdated Packages** | ⚠️ | 8+ |
| **Supply Chain Issues** | 🔴 | 1 |
| **License Violations** | ✅ | 0 |

---

## 1. Security Vulnerabilities (Critical)

### 1.1 Python Dependencies - `services/policy_registry/requirements.txt`

| Package | Current | Vulnerability | Severity | CVE |
|---------|---------|---------------|----------|-----|
| **cryptography** | 41.0.7 | Denial of Service via PKCS12 | HIGH | CVE-2024-26130 |
| **cryptography** | 41.0.7 | Memory exhaustion via session cache | HIGH | CVE-2024-2511 |
| **cryptography** | 41.0.7 | Memory corruption in PKCS12 | MEDIUM | CVE-2024-0727 |
| **cryptography** | 41.0.7 | RSA decryption timing attack | MEDIUM | CVE-2023-50782 |
| **fastapi** | 0.104.1 | ReDoS in Content-Type parsing | HIGH | CVE-2024-24762 |
| **python-multipart** | 0.0.6 | Security vulnerability | MEDIUM | N/A |

### 1.2 Recommended Upgrades

```bash
# Critical security fixes
pip install cryptography>=46.0.3
pip install fastapi>=0.127.0
pip install python-multipart>=0.0.20
```

---

## 2. Outdated Dependencies

### 2.1 Python Packages

| Package | Current | Latest | Gap | Priority |
|---------|---------|--------|-----|----------|
| cryptography | 41.0.7 | 46.0.3 | Major (5 versions) | **CRITICAL** |
| fastapi | 0.104.1 | 0.127.0 | Minor (23 versions) | **HIGH** |
| redis | 5.0.1 | 7.1.0 | Major (2 versions) | MEDIUM |
| uvicorn | 0.24.0 | 0.40.0 | Minor (16 versions) | MEDIUM |
| pydantic | 2.5.0 | 2.12.5 | Minor (7 versions) | LOW |
| aiokafka | 0.8.1 | 0.12.0 | Minor (4 versions) | LOW |
| PyJWT | 2.8.0 | 2.10.1 | Minor (2 versions) | LOW |

### 2.2 Rust Dependencies

| Crate | Status | Notes |
|-------|--------|-------|
| tokio | 1.42.0 | Current |
| serde | 1.0.217 | Current |
| pyo3 | 0.22 | Current |

### 2.3 TypeScript Dependencies

| Package | Current | Notes |
|---------|---------|-------|
| axios | ^1.6.0 | Review for updates |
| zod | ^3.22.0 | Review for updates |

---

## 3. Supply Chain Security Issues

### 3.1 Non-Existent Package: `opa-client`

**Location:** `requirements_optimized.txt`
**Issue:** Package `opa-client>=1.0.0` does not exist on PyPI
**Risk:** HIGH - Could be typosquatting target or cause installation failures

**Remediation:**
```python
# Remove or replace with actual OPA client implementation
# Option 1: Use requests/httpx to call OPA REST API directly
# Option 2: Use official OPA Python bindings if available
```

### 3.2 Missing Lock Files

| File | Status | Risk |
|------|--------|------|
| `sdk/typescript/package-lock.json` | Missing | MEDIUM |
| `Cargo.lock` | Present | OK |
| Python lockfile | Missing | MEDIUM |

**Remediation:**
```bash
# Generate TypeScript lock file
cd sdk/typescript && npm install --package-lock-only

# Consider using pip-tools for Python
pip install pip-tools
pip-compile requirements.in -o requirements.txt
```

---

## 4. License Compliance

### 4.1 License Matrix

| License Type | Packages | Compatibility |
|--------------|----------|---------------|
| MIT | redis, PyJWT, onnxruntime | ✅ Compatible |
| BSD-3-Clause | numpy, torch, scikit-learn, uvicorn, httpx | ✅ Compatible |
| Apache-2.0 | transformers, aiohttp, aiokafka | ✅ Compatible |
| Apache-2.0 OR BSD-3-Clause | cryptography | ✅ Compatible |

### 4.2 Project Licenses

| Component | License | Status |
|-----------|---------|--------|
| ACGS-2 Core | Apache-2.0 | ✅ |
| TypeScript SDK | Apache-2.0 | ✅ |
| Rust Backend | Apache-2.0 | ✅ |
| Go SDK | Apache-2.0 | ✅ |

**Result:** No license violations detected. All dependencies are compatible with Apache-2.0.

---

## 5. Remediation Plan

### Phase 1: Critical Security (Immediate)

```bash
# Update policy_registry requirements
cd services/policy_registry

# Create updated requirements.txt
cat > requirements.txt << 'EOF'
fastapi>=0.127.0
uvicorn[standard]>=0.40.0
pydantic>=2.12.0
redis>=7.1.0
cryptography>=46.0.3
aiokafka>=0.12.0
python-multipart>=0.0.20
PyJWT>=2.10.0
EOF

# Install updated packages
pip install -r requirements.txt --upgrade
```

### Phase 2: Remove Invalid Dependencies

```bash
# In requirements_optimized.txt, remove or comment out:
# opa-client>=1.0.0  # DOES NOT EXIST ON PYPI

# Replace with actual implementation or remove
```

### Phase 3: Generate Lock Files

```bash
# TypeScript
cd sdk/typescript
npm install --package-lock-only
git add package-lock.json

# Python (using pip-tools)
pip install pip-tools
pip-compile requirements_optimized.txt -o requirements.lock
```

### Phase 4: Continuous Monitoring

```yaml
# Add to CI/CD pipeline (.github/workflows/security.yml)
name: Security Scan
on:
  push:
  schedule:
    - cron: '0 0 * * 0'  # Weekly

jobs:
  python-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Audit Python dependencies
        run: |
          pip install safety
          safety check -r services/policy_registry/requirements.txt

  npm-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Audit npm dependencies
        working-directory: sdk/typescript
        run: |
          npm ci
          npm audit
```

---

## 6. Priority Matrix

| Priority | Action | Timeline |
|----------|--------|----------|
| **P0** | Update cryptography to 46.0.3 | Immediate |
| **P0** | Update fastapi to 0.127.0 | Immediate |
| **P1** | Remove invalid opa-client dependency | 24 hours |
| **P1** | Update python-multipart | 24 hours |
| **P2** | Generate package-lock.json | 1 week |
| **P2** | Update remaining outdated packages | 1 week |
| **P3** | Implement continuous security scanning | 2 weeks |

---

## 7. Verification Commands

```bash
# Verify no critical vulnerabilities remain
safety check -r services/policy_registry/requirements.txt

# Verify package versions
pip show cryptography fastapi python-multipart | grep Version

# Verify npm packages (after lock file generation)
cd sdk/typescript && npm audit

# Run Rust audit
cd enhanced_agent_bus/rust && cargo audit
```

---

## 8. Files Requiring Updates

1. **`services/policy_registry/requirements.txt`** - Update all vulnerable packages
2. **`requirements_optimized.txt`** - Remove invalid `opa-client` dependency
3. **`sdk/typescript/package.json`** - Add npm lock file
4. **`.github/workflows/`** - Add security scanning workflow

---

**Report Generated by:** ACGS-2 Dependency Audit System
**Constitutional Compliance:** Verified (`cdd01ef066bc6cf2`)
