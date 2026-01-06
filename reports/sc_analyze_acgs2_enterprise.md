# ACGS-2 Enterprise Stack — Code Analysis Report (/sc:analyze)

Generated: 2026-01-04T17:09:33Z
Scope: `src/acgs2/**` + related tests in `tests/**`
Focus: quality, security, performance, architecture

## Executive Summary

The enterprise stack (OBS/AUD/NPT + FastAPI/WebSocket/Auth + Flows B/C/D) is functional end-to-end, but it currently contains several **production-blocking security and compliance issues**, plus some **architecture gaps** around multi-step orchestration and checkpoint resumption.

Top risks to address immediately:

- **Remote code execution risk**: unsafe `eval()` usage in tool execution paths.
- **Secret leakage & insecure defaults**: hardcoded JWT secret, printing API keys at import time, permissive CORS with credentials.
- **Compliance risk**: audit trail currently records memory content previews and request metadata that may contain PII.

## Method

- **Discover**: enumerated Python files under `src/acgs2` and `tests`.
- **Scan**: static pattern search (e.g., `eval(`, hardcoded secrets, PII-ish logging).
- **Evaluate**: prioritized findings by likely impact and exploitability.
- **Recommend**: concrete remediations and hardening roadmap.

## Quick Metrics (scoped)

- **Files scanned**:
  - `src/acgs2`: 17 Python files
  - `tests`: 15 Python files (including integration tests)
- **High-risk patterns detected**:
  - `eval(` occurrences: 2
  - Hardcoded JWT secret: 1
  - API keys printed at import time: 2 lines
  - CORS wildcard origin + credentials: 1 config

## Findings (prioritized)

### SEC-01 — Unsafe `eval()` in tool execution (Critical)

**Where**
- `src/acgs2/components/tms.py`: calculator fallback path uses `eval(expression)`
- `src/acgs2/components/cre.py`: Flow C multi-step calculator simulation uses `eval(expr)`

**Impact**
- Arbitrary code execution if attacker controls expression content (directly or indirectly).
- Violates sandboxing assumptions.

**Recommendation**
- Replace with a safe expression evaluator using `ast.parse` with an allowlist of nodes/operators, or use a vetted library (e.g., `simpleeval`) and restrict available names/functions.
- In Flow C, do not simulate tool execution with `eval`; route through TMS with SAS gating.

### SEC-02 — Secrets & credentials hygiene (Critical)

**Where**
- `src/acgs2/api/auth.py`: hardcoded JWT secret, and API keys printed at import time.
- `src/acgs2/api/main.py`: CORS allows `*` and `allow_credentials=True` (risky).

**Impact**
- JWT secret in code enables token forgery if leaked (and it will leak via repo copies/logs).
- Printing API keys can leak credentials to logs/CI output.
- Wildcard CORS + credentials can enable cross-site request abuse.

**Recommendation**
- Load JWT secret from environment (`ACGS2_JWT_SECRET`) and fail hard if missing in non-dev mode.
- Remove module-level “test key” creation + `print()`; only generate in explicit dev/test fixtures.
- Replace `allow_origins=["*"]` with an explicit allowlist and ensure credentialed CORS is configured correctly.

### SEC-03 — Audit trail may contain PII / sensitive content (High)

**Where**
- `src/acgs2/components/dms.py`: writes `"content_preview"` into AUD entries.
- `src/acgs2/components/uig.py`: includes `"metadata": request.metadata` inside audit payload.

**Impact**
- Audit logs are commonly long-retention; storing content previews and arbitrary metadata can violate privacy/compliance requirements.
- Conflicts with manifest invariants (“No PII in metrics”; audit also generally must be redacted/minimized).

**Recommendation**
- Remove content previews from audit payloads. Store **hashes**, sizes, and structured metadata only.
- Redact or strictly schema-validate `request.metadata` before logging/auditing (e.g., allowlist keys).
- Add a “PII-safe audit serializer” (shared utility) and enforce it in UIG/DMS/TMS.

