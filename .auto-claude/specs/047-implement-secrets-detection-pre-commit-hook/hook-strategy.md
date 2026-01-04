# Pre-commit Hook Strategy for Secrets Detection

**Date:** 2026-01-03
**Subtask:** 1.3 - Design hook strategy
**Status:** Complete

## Executive Summary

This document defines a **multi-layered defense-in-depth approach** to secrets detection using:
1. **Gitleaks** - Industry-standard tool for general secret scanning
2. **Custom ACGS-2 Hook** - Project-specific patterns from `secrets_manager.py`

The strategy balances security with developer experience, ensuring <5s commit times while providing comprehensive coverage.

---

## 1. Multi-Layered Architecture

### Layer 1: Gitleaks (Broad Coverage)

**Purpose:** Industry-standard secret detection with 140+ built-in rules

**Responsibilities:**
- Detect common secrets (AWS keys, GitHub tokens, generic API keys)
- Catch secrets that don't match ACGS-2 patterns
- Provide baseline protection against known secret formats
- Leverage community-maintained rule database

**Configuration:**
- Custom `.gitleaks.toml` with ACGS-2-specific rules
- Enhanced allowlist for development placeholders
- Optimized for pre-commit (staged files only)

**Strengths:**
- ✅ Comprehensive rule database (AWS, GitHub, Google, etc.)
- ✅ Regular updates from community
- ✅ High-entropy string detection
- ✅ Industry-proven tool

**Weaknesses:**
- ⚠️ No awareness of ACGS-2 specific patterns
- ⚠️ Can't distinguish ACGS-2 placeholders from real secrets
- ⚠️ Generic rules may miss AI provider keys (Anthropic, OpenRouter)

### Layer 2: Custom ACGS-2 Hook (Precise Validation)

**Purpose:** Project-specific secret validation using patterns from `secrets_manager.py`

**Responsibilities:**
- Validate against 8 defined `CREDENTIAL_PATTERNS`
- Detect ACGS-2-specific AI provider keys (Anthropic, Claude Code, OpenRouter)
- Apply intelligent placeholder detection (`dev-*`, `your-*`, etc.)
- Provide actionable error messages with remediation steps
- Maintain consistency with runtime validation

**Configuration:**
- Python script: `scripts/check-secrets-pre-commit.py`
- Import patterns directly from `acgs2-core/shared/secrets_manager.py`
- Allow-list configuration for known-safe values

**Strengths:**
- ✅ Uses same patterns as runtime validation (single source of truth)
- ✅ ACGS-2-specific pattern detection (Anthropic, OpenRouter, Claude Code)
- ✅ Intelligent placeholder detection
- ✅ Context-aware (file-specific rules)
- ✅ Actionable error messages

**Weaknesses:**
- ⚠️ Only covers 8 of 15 secrets (those with defined patterns)
- ⚠️ Requires maintenance as new secrets are added

### Why Both Layers?

**Defense in Depth:**
- Gitleaks catches secrets custom hook might miss
- Custom hook catches ACGS-2 secrets gitleaks doesn't know about
- Overlapping coverage increases detection probability

**Complementary Strengths:**
```
┌─────────────────────────────────────────┐
│  Gitleaks: Broad, community-maintained  │
│  - AWS, GitHub, Google, etc.            │
│  - Generic high-entropy detection       │
│  - 140+ rules out of box                │
└─────────────────────────────────────────┘
                    ∪ (Union)
┌─────────────────────────────────────────┐
│  Custom Hook: Precise, ACGS-2 specific  │
│  - Anthropic, OpenRouter, Claude Code   │
│  - Placeholder-aware detection          │
│  - Consistent with runtime validation   │
└─────────────────────────────────────────┘
            = Maximum Coverage
```

---

## 2. Hook Execution Flow

### Pre-commit Sequence

