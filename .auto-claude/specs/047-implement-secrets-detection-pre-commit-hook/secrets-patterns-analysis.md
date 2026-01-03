# Secrets Manager Patterns Analysis

**Date:** 2026-01-03
**Subtask:** 1.2 - Review secrets_manager.py patterns
**Status:** Complete

## Executive Summary

This document extracts and analyzes all credential validation patterns from `secrets_manager.py` to inform pre-commit hook configuration. It provides a comprehensive mapping of what constitutes valid vs invalid secrets and how to distinguish placeholders from real credentials.

---

## 1. CREDENTIAL_PATTERNS Extraction

**Source:** `acgs2-core/shared/secrets_manager.py` (lines 33-42)

### Complete Pattern List

| Secret Name | Regex Pattern | Description | Example Format |
|-------------|---------------|-------------|----------------|
| `CLAUDE_CODE_OAUTH_TOKEN` | `^sk-ant-oat\d{2}-[A-Za-z0-9_-]{60,}$` | Claude Code OAuth token with numeric version | `sk-ant-oat01-ABCdef...` (60+ chars) |
| `OPENAI_API_KEY` | `^sk-[A-Za-z0-9]{20,}$` | OpenAI API key with standard prefix | `sk-ABCdef123...` (20+ chars) |
| `OPENROUTER_API_KEY` | `^sk-or-v1-[A-Za-z0-9]{60,}$` | OpenRouter API key with version prefix | `sk-or-v1-ABCdef...` (60+ chars) |
| `HF_TOKEN` | `^hf_[A-Za-z0-9]{30,}$` | HuggingFace token with standard prefix | `hf_ABCdef123...` (30+ chars) |
| `ANTHROPIC_API_KEY` | `^sk-ant-[A-Za-z0-9_-]{80,}$` | Anthropic API key with extended format | `sk-ant-ABCdef...` (80+ chars) |
| `AWS_ACCESS_KEY_ID` | `^AKIA[A-Z0-9]{16}$` | AWS access key with standard AKIA prefix | `AKIAIOSFODNN7EXAMPLE` (20 chars) |
| `JWT_SECRET` | `^[A-Fa-f0-9]{64}$` | JWT secret as 64-character hex string | `a1b2c3d4e5f6...` (64 hex chars) |
| `VAULT_TOKEN` | `^(hvs\.|s\.)[A-Za-z0-9]{20,}$` | HashiCorp Vault token with prefix | `hvs.ABC123...` or `s.ABC123...` (20+ chars) |

### Pattern Analysis

**AI Provider Keys (5 patterns):**
- All use prefix-based identification (`sk-`, `hf_`, `sk-ant-`, etc.)
- Length requirements range from 20 to 80+ characters
- Allow alphanumeric, underscore, and hyphen characters
- Highly specific to prevent false positives

**Infrastructure Keys (2 patterns):**
- AWS: Fixed-length (20 chars), strict format `AKIA[A-Z0-9]{16}`
- Vault: Variable-length (20+ chars), two possible prefixes (`hvs.` or `s.`)

**Security Keys (1 pattern):**
- JWT: Exactly 64 hexadecimal characters
- No prefix, pure hex format
- Used for signing/verifying tokens

---

## 2. SECRET_CATEGORIES Organization

**Source:** `acgs2-core/shared/secrets_manager.py` (lines 45-69)

### Category Breakdown

#### `ai_providers` (5 secrets)
Secrets for external AI service authentication:
- `CLAUDE_CODE_OAUTH_TOKEN` - Claude Code integration
- `OPENAI_API_KEY` - OpenAI GPT models
- `OPENROUTER_API_KEY` - OpenRouter aggregator
- `HF_TOKEN` - HuggingFace models/datasets
- `ANTHROPIC_API_KEY` - Anthropic Claude API

**Risk Level:** HIGH
- Direct cost implications (API usage billing)
- Potential for unauthorized AI model access
- May expose training data or model queries

#### `security` (3 secrets)
Core application security credentials:
- `JWT_SECRET` - JSON Web Token signing key ✅ (has pattern)
- `API_KEY_INTERNAL` - Internal service authentication ❌ (no pattern)
- `AUDIT_SIGNATURE_KEY` - Audit log signatures ❌ (no pattern)