### ARCH-01 — Flow C orchestration is not truly mediated by TMS/DMS (High)

**Where**
- `src/acgs2/components/cre.py`: multi-step execution currently simulates tool calls rather than invoking TMS.
- `src/acgs2/components/dms.py`: `read_checkpoint()` is a stub returning `None`.

**Impact**
- Flow C does not fully meet “tool-mediated execution” and “checkpoint/resume” expectations.
- Limits production usefulness for long-running tasks and crash recovery.

**Recommendation**
- Refactor Flow C execution to route each step through:
  - SAS plan/tool checks
  - TMS execution
  - DMS `write_checkpoint()` and `read_checkpoint()` for resumption
- Add explicit step idempotency and compensation paths.

### REL-01 — Audit chain hashing bug when `timestamp` not set (Medium)

**Where**
- `src/acgs2/components/aud.py`: computes hash, then sets timestamp if empty.

**Impact**
- If any caller creates an AuditEntry without timestamp, the computed `entry_hash` won’t match later verification (timestamp becomes part of hashed fields via `_entry_to_dict`).

**Recommendation**
- Normalize/populate timestamp **before** hashing and chaining.

### REL-02 — Auth middleware uses `JSONResponse` without importing it (Medium)

**Where**
- `src/acgs2/api/auth.py`: `auth_middleware()` returns `JSONResponse(...)` but module does not import it.

**Impact**
- If middleware is enabled, runtime error will occur.

**Recommendation**
- Import `JSONResponse` in `auth.py` or move middleware into `api/main.py` where it’s already imported.

### QUAL-01 — Inconsistent `UserResponse.metadata` type usage (Medium)

**Where**
- `src/acgs2/components/uig.py`: returns `metadata=None` when not terminating session.

**Impact**
- Breaks consumers expecting `metadata` to be a dict.

**Recommendation**
- Always return a dict (use `{}` when empty). Keep dataclass type consistent.

### QUAL-02 — Auth tests inconsistent with AuthManager password logic (Medium)

**Where**
- `tests/api/test_auth.py`: expects `authenticate_user("testuser", "password")` to succeed.
- `src/acgs2/api/auth.py`: accepts only `password_for_{username}`.

**Impact**
- Test suite will fail or gives misleading confidence.

**Recommendation**
- Align tests with actual logic, or (preferably) implement a real password hash store and update tests accordingly.

### PERF-01 — Observability cleanup strategy is O(N) per event (Low/Medium)

**Where**
- `src/acgs2/components/obs.py`: trace cleanup is executed on each emitted event.

**Impact**
- Potential throughput degradation as trace count grows.

**Recommendation**
- Move cleanup to a periodic task or amortize cleanup with a probabilistic/interval trigger.

## Recommended Remediation Roadmap

### Immediate (blockers)
- Remove/replace all `eval()` usage in `CRE` and `TMS`.
- Remove import-time API key generation and `print()` of secrets.
- Move JWT secret to environment/config; add safe defaults for dev only.
- Remove `content_preview` from AUD; redact/allowlist `request.metadata` before audit logging.
- Lock down CORS configuration (explicit origins; credential policy).

### Short-term (stability + correctness)
- Fix AUD timestamp hashing order.
- Fix missing `JSONResponse` import (or remove middleware).
- Enforce `UserResponse.metadata` as dict always.
- Fix/align authentication tests and remove side-effectful imports in test runs.

### Medium-term (architecture hardening)
- Implement true Flow C execution through SAS→TMS, with DMS checkpoint write/read and resumable orchestration.
- Extend Flow D event emission beyond SAS to CRE/TMS/DMS for richer learning signals.
- Add structured schemas for audit/telemetry payloads and centralized redaction utilities.

## Notes

- `pyproject.toml` includes FastAPI/Uvicorn in optional dependency group `cli`, but `PyJWT` is not declared there; ensure runtime dependencies are declared for reliable installs.