```
Developer commits code
         ↓
┌────────────────────────────┐
│ 1. Run Gitleaks Hook       │ (~2-3s)
│    - Scan staged files     │
│    - Check against 140+    │
│      built-in rules        │
│    - Apply custom ACGS-2   │
│      rules from .toml      │
└────────────────────────────┘
         ↓
    Pass? ──No──→ Block commit, show gitleaks findings
         ↓
        Yes
         ↓
┌────────────────────────────┐
│ 2. Run Custom ACGS-2 Hook  │ (~1-2s)
│    - Scan staged files     │
│    - Validate against      │
│      CREDENTIAL_PATTERNS   │
│    - Check placeholders    │
│    - Apply file-specific   │
│      rules                 │
└────────────────────────────┘
         ↓
    Pass? ──No──→ Block commit, show custom findings
         ↓
        Yes
         ↓
   Commit succeeds ✅
```

**Total Time Target:** <5 seconds for typical commits

**Performance Optimization:**
- Both hooks run in parallel where possible
- Scan only staged files (not full history)
- Skip binary files and large media
- Cache gitleaks binary for faster startup

---

## 3. Files to Scan vs Exclude

### High Priority - MUST Scan

**Environment Files:**
```
**/.env
**/.env.local
**/.env.production
**/.env.prod
**/.env.staging
service-*/.env
```

**Rationale:** Primary location for secrets, highest risk

**Source Code:**
```
**/*.py
**/*.ts
**/*.js
**/*.tsx
**/*.jsx
```

**Rationale:** Hardcoded secrets in source code, very high risk

**Configuration Files:**
```
**/*.yaml
**/*.yml
**/*.json
**/*.toml
**/config/**/*
```

**Rationale:** Common location for credentials and API keys

**Infrastructure as Code:**
```
**/docker-compose*.yml
**/Dockerfile
**/*.dockerfile
**/k8s/**/*.yaml
**/helm/**/values*.yaml
```

**Rationale:** May contain embedded secrets for services

**Scripts:**
```
**/*.sh
**/*.bash
**/scripts/**/*
```

**Rationale:** Shell scripts often contain exported credentials

### Medium Priority - SHOULD Scan

**Markdown Documentation:**
```
**/*.md
**/docs/**/*
```

**Rationale:** May accidentally contain real secrets in examples (scan but allow redacted formats)

**Git Configuration:**
```
.git/config
.github/**/*
```

**Rationale:** Git config may store credentials

### Exclude from Scanning

**Example/Template Files:**
```
**/.env.example
**/.env.template
**/*.example.*
**/*.template.*
```

**Rationale:** Intentionally contain placeholder values, but validate placeholders are safe

**Test Fixtures:**
```
**/tests/fixtures/**/*
**/test/fixtures/**/*
**/__fixtures__/**/*
```

**Rationale:** May contain test secrets, but validate these are documented exceptions

**Dependencies:**
```
**/node_modules/**/*
**/.venv/**/*
**/venv/**/*
**/__pycache__/**/*
**/dist/**/*
**/build/**/*
```

**Rationale:** Third-party code, not our responsibility

**Binary/Media Files:**
```
**/*.png
**/*.jpg
**/*.jpeg
**/*.gif
**/*.pdf
**/*.zip
**/*.tar.gz
**/*.woff
**/*.woff2
**/*.ttf
**/*.eot
```

**Rationale:** Performance - binary files unlikely to contain text secrets

**Development Certificates (with explicit allow-list):**
```
acgs2-core/shared/auth/certs/sp.key
acgs2-core/shared/auth/certs/sp.crt
```

**Rationale:** Already in `.gitleaksignore`, development-only, self-signed

---

## 4. Scanning Strategy by File Type

### Strategy: Context-Aware Validation

Different file types require different validation approaches:

#### `.env` Files

**Scan Level:** STRICT

**Rules:**
1. ❌ BLOCK any value matching `CREDENTIAL_PATTERNS` without placeholder indicators
2. ✅ ALLOW values with `dev-*`, `test-*`, `your-*` prefixes
3. ✅ ALLOW empty values
4. ⚠️ WARN on generic passwords unless in `.env.example`

**Example:**
```bash
# .env - BLOCKED
JWT_SECRET=a1b2c3d4e5f6789abcdef0123456789a1b2c3d4e5f6789abcdef0123456789

# .env.dev - ALLOWED
JWT_SECRET=dev-jwt-secret-min-32-chars-required

# .env.example - ALLOWED
JWT_SECRET=your-jwt-secret-min-32-chars
```

#### Python Source Files

**Scan Level:** VERY STRICT