**Risk Level:** CRITICAL
- JWT_SECRET compromise = complete authentication bypass
- API_KEY_INTERNAL leak = inter-service security breach
- Audit tampering if signature key exposed

**Note:** Only `JWT_SECRET` has a validation pattern. `API_KEY_INTERNAL` and `AUDIT_SIGNATURE_KEY` lack defined patterns.

#### `infrastructure` (4 secrets)
Infrastructure service credentials:
- `VAULT_TOKEN` - HashiCorp Vault access ✅ (has pattern)
- `REDIS_PASSWORD` - Redis authentication ❌ (no pattern)
- `DB_USER_PASSWORD` - Database credentials ❌ (no pattern)
- `KAFKA_SASL_PASSWORD` - Kafka SASL auth ❌ (no pattern)

**Risk Level:** HIGH
- Database access = data breach potential
- Vault compromise = all secrets exposed
- Kafka/Redis = system availability impact

#### `cloud` (3 secrets)
Cloud and blockchain credentials:
- `AWS_ACCESS_KEY_ID` - AWS authentication ✅ (has pattern)
- `AWS_SECRET_ACCESS_KEY` - AWS secret key ❌ (no pattern)
- `BLOCKCHAIN_PRIVATE_KEY` - Blockchain signing ❌ (no pattern)

**Risk Level:** CRITICAL
- AWS keys = infrastructure control, cost implications
- Blockchain keys = financial/asset control
- Permanent damage potential if leaked

### Pattern Coverage Analysis

**Total Secrets:** 15
**With Patterns:** 8 (53%)
**Without Patterns:** 7 (47%)

**Secrets Missing Patterns:**
1. `API_KEY_INTERNAL` (security)
2. `AUDIT_SIGNATURE_KEY` (security)
3. `REDIS_PASSWORD` (infrastructure)
4. `DB_USER_PASSWORD` (infrastructure)
5. `KAFKA_SASL_PASSWORD` (infrastructure)
6. `AWS_SECRET_ACCESS_KEY` (cloud)
7. `BLOCKCHAIN_PRIVATE_KEY` (cloud)

**Implication for Hook Design:**
- Custom hook can validate 8 secrets with strict patterns
- Need generic detection rules for the 7 secrets without patterns
- Gitleaks default rules should catch some (e.g., generic API keys, passwords)
- Consider adding patterns for critical missing secrets

---

## 3. Valid vs Invalid Secret Formats

### Valid Secret Format Criteria

A secret is considered **VALID** if it matches one of these conditions:

1. **Matches Defined Pattern:** Conforms to regex in `CREDENTIAL_PATTERNS`
   ```python
   # Example: Valid ANTHROPIC_API_KEY
   "sk-ant-api01_ABC123xyz_abc-XYZ-789_..." # 80+ chars, matches pattern
   ```

2. **Pattern Not Defined:** No validation pattern exists (auto-passes validation)
   ```python
   # Example: API_KEY_INTERNAL (no pattern defined)
   "any-string-here" # Would pass validate_format() but may be caught by gitleaks
   ```

### Invalid Secret Format Examples

A secret is considered **INVALID** if:

1. **Pattern exists but doesn't match:**
   ```python
   # Invalid OPENAI_API_KEY (missing 'sk-' prefix)
   "abc123def456..."  # Missing required prefix

   # Invalid JWT_SECRET (not 64 hex chars)
   "short-secret-123"  # Not hexadecimal, wrong length

   # Invalid AWS_ACCESS_KEY_ID (wrong prefix)
   "ASIA123456789012345"  # Should be AKIA, not ASIA
   ```

2. **Length requirements not met:**
   ```python
   # Invalid ANTHROPIC_API_KEY (too short)
   "sk-ant-short"  # Requires 80+ chars after prefix

   # Invalid HF_TOKEN (too short)
   "hf_abc"  # Requires 30+ chars after prefix
   ```

3. **Character set violations:**
   ```python
   # Invalid JWT_SECRET (non-hex characters)
   "g1h2i3j4k5l6..."  # g, h, i, j, k, l are not hex digits

   # Invalid AWS_ACCESS_KEY_ID (lowercase)
   "AKIAabcdefgh12345678"  # Must be uppercase only
   ```

