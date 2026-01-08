# ACGS-2 Secrets Detection

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

> **Version**: 1.0.0
> **Last Updated**: 2026-01-03
> **Status**: Active

This document explains how ACGS-2 protects against accidental secret commits through automated pre-commit hooks and what to do when secrets are detected.

## Overview

ACGS-2 implements a **multi-layered secrets detection system** to prevent accidental exposure of sensitive credentials:

1. **Gitleaks** - Industry-standard secret scanning (140+ built-in rules)
2. **ACGS-2 Custom Hook** - Project-specific pattern validation using `secrets_manager.py`
3. **CI/CD Validation** - Additional scanning in GitHub Actions workflow

This defense-in-depth approach catches secrets before they enter git history, where they are difficult to remove and may be exposed in public repositories.

---

## What Secrets Are Detected

### 1. AI Provider Credentials

| Secret Type | Pattern | Example (Invalid) |
|-------------|---------|-------------------|
| **Anthropic API Key** | `sk-ant-[A-Za-z0-9_-]{80,}` | `sk-ant-api03-abc123...` |
| **Claude Code OAuth Token** | `sk-ant-oat\d{2}-[A-Za-z0-9_-]{60,}` | `sk-ant-oat01-xyz789...` |
| **OpenRouter API Key** | `sk-or-v1-[A-Za-z0-9]{60,}` | `sk-or-v1-abc123xyz...` |
| **HuggingFace Token** | `hf_[A-Za-z0-9]{30,}` | `hf_AbCdEfGhIjKlMnOpQr...` |
| **OpenAI API Key** | `sk-[A-Za-z0-9]{20,}` | `sk-proj-abc123xyz789...` |

### 2. Infrastructure Secrets

| Secret Type | Pattern | Example (Invalid) |
|-------------|---------|-------------------|
| **AWS Access Key ID** | `AKIA[A-Z0-9]{16}` | `AKIAIOSFODNN7EXAMPLE` |
| **JWT Secret** | `[A-Fa-f0-9]{64}` (hex) | `a1b2c3d4...` (64 chars) |
| **Vault Token** | `(hvs\.|s\.)[A-Za-z0-9]{20,}` | `hvs.abc123xyz789...` |

### 3. Generic Patterns

Gitleaks also detects 140+ generic secret patterns including:
- Database passwords (PostgreSQL, MySQL, MongoDB)
- Private keys (SSH, PGP, TLS certificates)
- GitHub tokens, GitLab tokens
- Slack webhooks, Discord webhooks
- Cloud provider credentials (Azure, GCP)
- And many more...