**Rules:**
1. ❌ BLOCK any pattern-matching secrets
2. ❌ BLOCK hardcoded credentials
3. ❌ NO EXCEPTIONS (use environment variables)

**Example:**
```python
# BLOCKED - hardcoded secret
OPENAI_KEY = "sk-abc123def456..."

# ALLOWED - environment variable
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# ALLOWED - from secrets manager
OPENAI_KEY = secrets_manager.get_secret("OPENAI_API_KEY")
```

#### YAML/JSON Configuration

**Scan Level:** STRICT

**Rules:**
1. ❌ BLOCK pattern-matching secrets
2. ✅ ALLOW placeholder references: `${ENV_VAR}`, `<placeholder>`
3. ✅ ALLOW redacted examples in documentation

**Example:**
```yaml
# BLOCKED
database:
  password: my_real_db_password_123

# ALLOWED - environment variable reference
database:
  password: ${DB_PASSWORD}

# ALLOWED - placeholder
database:
  password: <your-database-password>
```

#### Markdown Documentation

**Scan Level:** RELAXED

**Rules:**
1. ✅ ALLOW redacted formats: `sk-ant-XXX...XXX`
2. ✅ ALLOW example placeholders: `your-api-key-here`
3. ⚠️ WARN on pattern matches, but allow override

**Example:**
```markdown
# ALLOWED - redacted example
Set your API key: `sk-ant-XXX...XXX`

# ALLOWED - instructional
ANTHROPIC_API_KEY=your-anthropic-api-key

# WARNED but allowed - looks real but documented
For testing: `sk-test-123456789012345678901234567890...`
```

---

## 5. Performance Considerations

### Target Performance Metrics

**Acceptable:**
- Small commits (1-5 files): <2 seconds
- Medium commits (6-20 files): <5 seconds
- Large commits (21+ files): <10 seconds

**Unacceptable:**
- Any commit taking >15 seconds
- Scanning full git history on each commit

### Optimization Strategies

#### 1. Scan Only Staged Files

**Gitleaks Configuration:**
```bash
# Use --staged flag (pre-commit framework handles this)
gitleaks detect --no-git --staged
```

**Custom Hook:**
```python
# Get only staged files
staged_files = subprocess.check_output(
    ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM']
).decode().splitlines()
```

**Performance Gain:** ~90% faster than full repository scan

#### 2. File Type Filtering

**Skip Non-Text Files:**
```python
SKIP_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip',
                   '.tar', '.gz', '.woff', '.woff2', '.ttf', '.eot'}

def should_scan_file(file_path: str) -> bool:
    ext = os.path.splitext(file_path)[1].lower()
    return ext not in SKIP_EXTENSIONS
```

**Performance Gain:** Avoid reading large binary files

#### 3. Early Exit on First Finding (Optional)

**For Developers:**
```python
# Stop on first secret found (faster feedback)
--exit-code 1 --fail-on-first
```

**For CI:**
```python
# Report all findings (complete security scan)
--exit-code 1 --report-all
```

**Performance Gain:** Up to 50% faster for commits with secrets

#### 4. Parallel Execution

**Run Both Hooks in Parallel:**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    hooks:
      - id: gitleaks
        stages: [commit]
        # Runs in parallel with other hooks

  - repo: local
    hooks:
      - id: check-acgs2-secrets
        name: Check ACGS-2 Secrets
        entry: python scripts/check-secrets-pre-commit.py
        language: system
        stages: [commit]
        # Runs in parallel with gitleaks
```

**Performance Gain:** ~40% time reduction (2 hooks run simultaneously)

#### 5. Caching

**Gitleaks Binary Caching:**
- Pre-commit framework caches tools automatically
- First run: ~5s (download binary)
- Subsequent runs: ~2s (use cached binary)

**Pattern Compilation Caching:**
```python
import functools

@functools.lru_cache(maxsize=None)
def get_compiled_patterns():
    """Cache compiled regex patterns for reuse."""
    return {
        name: re.compile(pattern)
        for name, pattern in CREDENTIAL_PATTERNS.items()
    }