### Edge Cases

**Partial Matches:**
```python
# These look like secrets but fail validation:
"sk-ant-oat-ABC123..."  # Missing numeric version (oat\d{2})
"sk-or-v2-ABC123..."    # Wrong version (expects v1)
"hvs-ABC123..."         # Missing period (expects hvs.)
```

---

## 4. Placeholder vs Real Secret Identification

### Placeholder Patterns Observed in Codebase

**From `.env.dev`:**
```bash
JWT_SECRET=dev-jwt-secret-min-32-chars-required  # Development placeholder
REDIS_PASSWORD=dev_password                      # Simple dev password
POSTGRES_ML_PASSWORD=mlflow_password             # Service-specific dev password
```

**From `.env.example`:**
```bash
REDIS_PASSWORD=                                  # Empty (no default)
KAFKA_PASSWORD=                                  # Empty (requires user input)
```

**From service `.env.example` (commented):**
```bash
# API_KEY_INTERNAL=your-secure-api-key          # Instructional placeholder
# JWT_SECRET=your-jwt-secret-min-32-chars       # Instructional placeholder
```

### Placeholder Classification Rules

#### Category 1: Prefix-Based Placeholders (SAFE)
Starts with development/test indicators:
- `dev-*` (e.g., `dev-jwt-secret-min-32-chars-required`)
- `test-*` (e.g., `test-api-key-placeholder`)
- `development-*`
- `local-*`
- `placeholder-*`

#### Category 2: Instructional Placeholders (SAFE)
Contains instructional text:
- `your-*` (e.g., `your-api-key-here`)
- `<*>` (e.g., `<your-key-here>`)
- `*-example` (e.g., `jwt-secret-example`)
- `*-placeholder`
- `*-template`

#### Category 3: Simple Known-Safe Passwords (SAFE - with caution)
Common development passwords (ONLY in .env.dev or .env.example):
- `dev_password`
- `password`
- `admin` (if in development context)
- Service-specific: `mlflow_password`, `acgs2_pass`

**Caveat:** These should ONLY be allowed in specific files:
- `.env.dev`
- `.env.example`
- Service-specific `.env.example` files
- Test fixtures

#### Category 4: Empty/Missing Values (SAFE)
No value provided:
- `SECRET_NAME=` (empty string)
- Commented-out variables

#### Category 5: Redacted/Masked Values (SAFE)
Documentation examples:
- `sk-ant-XXX...XXX` (masked with X)
- `***hidden***`
- `[REDACTED]`
- `<hidden>` or `<secret>`

### Real Secret Indicators (DANGEROUS)

A value is likely a **REAL SECRET** if:

1. **Matches pattern AND doesn't match placeholder rules**
   ```bash
   # REAL - matches pattern, no placeholder indicator
   ANTHROPIC_API_KEY=sk-ant-api01_ABC123xyz_abc-XYZ-789...
   ```

2. **High entropy AND meaningful length**
   ```bash
   # REAL - 32+ random-looking characters
   JWT_SECRET=a1b2c3d4e5f6789abcdef0123456789a1b2c3d4e5f6789abcdef0123456789
   ```

3. **Base64-encoded blobs**
   ```bash
   # REAL - Base64 pattern with sufficient length
   API_KEY=dGhpc2lzYXNlY3JldGtleXRoYXRpc2Jhc2U2NGVuY29kZWQ=
   ```

4. **In files that shouldn't contain secrets**
   ```bash
   # DANGEROUS - secrets in committed Python files
   # my_service.py
   OPENAI_KEY = "sk-abc123def456..."  # Hardcoded in source
   ```

### Detection Logic for Pre-commit Hook