**Full Gitleaks Rules**: [https://github.com/gitleaks/gitleaks](https://github.com/gitleaks/gitleaks)

---

## Safe vs Unsafe Secrets

### ✅ Safe Secrets (Allowed)

These patterns are **safe to commit** and will not trigger detection:

#### Development Placeholders
```bash
# Prefix-based placeholders
JWT_SECRET=dev-jwt-secret-min-32-chars-required
API_KEY=test-api-key-for-development-only
DATABASE_PASSWORD=your-database-password-here

# Instructional markers
OPENAI_API_KEY=<your-openai-key-here>
AWS_SECRET=***REDACTED***
REDIS_PASSWORD=example_password

# Known safe development values (from .env.dev)
REDIS_PASSWORD=dev_password
POSTGRES_ML_PASSWORD=mlflow_password
JWT_SECRET=dev-jwt-secret-min-32-chars-required
```

#### Example and Template Files
```bash
# These files are automatically excluded from strict scanning:
.env.example
.env.template
.env.dev
docs/*.md
tests/fixtures/**
**/example.*
**/template.*
```

### ❌ Unsafe Secrets (Blocked)

These patterns will **trigger detection** and block commits:

```bash
# Real AI provider keys
ANTHROPIC_API_KEY=sk-ant-api03-JqPxY8zN2vWmKlRtHgFdCbV...
OPENAI_API_KEY=sk-proj-abc123xyz789def456ghi...
HF_TOKEN=hf_AbCdEfGhIjKlMnOpQrStUvWxYz...

# Real infrastructure credentials
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
JWT_SECRET=a1b2c3d4e5f6...  # 64-char hex string
VAULT_TOKEN=hvs.CAESIJ1n9eF3...

# Database credentials with real-looking values
DATABASE_PASSWORD=P@ssw0rd123!
REDIS_PASSWORD=superSecretPassword2024
```

---

## How It Works

### Detection Layers

```
┌─────────────────────────────────────────────────────────┐
│  1. Pre-commit Hook (Local)                             │
│     ├─ Gitleaks (140+ industry patterns)                │
│     └─ ACGS-2 Custom Hook (project-specific patterns)   │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  2. CI/CD Pipeline (GitHub Actions)                     │
│     └─ Gitleaks full repository scan                    │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  3. Runtime Validation (Production)                     │
│     └─ secrets_manager.py validates credential formats  │
└─────────────────────────────────────────────────────────┘
```

### Integration with secrets_manager.py

The custom ACGS-2 hook uses `CREDENTIAL_PATTERNS` from `src/core/shared/secrets_manager.py` as its **single source of truth**. This ensures:

1. **Consistency**: Same patterns used for validation at commit-time and runtime
2. **Maintainability**: Update patterns in one place
3. **Type Safety**: Leverages Python's type system for pattern definitions

```python
# From secrets_manager.py - used by both hooks and runtime validation
CREDENTIAL_PATTERNS = {
    "CLAUDE_CODE_OAUTH_TOKEN": r"^sk-ant-oat\d{2}-[A-Za-z0-9_-]{60,}$",
    "OPENAI_API_KEY": r"^sk-[A-Za-z0-9]{20,}$",
    "ANTHROPIC_API_KEY": r"^sk-ant-[A-Za-z0-9_-]{80,}$",
    # ... 8 total patterns
}
```

---

## When Secrets Are Detected

### What You'll See

When a secret is detected during commit, you'll see an error message like:

```bash
❌ ACGS-2 Secrets Detection Failed!

Found potential secrets in your commit:

  File: .env
  Category: ai_providers
  Pattern: ANTHROPIC_API_KEY

  ⚠️  SECURITY RISK: Real credential detected
      Value matches pattern: sk-ant-[A-Za-z0-9_-]{80,}

REMEDIATION OPTIONS:

  Option 1: Use environment variables + secrets_manager.py (RECOMMENDED)
    - Store secrets in Vault or encrypted local storage
    - Reference via environment variables
    - See: src/core/shared/secrets_manager.py

  Option 2: Use safe placeholder prefixes
    - dev-*, test-*, your-*, example-*, sample-*
    - Example: ANTHROPIC_API_KEY=dev-anthropic-key-here

  Option 3: Add to .gitleaksignore (ONLY IF JUSTIFIED)
    - Run: gitleaks detect --no-git
    - Add fingerprint to .gitleaksignore with justification
    - Requires code review approval

For more info: docs/SECRETS_DETECTION.md
```

---

## Resolving False Positives

### Step 1: Verify It's Actually a False Positive

Before adding exceptions, confirm the value is **truly safe**:

```bash
# Ask yourself:
✓ Is this a development placeholder? (dev-*, test-*, etc.)
✓ Is this in an example/template file?
✓ Is this already public/documented?
✓ Will this NEVER be used in production?

# If any answer is "no", it's likely NOT a false positive
```

### Step 2: Choose the Right Solution

#### Solution A: Use Development Placeholders (Preferred)

Update your values to use safe prefixes:

```bash
# Before (triggers detection)
JWT_SECRET=mysecret123

# After (passes detection)
JWT_SECRET=dev-jwt-secret-min-32-chars-required
```

**Why this is best**: Makes it obvious the value is not for production use.

#### Solution B: Add to Allow-list Configuration

For project-wide exceptions, update `.secrets-allowlist.yaml`:

```yaml
known_safe_values:
  development:
    - value: "my-development-value"
      context: "Used in docker-compose.dev.yml"
      why_safe: "Development-only, never used in production"
      production_mitigation: "Production uses Vault-managed secrets"
```

**Why this is good**: Documents the exception with context and justification.

#### Solution C: Add to .gitleaksignore (Last Resort)

For gitleaks-specific exceptions, use fingerprints:

```bash
# 1. Generate the fingerprint
gitleaks detect --no-git --verbose

# 2. Copy the fingerprint from output
# Example: abc123:path/to/file:rule-id:12

# 3. Add to .gitleaksignore with documentation
echo "# SAML development certificate (safe to commit)" >> .gitleaksignore
echo "abc123:config/sp.crt:generic-api-key:42" >> .gitleaksignore
```

**Why this is last resort**: Fingerprints are file/line-specific and break when content changes.

### Step 3: Test Your Changes

```bash
# Test the custom ACGS-2 hook
python scripts/check-secrets-pre-commit.py --verbose

# Test gitleaks
gitleaks protect --staged --verbose

# Run all pre-commit hooks
pre-commit run --all-files
```

### Step 4: Document Your Exception

Always add a comment explaining why the exception is safe:

```bash
# .gitleaksignore
# SAML development certificate - public test cert, not used in production
abc123:config/sp.crt:generic-api-key:42

# Development JWT secret - placeholder value, production uses Vault
def456:config/.env.dev:jwt:15
```

---

## Best Practices

### DO ✅

- **Use placeholder prefixes** (`dev-*`, `test-*`, `your-*`) for development values
- **Store real secrets** in Vault or encrypted storage (use `secrets_manager.py`)
- **Add context** when creating exceptions (explain why it's safe)
- **Review exceptions** during code review
- **Keep .env.example** updated with placeholder patterns
- **Test hooks** before committing sensitive changes

### DON'T ❌

- **Don't commit** real API keys, tokens, or passwords
- **Don't disable** hooks to bypass detection (security risk!)
- **Don't add exceptions** without justification
- **Don't use** production secrets in development environments
- **Don't share** `.env` files (use `.env.example` instead)
- **Don't skip** pre-commit hooks with `--no-verify`

---

## Troubleshooting

### Issue: Hook Fails on Legitimate Placeholder

**Symptom**: Hook blocks a placeholder like `your-api-key-here`

**Solution**: The placeholder should already be allowed. If not:

```bash
# Check if it matches allowed patterns
python scripts/check-secrets-pre-commit.py --verbose

# If needed, add to .secrets-allowlist.yaml
# Under placeholder_patterns.prefixes or known_safe_values
```

### Issue: Hook Fails on Example File

**Symptom**: Hook blocks content in `.env.example` or `docs/`

**Solution**: These should be auto-excluded. Verify the file name:

```bash
# These patterns are excluded:
.env.example
.env.template
*.example.*
docs/**/*.md
tests/fixtures/**
```

If your file doesn't match, either:
- Rename it to match the pattern (e.g., `config.example.yaml`)
- Add the path to `.secrets-allowlist.yaml` under `excluded_paths`

### Issue: Need to Commit a Real Secret Temporarily

**Symptom**: You have a legitimate reason to commit a secret (e.g., test fixture)

**Solution**:

1. **Best**: Use a placeholder and load real value from environment
   ```python
   # test_auth.py
   test_key = os.getenv("TEST_API_KEY", "test-placeholder-key")
   ```

2. **If you must**: Add to `.gitleaksignore` with clear documentation
   ```bash
   # Test fixture API key - expired, only for test_auth.py unit tests
   # Key expired on 2025-01-01, safe to commit
   abc123:tests/fixtures/test_key.txt:generic-api-key:5
   ```

### Issue: Hook is Too Slow

**Symptom**: Pre-commit hooks take >5 seconds

**Solution**: Check performance settings:

```bash
# The hooks only scan staged files, not full history
# If slow, check file sizes:
git diff --cached --stat

# Very large files may need exclusion
# Add to .secrets-allowlist.yaml:
# performance:
#   max_file_size_kb: 500
```

### Issue: Pattern Not Detected

**Symptom**: A secret pattern is not being caught

**Solution**:

1. Check if pattern is in `secrets_manager.py`:
   ```bash
   grep "CREDENTIAL_PATTERNS" src/core/shared/secrets_manager.py
   ```

2. If missing, add to `secrets_manager.py` (will auto-sync to hook):
   ```python
   CREDENTIAL_PATTERNS = {
       "MY_NEW_SECRET": r"^my-pattern-[A-Za-z0-9]+$",
       # ...
   }
   ```

3. Test the updated pattern:
   ```bash
   python scripts/check-secrets-pre-commit.py --verbose
   ```

---

## Configuration Files Reference

### .gitleaks.toml
- **Purpose**: Gitleaks configuration with ACGS-2 custom rules
- **Location**: `./.gitleaks.toml`
- **Contains**: 8 custom ACGS-2 rules + global allowlist patterns
- **Update when**: Adding new AI provider integrations

### .gitleaksignore
- **Purpose**: Fingerprint-based exceptions for gitleaks
- **Location**: `./.gitleaksignore`
- **Contains**: Documented exceptions with justifications
- **Update when**: You have a file/line-specific exception

### .secrets-allowlist.yaml
- **Purpose**: ACGS-2 custom hook configuration
- **Location**: `./.secrets-allowlist.yaml`
- **Contains**: Three-tier allow-list (pattern/path/value)
- **Update when**: Adding project-wide placeholder patterns

### secrets_manager.py
- **Purpose**: Source of truth for credential patterns
- **Location**: `src/core/shared/secrets_manager.py`
- **Contains**: `CREDENTIAL_PATTERNS` dict with validation regexes
- **Update when**: Adding new secret types to ACGS-2

---

## Getting Help

### Quick Reference

```bash
# Check what secrets would be detected
gitleaks detect --no-git --verbose

# Run custom hook manually
python scripts/check-secrets-pre-commit.py --verbose

# Test all pre-commit hooks
pre-commit run --all-files

# View hook configuration
cat .pre-commit-config.yaml

# View allow-list configuration
cat .secrets-allowlist.yaml
```

### Documentation Links

- **Allow-list Configuration**: `.secrets-allowlist.README.md`
- **Development Guide**: `docs/DEVELOPMENT.md`
- **Gitleaks Documentation**: [https://github.com/gitleaks/gitleaks](https://github.com/gitleaks/gitleaks)
- **Secrets Manager API**: `src/core/shared/secrets_manager.py`

### Support

If you encounter issues not covered here:

1. Check the **Troubleshooting** section above
2. Review **build-progress.txt** in `.auto-claude/specs/047-*/`
3. Check existing exceptions in `.gitleaksignore` for similar cases
4. Open an issue with:
   - The hook output (redact actual secrets!)
   - File type and context
   - Why you believe it's a false positive

---

## Security Impact

### Why This Matters

Accidental secret commits are a **critical security risk**:

- **Attack Vector**: Exposed credentials enable authentication bypass
- **Blast Radius**: JWT secrets compromise entire authentication system
- **Persistence**: Git history preserves secrets even after removal
- **Compliance**: GDPR, SOC 2, ISO 27001 require secrets protection

### Protection Layers

ACGS-2's secrets detection provides:

1. **Prevention**: Stop secrets before they enter git history
2. **Detection**: Catch secrets in CI if hooks are bypassed
3. **Validation**: Runtime checks ensure credentials meet format requirements
4. **Rotation**: Secrets manager tracks rotation schedules

### Incident Response

If a secret is accidentally committed:

1. **Immediately rotate** the exposed credential
2. **Remove from git history** using BFG Repo-Cleaner or git-filter-repo:
   ```bash
   # Install BFG
   brew install bfg  # or download from https://rtyley.github.io/bfg-repo-cleaner/

   # Remove secret from history
   bfg --replace-text passwords.txt repo.git
   git reflog expire --expire=now --all
   git gc --prune=now --aggressive
   ```
3. **Force push** (coordinate with team!)
4. **Audit access** to determine if credential was compromised
5. **Document** in incident log

---

## Appendix: Example Workflows

### Workflow 1: Adding a New API Integration

```bash
# 1. Add credential pattern to secrets_manager.py
# src/core/shared/secrets_manager.py
CREDENTIAL_PATTERNS = {
    "MY_NEW_API_KEY": r"^myapi-[A-Za-z0-9]{32}$",
    # ...
}

# 2. Add to .env.example with placeholder
echo "MY_NEW_API_KEY=dev-myapi-key-placeholder" >> .env.example

# 3. Add to .secrets-allowlist.yaml (if needed)
# Under known_safe_values.development

# 4. Test detection works
echo "MY_NEW_API_KEY=myapi-abc123xyz789" > test.env
git add test.env
pre-commit run --files test.env  # Should fail
rm test.env

# 5. Commit the configuration
git add src/core/shared/secrets_manager.py .env.example
git commit -m "feat: add MY_NEW_API integration"
```

### Workflow 2: Handling a False Positive

```bash
# 1. Identify the issue
git add my-file.py
git commit -m "update"
# ❌ ACGS-2 Secrets Detection Failed!

# 2. Examine the detection
python scripts/check-secrets-pre-commit.py --verbose

# 3. Decide on solution
# If it's a placeholder → rename with dev-* prefix
# If it's a test fixture → add to .secrets-allowlist.yaml
# If it's a known safe value → document in .gitleaksignore

# 4. Implement solution (example: use placeholder)
# Change: API_KEY=abc123
# To: API_KEY=dev-api-key-placeholder

# 5. Test and commit
git add my-file.py
git commit -m "update"
# ✅ ACGS-2 Secrets Detection...Passed
```

### Workflow 3: Rotating a Development Secret

```bash
# 1. Generate new secret
python -c "import secrets; print(secrets.token_hex(32))"

# 2. Update in Vault (production) or secrets_manager (dev)
# Production:
vault kv put secret/acgs2/production JWT_SECRET="new-secret"

# Development:
from shared.secrets_manager import SecretsManager
manager = SecretsManager()
manager.set("JWT_SECRET", "new-secret")

# 3. Keep .env.example with placeholder (DO NOT update with real secret!)
# .env.example should always have: JWT_SECRET=dev-jwt-secret-min-32-chars-required

# 4. Update rotation metadata
manager.rotate("JWT_SECRET")  # Updates last_rotated timestamp

# 5. Notify team to pull new secrets
# Send message: "JWT_SECRET rotated, please pull from Vault"
```

---

**End of Document**

For questions or improvements to this documentation, please open an issue or submit a pull request.