```

**Performance Gain:** ~20% faster for multi-file scans

#### 6. Incremental Scanning

**Only Scan Changed Lines (Advanced):**
```python
def get_changed_lines(file_path: str):
    """Get only added/modified lines from git diff."""
    diff = subprocess.check_output(
        ['git', 'diff', '--cached', '-U0', file_path]
    ).decode()
    # Parse diff for '+' lines only
    return parse_added_lines(diff)
```

**Performance Gain:** ~60% faster for large files with small changes

### Performance Monitoring

**Add Timing to Hooks:**
```python
import time

start_time = time.time()
# ... run hook ...
elapsed = time.time() - start_time

if elapsed > 5.0:
    print(f"⚠️ WARNING: Hook took {elapsed:.2f}s (target: <5s)")
```

**Collect Metrics:**
- Track hook execution time per commit
- Identify slow patterns or files
- Optimize bottlenecks

---

## 6. Hook Configuration Details

### Gitleaks Configuration (.gitleaks.toml)

**Structure:**
```toml
title = "ACGS-2 Gitleaks Configuration"

# Custom rules for ACGS-2 specific secrets
[[rules]]
id = "anthropic-api-key"
description = "Anthropic API Key"
regex = '''sk-ant-[A-Za-z0-9_-]{80,}'''
keywords = ["sk-ant-"]

[[rules]]
id = "claude-code-oauth-token"
description = "Claude Code OAuth Token"
regex = '''sk-ant-oat\d{2}-[A-Za-z0-9_-]{60,}'''
keywords = ["sk-ant-oat"]

[[rules]]
id = "openrouter-api-key"
description = "OpenRouter API Key"
regex = '''sk-or-v1-[A-Za-z0-9]{60,}'''
keywords = ["sk-or-v1-"]

[[rules]]
id = "huggingface-token"
description = "HuggingFace API Token"
regex = '''hf_[A-Za-z0-9]{30,}'''
keywords = ["hf_"]

# Allowlist for development placeholders
[allowlist]
description = "Safe development placeholders"

# Placeholder patterns
regexes = [
  '''dev-.*''',
  '''test-.*''',
  '''your-.*''',
  '''<.*>''',
  '''.*-example''',
  '''placeholder-.*''',
  '''XXX''',
  '''\*\*\*hidden\*\*\*''',
  '''\[REDACTED\]''',
]

# Specific paths to exclude from scanning
paths = [
  '''.env.example$''',
  '''.env.template$''',
  '''tests/fixtures/.*''',
  '''docs/.*\.md$''',
]

# Specific commits to skip (if needed)
commits = []

# Stop words that indicate false positives
stopwords = []
```

### Custom Hook Configuration (scripts/check-secrets-pre-commit.py)

**Key Features:**

1. **Import CREDENTIAL_PATTERNS directly:**
```python
from acgs2_core.shared.secrets_manager import CREDENTIAL_PATTERNS, SECRET_CATEGORIES
```

2. **Placeholder Detection:**
```python
def is_placeholder(value: str, file_path: str) -> bool:
    """Check if value is a safe placeholder."""
    # Category 1: Prefix-based
    if any(value.startswith(p) for p in ['dev-', 'test-', 'your-', 'placeholder-']):
        return True

    # Category 2: Instructional
    if any(marker in value.lower() for marker in ['<', '>', 'example', 'template']):
        return True

    # Category 3: Known-safe (file-specific)
    if '.env.example' in file_path or '.env.dev' in file_path:
        if value in ['dev_password', 'password', 'acgs2_pass']:
            return True

    # Category 4: Empty
    if not value or value.strip() == '':
        return True

    # Category 5: Redacted
    if any(marker in value for marker in ['XXX', '***', '[REDACTED]', '<hidden>']):
        return True

    return False
```

3. **File-Specific Rules:**
```python
def get_scan_level(file_path: str) -> str:
    """Determine scanning strictness based on file type."""
    if file_path.endswith('.env.example') or file_path.endswith('.env.template'):
        return 'RELAXED'  # Allow placeholders
    elif file_path.endswith('.env.dev'):
        return 'MODERATE'  # Warn on suspicious values
    elif '.env' in file_path:
        return 'STRICT'  # Block all real secrets
    elif file_path.endswith('.py'):
        return 'VERY_STRICT'  # No exceptions
    elif file_path.endswith('.md'):
        return 'RELAXED'  # Documentation examples OK
    else:
        return 'STRICT'  # Default