```python
def is_placeholder(secret_name: str, secret_value: str, file_path: str) -> bool:
    """
    Determine if a secret value is a safe placeholder.

    Returns True if safe to commit, False if likely real secret.
    """
    # Category 1: Prefix-based placeholders
    placeholder_prefixes = ['dev-', 'test-', 'development-', 'local-', 'placeholder-', 'your-']
    if any(secret_value.startswith(prefix) for prefix in placeholder_prefixes):
        return True

    # Category 2: Instructional patterns
    instructional_patterns = ['<', '>', 'example', 'template', 'your-']
    if any(pattern in secret_value.lower() for pattern in instructional_patterns):
        return True

    # Category 3: Simple known-safe passwords (only in .env.example/.env.dev)
    safe_files = ['.env.example', '.env.dev', 'tests/']
    if any(safe_file in file_path for safe_file in safe_files):
        known_safe = ['dev_password', 'password', 'acgs2_pass', 'mlflow_password']
        if secret_value in known_safe:
            return True

    # Category 4: Empty values
    if not secret_value or secret_value.strip() == '':
        return True

    # Category 5: Redacted/masked
    redaction_indicators = ['XXX', '***', '[REDACTED]', '<hidden>', '<secret>']
    if any(indicator in secret_value for indicator in redaction_indicators):
        return True

    # If none of the above, likely a real secret
    return False
```

---

## 5. Pattern-to-Gitleaks Rule Mapping

### Custom Gitleaks Rules Needed

For secrets with defined patterns, we can create precise gitleaks rules:

```toml
# .gitleaks.toml custom rules for ACGS-2

# Anthropic API Key (not in default gitleaks)
[[rules]]
id = "anthropic-api-key"
description = "Anthropic API Key"
regex = '''sk-ant-[A-Za-z0-9_-]{80,}'''
keywords = ["sk-ant-"]

# Claude Code OAuth Token (not in default gitleaks)
[[rules]]
id = "claude-code-oauth-token"
description = "Claude Code OAuth Token"
regex = '''sk-ant-oat\d{2}-[A-Za-z0-9_-]{60,}'''
keywords = ["sk-ant-oat"]

# OpenRouter API Key (not in default gitleaks)
[[rules]]
id = "openrouter-api-key"
description = "OpenRouter API Key"
regex = '''sk-or-v1-[A-Za-z0-9]{60,}'''
keywords = ["sk-or-v1-"]

# HuggingFace Token (may exist in gitleaks, but ensure coverage)
[[rules]]
id = "huggingface-token"
description = "HuggingFace API Token"
regex = '''hf_[A-Za-z0-9]{30,}'''
keywords = ["hf_"]
```

### Allowlist Patterns for Placeholders

```toml
# .gitleaks.toml allowlist section

[allowlist]
description = "Allowlist for development placeholders"

# Development placeholders
regexes = [
  '''dev-jwt-secret-min-32-chars-required''',
  '''dev-.*-placeholder''',
  '''test-.*''',
  '''your-.*''',
  '''<.*>''',
  '''.*-example''',
]

# Specific paths to exclude
paths = [
  '''.env.example$''',
  '''.env.template$''',
  '''tests/fixtures/.*''',
  '''docs/.*\.md$''',
]
```

---

## 6. Secrets Without Patterns - Generic Detection Strategy

For the 7 secrets without defined patterns, rely on gitleaks generic rules:

| Secret Name | Gitleaks Default Rule | Detection Quality |
|-------------|----------------------|-------------------|
| `API_KEY_INTERNAL` | generic-api-key | Medium (many false positives) |
| `AUDIT_SIGNATURE_KEY` | generic-api-key | Medium |
| `REDIS_PASSWORD` | generic-password / connection-string | Low (common word) |
| `DB_USER_PASSWORD` | generic-password / connection-string | Medium (in DB URLs) |
| `KAFKA_SASL_PASSWORD` | generic-password | Low |
| `AWS_SECRET_ACCESS_KEY` | aws-secret-access-key | ✅ HIGH (standard rule) |
| `BLOCKCHAIN_PRIVATE_KEY` | private-key / generic-api-key | Medium |

**Recommendations:**
1. Keep generic gitleaks rules enabled for baseline coverage
2. Add custom patterns for high-risk secrets (BLOCKCHAIN_PRIVATE_KEY)
3. Document known false positives in .gitleaksignore
4. Consider adding patterns to secrets_manager.py for better validation

---

## 7. File-Specific Secret Handling

### Files That Should Allow "Secrets" (with restrictions)

**`.env.example` files:**
- MUST contain only placeholders or empty values
- Pre-commit hook should validate: no pattern-matching real secrets
- Allow: `dev-*`, `your-*`, `<...>`, empty values