```

4. **Actionable Error Messages:**
```python
def report_secret_found(secret_name: str, file_path: str, line_num: int):
    """Report secret with remediation steps."""
    print(f"🚫 SECRET DETECTED: {secret_name}")
    print(f"   File: {file_path}:{line_num}")
    print(f"   Category: {get_secret_category(secret_name)}")
    print(f"\n💡 REMEDIATION:")
    print(f"   1. Remove the secret from {file_path}")
    print(f"   2. Add to .env (not committed to git)")
    print(f"   3. Load via: secrets_manager.get_secret('{secret_name}')")
    print(f"\n   OR if this is a safe placeholder:")
    print(f"   1. Use prefix: dev-*, test-*, your-*")
    print(f"   2. Add to .gitleaksignore with justification")
```

---

## 7. Allow-list Strategy

### Three-Tier Allow-list System

#### Tier 1: Pattern-Based (Broad)

**Location:** `.gitleaks.toml` allowlist section

**Purpose:** Exclude common placeholder patterns across the entire codebase

**Examples:**
- `dev-*` (development prefixes)
- `test-*` (test data)
- `your-*` (instructional placeholders)
- `<.*>` (angle-bracket placeholders)

**Pros:** Fast, applies globally, low maintenance
**Cons:** May miss sophisticated fake placeholders

#### Tier 2: Path-Based (Targeted)

**Location:** `.gitleaks.toml` allowlist paths

**Purpose:** Exclude entire files/directories that should never be scanned

**Examples:**
- `.env.example$` (example files)
- `tests/fixtures/.*` (test data)
- `docs/.*\.md$` (documentation)

**Pros:** Very fast, clear exceptions, easy to understand
**Cons:** All-or-nothing (can't selectively scan within excluded files)

#### Tier 3: Fingerprint-Based (Precise)

**Location:** `.gitleaksignore`

**Purpose:** Exclude specific secret instances with full context

**Format:** `file:rule:line` or `fingerprint-hash`

**Examples:**
```
# Development SAML certificate (safe, self-signed)
acgs2-core/shared/auth/certs/sp.key:private-key:1

# Test fixture for secret validation (documented)
tests/fixtures/test_secrets.py:anthropic-api-key:42
```

**Pros:** Most precise, fully documented, minimal false negatives
**Cons:** Requires manual addition, line numbers can change

### When to Use Each Tier

**Use Pattern-Based when:**
- Placeholder follows consistent format (`dev-*`, `test-*`)
- Applies to many files across codebase
- Low risk of false negatives

**Use Path-Based when:**
- Entire file/directory should be excluded
- File contains many placeholders
- File type inherently safe (e.g., examples)

**Use Fingerprint-Based when:**
- Specific secret instance needs exception
- High-risk file but one line is safe
- Need audit trail for exception

---

## 8. Error Message Strategy

### Principle: Actionable, Educational, Not Punitive

**Bad Error Message:**
```
Secret detected in file.py line 42
```

**Good Error Message:**
```
🚫 ANTHROPIC_API_KEY detected in api_client.py:42

   Value: sk-ant-api01_ABC123...
   Risk Level: CRITICAL (AI Provider - Cost & Data Exposure)

💡 REMEDIATION STEPS:

   1. Remove secret from api_client.py

   2. Store in environment or secrets manager:
      # .env (add to .gitignore)
      ANTHROPIC_API_KEY=sk-ant-api01_ABC123...

   3. Load in code:
      from acgs2_core.shared.secrets_manager import get_secret
      api_key = get_secret("ANTHROPIC_API_KEY")

   OR if this is a development placeholder:

   1. Use safe prefix: dev-anthropic-key-placeholder

   2. Document in .gitleaksignore:
      # Development Anthropic key (not real, for local testing)
      api_client.py:anthropic-api-key:42

📚 Documentation: docs/SECRETS_DETECTION.md
```

### Error Message Components

1. **Clear Identification:** What secret, where, what line
2. **Risk Context:** Why this matters (cost, data exposure, etc.)
3. **Remediation Steps:** Exact commands to fix
4. **Alternative Path:** If it's a false positive, how to resolve
5. **Documentation Link:** Where to learn more

---

## 9. Integration with secrets_manager.py

### Single Source of Truth

**Philosophy:** Pre-commit validation should mirror runtime validation

**Implementation:**
```python
# scripts/check-secrets-pre-commit.py