**`.env.dev` file:**
- SHOULD contain only development-safe values
- Current values: `dev-jwt-secret-min-32-chars-required`, `dev_password`, etc.
- Pre-commit hook should warn but allow explicitly listed placeholders

**Test fixtures (`tests/fixtures/**`):**
- May contain example secrets for testing validation logic
- Should be excluded from scanning OR use allowlist fingerprints

**Documentation (`docs/**`, `*.md`):**
- Often contains redacted examples
- Allow masked formats: `sk-ant-XXX...XXX`

### Files That Should NEVER Contain Secrets

**Source code (`**/*.py`, `**/*.ts`, `**/*.js`):**
- BLOCK all pattern-matching secrets
- No exceptions (use environment variables or secrets manager)

**Production config (`*.env.production`, `*.env.prod`):**
- Should NOT be in repository at all
- Add to `.gitignore` if found

**Docker files (`Dockerfile`, `docker-compose*.yml`):**
- BLOCK hardcoded secrets
- Allow only placeholders or environment variable references

---

## 8. Validation Method Integration

### From secrets_manager.py

**Method:** `validate_format(name: str, value: str) -> bool` (lines 252-266)

```python
def validate_format(self, name: str, value: str) -> bool:
    """
    Validate credential format against known patterns.

    Returns:
        True if valid or no pattern defined, False if invalid
    """
    pattern = CREDENTIAL_PATTERNS.get(name)
    if pattern is None:
        return True  # No pattern = auto-pass
    return bool(re.match(pattern, value))
```

**Usage in Pre-commit Hook:**
```python
# Import patterns from secrets_manager
from acgs2-core.shared.secrets_manager import CREDENTIAL_PATTERNS, SECRET_CATEGORIES

def check_secret_in_file(file_path: str):
    """Check file for secrets using CREDENTIAL_PATTERNS."""
    for line in read_file(file_path):
        for secret_name, pattern in CREDENTIAL_PATTERNS.items():
            if re.search(pattern, line):
                if not is_placeholder(secret_name, match.group(), file_path):
                    report_secret_found(secret_name, file_path, line)
```

---

## 9. Summary and Recommendations

### Key Findings

1. **8 of 15 secrets have strict validation patterns** - these can be precisely detected
2. **7 secrets lack patterns** - rely on gitleaks generic rules
3. **Placeholder patterns are consistent** - `dev-*`, `your-*`, `<...>` format
4. **Development secrets are well-documented** - `.env.dev` uses clear placeholders

### Recommendations for Hook Configuration

#### Phase 1: Gitleaks Configuration
1. Add custom rules for AI provider keys (Anthropic, OpenRouter, Claude Code)
2. Enable default rules for AWS, OpenAI, HuggingFace
3. Add allowlist patterns for `dev-*`, `test-*`, `your-*` placeholders
4. Exclude `.env.example`, `tests/fixtures/`, `docs/` paths

#### Phase 2: Custom Hook
1. Import `CREDENTIAL_PATTERNS` directly from `secrets_manager.py`
2. Implement placeholder detection using observed patterns
3. Provide clear error messages referencing secret categories
4. Use `validate_format()` method for consistency with runtime validation

#### Phase 3: Documentation
1. Document each allowed placeholder pattern with examples
2. Create guide for adding new secrets to `CREDENTIAL_PATTERNS`
3. Establish process for reviewing .env.dev values
4. Provide remediation steps for secret findings

---

## Acceptance Criteria Met

✅ **List of all credential patterns from secrets_manager.py**
- Documented all 8 patterns with regex, examples, and descriptions
- Identified 7 additional secrets without patterns

✅ **Understanding of what constitutes a valid vs invalid secret format**
- Defined validation criteria with examples
- Documented edge cases and pattern violations
- Explained auto-pass behavior for undefined patterns

✅ **Identification of placeholder vs real secrets**
- Categorized 5 types of safe placeholders
- Established detection logic with code examples
- Analyzed real secret indicators
- Provided file-specific handling rules

---

## Next Steps

Proceed to **Subtask 1.3: Design hook strategy** with this information to:
1. Design multi-layered detection approach
2. Balance security with developer experience
3. Plan performance optimizations
4. Document integration points with secrets_manager.py