# Import patterns directly from secrets_manager
from acgs2_core.shared.secrets_manager import (
    CREDENTIAL_PATTERNS,
    SECRET_CATEGORIES,
    SecretsManager
)

def validate_secret_format(name: str, value: str) -> bool:
    """Use same validation as runtime."""
    # Option 1: Use patterns directly
    pattern = CREDENTIAL_PATTERNS.get(name)
    if pattern is None:
        return True  # No pattern defined
    return bool(re.match(pattern, value))

    # Option 2: Use SecretsManager method (if accessible)
    # sm = SecretsManager()
    # return sm.validate_format(name, value)
```

### Benefits of Integration

1. **Consistency:** Pre-commit and runtime use same rules
2. **Maintainability:** Update patterns in one place
3. **Completeness:** Automatically pick up new secret types
4. **Documentation:** secrets_manager.py is source of truth

### When Patterns Change

**Workflow:**
1. Developer adds new secret type to `SECRET_CATEGORIES`
2. Developer defines pattern in `CREDENTIAL_PATTERNS`
3. Pre-commit hook automatically picks up new pattern (no update needed)
4. CI and runtime validation also updated

**Example:**
```python
# Someone adds a new secret to secrets_manager.py
CREDENTIAL_PATTERNS["DATABRICKS_TOKEN"] = r"^dapi[a-f0-9]{32}$"
SECRET_CATEGORIES["cloud"].append("DATABRICKS_TOKEN")

# Pre-commit hook automatically validates it (next commit)
# No manual updates needed to hook configuration
```

---

## 10. Phased Rollout Plan

### Phase 1: Gitleaks Pre-commit (Week 1)

**Goal:** Get basic protection in place quickly

**Tasks:**
1. Add gitleaks to `.pre-commit-config.yaml`
2. Create basic `.gitleaks.toml` with ACGS-2 rules
3. Update `.gitleaksignore` with current exceptions
4. Test on clean repository

**Success Criteria:**
- Gitleaks runs on every commit
- No false positives on current codebase
- <5s execution time

**Risk:** Low - gitleaks is mature, well-tested

### Phase 2: Custom Hook Development (Week 2)

**Goal:** Add ACGS-2-specific validation

**Tasks:**
1. Create `scripts/check-secrets-pre-commit.py`
2. Implement placeholder detection logic
3. Add integration with `secrets_manager.py`
4. Create allow-list configuration
5. Test with realistic fixtures

**Success Criteria:**
- Catches all 8 pattern-defined secrets
- Correctly identifies placeholders
- Clear error messages
- <3s execution time

**Risk:** Medium - custom code, needs thorough testing

### Phase 3: Team Onboarding (Week 3)

**Goal:** Roll out to development team

**Tasks:**
1. Create documentation (`docs/SECRETS_DETECTION.md`)
2. Update `CONTRIBUTING.md` with secrets policy
3. Create migration guide for existing developers
4. Update `init.sh` for automated setup
5. Conduct team training session

**Success Criteria:**
- All developers have hooks installed
- <5 questions per developer
- No workflow blockers

**Risk:** Medium - change management, requires good docs

### Phase 4: Validation & Refinement (Week 4)

**Goal:** Validate effectiveness, tune for false positives

**Tasks:**
1. Collect metrics on hook performance
2. Review false positives from first week
3. Refine allow-lists based on feedback
4. Add additional tests for edge cases
5. Ensure CI consistency

**Success Criteria:**
- <1% false positive rate
- <5s average commit time
- Team satisfaction >80%
- Zero secrets reach main branch

**Risk:** Low - refinement phase

---

## 11. Success Metrics

### Security Metrics

**Primary:**
- **Zero secrets in git history** (after rollout)
- **100% detection rate** for pattern-defined secrets
- **<1% false positive rate**

**Secondary:**
- Number of secrets caught per week
- Time to detection (pre-commit vs CI)
- Secret types caught (categorized)

### Performance Metrics

**Primary:**
- **Average commit time:** <5s (target: <3s)
- **P95 commit time:** <10s
- **P99 commit time:** <15s

**Secondary:**
- Gitleaks execution time
- Custom hook execution time
- Time by file count

### Developer Experience Metrics

**Primary:**
- **Team satisfaction:** >80% positive
- **False positives per week:** <5
- **Time to resolve findings:** <5 minutes average

**Secondary:**
- Number of `.gitleaksignore` additions per week
- Hook bypass attempts (should be zero)
- Documentation views/week

### Monitoring Dashboard

**Collect data on:**
```python
{
  "date": "2026-01-03",
  "commits": 47,
  "secrets_caught": 2,
  "false_positives": 1,
  "avg_time_gitleaks": 2.3,
  "avg_time_custom": 1.1,
  "avg_time_total": 3.4,
  "p95_time": 6.2,
  "team_bypass_rate": 0.0
}
```

---

## 12. Contingency Plans

### Scenario 1: Hooks Too Slow

**If commit time >10s regularly:**

**Immediate Actions:**
1. Reduce file scope (exclude more file types)
2. Enable fail-fast mode (exit on first finding)
3. Optimize custom hook (profile and fix bottlenecks)

**Long-term Solutions:**
1. Incremental scanning (only changed lines)
2. Parallel execution optimization
3. Consider async/background scanning

### Scenario 2: Too Many False Positives

**If false positive rate >5%:**

**Immediate Actions:**
1. Review and refine placeholder patterns
2. Add file-specific exceptions
3. Improve error messages for common false positives

**Long-term Solutions:**
1. Machine learning for placeholder detection
2. Whitelist known-safe entropy patterns
3. Context-aware validation

### Scenario 3: Developer Pushback

**If team satisfaction <60%:**

**Immediate Actions:**
1. Collect specific feedback on pain points
2. Improve documentation and examples
3. Provide easy bypass for emergencies (with logging)

**Long-term Solutions:**
1. Automated allow-list suggestions
2. One-click remediation tools
3. Integration with IDE for pre-commit feedback

### Scenario 4: Hook Bypass

**If developers routinely use `--no-verify`:**

**Immediate Actions:**
1. Understand why (performance? false positives?)
2. Address root cause
3. Ensure CI still catches bypassed secrets

**Long-term Solutions:**
1. Make hooks so fast/accurate that bypass is unnecessary
2. Team culture: explain why secrets detection matters
3. Metrics/alerts on bypass rate

---

## 13. Acceptance Criteria Met

✅ **Documented hook strategy with rationale**
- Multi-layered approach defined (gitleaks + custom hook)
- Rationale for each layer explained
- Defense-in-depth architecture documented

✅ **List of files/patterns to scan vs exclude**
- High/medium/low priority files categorized
- Explicit inclusion and exclusion lists
- File-type-specific scanning strategies

✅ **Performance considerations documented**
- Target metrics defined (<5s commits)
- 6 optimization strategies detailed
- Performance monitoring approach specified

---

## 14. Next Steps

**Immediate (Subtask 2.1):**
1. Implement gitleaks pre-commit configuration
2. Create `.gitleaks.toml` with ACGS-2 rules
3. Test on current repository state

**Short-term (Phase 2):**
1. Develop custom hook script
2. Implement placeholder detection
3. Create comprehensive tests

**Long-term (Phases 3-4):**
1. Team onboarding and training
2. Documentation and migration guides
3. Monitoring and continuous improvement

---

## 15. Conclusion

This multi-layered hook strategy provides **defense-in-depth** protection against accidental secret commits while maintaining excellent developer experience. By combining industry-standard gitleaks with ACGS-2-specific custom validation, we achieve comprehensive coverage without sacrificing performance or usability.

**Key Principles:**
1. **Security without friction** - Fast, accurate detection
2. **Actionable feedback** - Clear error messages with remediation steps
3. **Consistency** - Pre-commit mirrors runtime validation
4. **Maintainability** - Single source of truth in `secrets_manager.py`
5. **Continuous improvement** - Metrics-driven refinement

The strategy balances security requirements with practical developer workflows, ensuring secrets protection becomes a natural, unobtrusive part of the development process.
