# Secrets Detection Quick-Fix Guide

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

> **Version**: 1.0.0
> **Last Updated**: 2026-01-03
> **Status**: Active

**Quick Links:**
- Full Documentation: [`SECRETS_DETECTION.md`](./SECRETS_DETECTION.md)
- Allow-list Configuration: [`.secrets-allowlist.README.md`](../.secrets-allowlist.README.md)
- Secrets Manager: [`src/core/shared/secrets_manager.py`](../src/core/shared/secrets_manager.py)

---

## Emergency: I Committed a Real Secret! 🚨

**STOP! Follow these steps immediately:**

### 1. Rotate the Secret (Do This First!)
```bash
# The secret is compromised. Rotate it IMMEDIATELY:
# - Revoke the API key/token in the provider console
# - Generate a new secret
# - Update production systems with the new secret
```

**Why first?** Once committed, the secret is in git history and may have been pushed to remote repositories. Assume it's compromised.

### 2. Remove from Git History

Choose the appropriate method based on your situation:

#### Method A: Secret in Latest Commit Only (NOT YET PUSHED)

```bash
# 1. Remove the file from staging
git reset HEAD path/to/file

# 2. Edit the file to remove/replace the secret
# Use secrets_manager.py or a placeholder (see below)

# 3. Amend the commit
git add path/to/file
git commit --amend --no-edit

# 4. Verify it's gone
git show HEAD:path/to/file | grep -i "secret-pattern"
```

#### Method B: Secret Already Pushed to Remote

```bash
# WARNING: This rewrites history and affects all team members!
# Coordinate with your team before proceeding.

# 1. Use git filter-repo (preferred) or BFG Repo-Cleaner
# Install git-filter-repo:
pip install git-filter-repo

# 2. Remove the secret from history
git filter-repo --path path/to/file --invert-paths --force

# OR remove specific strings:
echo "sk-ant-api03-actual-secret-here" > /tmp/secrets.txt
git filter-repo --replace-text /tmp/secrets.txt --force

# 3. Force push (coordinate with team!)
git push --force-with-lease origin main

# 4. Team members must re-clone:
# git clone <repository-url>
```

#### Method C: Secret in Multiple Commits (Complex)

```bash
# Use BFG Repo-Cleaner for better performance
# Download: https://rtyley.github.io/bfg-repo-cleaner/

# 1. Create a fresh clone
git clone --mirror git@github.com:yourorg/yourrepo.git

# 2. Remove the secret
java -jar bfg.jar --replace-text secrets.txt yourrepo.git

# 3. Clean and push
cd yourrepo.git
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force

# 4. Update all local repositories
# All team members must re-clone!
```

### 3. Verify Removal

```bash
# Check git history for the secret
git log -p --all -S "secret-pattern-here"

# Should return no results!
```

### 4. Document the Incident

```bash
# Create an incident report
cat >> SECURITY_INCIDENTS.md <<EOF
## $(date +%Y-%m-%d): Secret Exposure

**What**: [Brief description, e.g., "Anthropic API key"]
**When**: [Date/time detected]
**Where**: [File path, commit hash]
**Action Taken**:
- ✅ Secret rotated
- ✅ Removed from git history
- ✅ Force pushed to remote
- ✅ Team notified

**Root Cause**: [Why it happened]
**Prevention**: [What will prevent recurrence]
EOF
```

---

## Quick Fixes for Pre-commit Hook Failures

### Scenario 1: False Positive on Development Placeholder

**Error Message:**
```
❌ Potential secret detected in .env.dev:
   JWT_SECRET=mysupersecret
```

**Quick Fix:**
```bash
# Option 1: Use a safe placeholder prefix (BEST)
# Edit .env.dev:
JWT_SECRET=dev-jwt-secret-min-32-chars-required

# Option 2: Add to allow-list
# Edit .secrets-allowlist.yaml:
known_safe_values:
  development:
    - value: "mysupersecret"
      context: "Development JWT secret in .env.dev"
      why_safe: "Placeholder value, never used in production"
      production_mitigation: "Production uses Vault-managed secrets via secrets_manager.py"

# Test the fix
python scripts/check-secrets-pre-commit.py --verbose
```

### Scenario 2: Need to Commit Example Configuration

**Error Message:**
```
❌ Potential secret detected in docs/api-example.md:
   ANTHROPIC_API_KEY=sk-ant-api03-example
```

**Quick Fix:**
```bash
# Option 1: Rename file to match exclusion pattern
mv docs/api-example.md docs/api-example.example.md

# Option 2: Use placeholder prefix
# Edit docs/api-example.md:
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Option 3: Add path to exclusions
# Edit .secrets-allowlist.yaml:
excluded_paths:
  file_patterns:
    - "docs/api-example.md"
```

### Scenario 3: Gitleaks Fails on Test Fixture

**Error Message:**
```
gitleaks detected secrets in test_auth.py
```

**Quick Fix:**
```bash
# 1. Run gitleaks with verbose to get the fingerprint
gitleaks detect --no-git --verbose

# Output will show:
# Finding: generic-api-key
# Secret: sk-test-12345
# File: tests/fixtures/test_auth.py:15
# Fingerprint: abc123def456:tests/fixtures/test_auth.py:generic-api-key:15

# 2. Add fingerprint to .gitleaksignore with documentation
cat >> .gitleaksignore <<EOF

# Test fixture API key - expired test key for unit tests only
# Key expired 2025-01-01, documented in tests/fixtures/README.md
abc123def456:tests/fixtures/test_auth.py:generic-api-key:15
EOF

# 3. Test the fix
gitleaks protect --staged --verbose
```

---

## How to Use secrets_manager.py for Safe Secret Storage

### Quick Start: Loading Secrets from Vault/Environment

```python
from acgs2_core.shared.secrets_manager import SecretsManager

# Initialize the secrets manager
secrets = SecretsManager()

# Load secret from Vault or environment variable
# Priority: Vault > Environment Variable > Default
anthropic_key = secrets.get_secret(
    "ANTHROPIC_API_KEY",
    default="dev-anthropic-key-placeholder"  # Safe placeholder for development
)

# Validate the secret format
if secrets.validate_credential("ANTHROPIC_API_KEY", anthropic_key):
    print("✅ Valid Anthropic API key")
else:
    print("❌ Invalid format - using development mode")
```

### Setting Up Vault for Production

```python
# 1. Configure Vault connection (production only)
import os
os.environ["VAULT_ADDR"] = "https://vault.yourcompany.com"
os.environ["VAULT_TOKEN"] = os.getenv("VAULT_TOKEN")  # From CI/CD

# 2. SecretsManager automatically uses Vault if available
secrets = SecretsManager()

# 3. It falls back to environment variables if Vault is unavailable
# This is safe because dev environments won't have Vault configured
```

### Development vs Production Pattern

```python
# config.py - Safe pattern for all environments
from acgs2_core.shared.secrets_manager import SecretsManager

secrets = SecretsManager()

# Development: Uses placeholder from .env.dev
# Production: Uses Vault-managed secret
ANTHROPIC_API_KEY = secrets.get_secret(
    "ANTHROPIC_API_KEY",
    default="dev-anthropic-api-key-placeholder"
)

# Validation ensures we never use placeholders in production
if not secrets.validate_credential("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY):
    if os.getenv("ENVIRONMENT") == "production":
        raise ValueError("Invalid ANTHROPIC_API_KEY in production!")
    else:
        print("⚠️  Using development placeholder for ANTHROPIC_API_KEY")
```

### Available Credential Patterns

SecretsManager validates these credential types (from `CREDENTIAL_PATTERNS`):

| Secret Type | Validation Pattern | Example Valid Format |
|-------------|-------------------|---------------------|
| `ANTHROPIC_API_KEY` | `sk-ant-[A-Za-z0-9_-]{80,}` | `sk-ant-api03-...` (80+ chars) |
| `CLAUDE_CODE_OAUTH_TOKEN` | `sk-ant-oat\d{2}-[A-Za-z0-9_-]{60,}` | `sk-ant-oat01-...` (60+ chars) |
| `OPENROUTER_API_KEY` | `sk-or-v1-[A-Za-z0-9]{60,}` | `sk-or-v1-...` (60+ chars) |
| `HUGGINGFACE_TOKEN` | `hf_[A-Za-z0-9]{30,}` | `hf_...` (30+ chars) |
| `AWS_ACCESS_KEY_ID` | `AKIA[A-Z0-9]{16}` | `AKIAIOSFODNN7EXAMPLE` |
| `JWT_SECRET` | `[A-Fa-f0-9]{64}` | 64-character hex string |
| `VAULT_TOKEN` | `(hvs\.|s\.)[A-Za-z0-9]{20,}` | `hvs.abc123...` or `s.xyz789...` |
| `OPENAI_API_KEY` | `sk-[A-Za-z0-9]{20,}` | `sk-proj-...` (20+ chars) |

```python
# Validate a secret before use
from acgs2_core.shared.secrets_manager import SecretsManager

secrets = SecretsManager()

key = "sk-ant-api03-abc123..."
if secrets.validate_credential("ANTHROPIC_API_KEY", key):
    # Safe to use
    client = anthropic.Anthropic(api_key=key)
else:
    # Invalid format - don't use!
    raise ValueError("Invalid Anthropic API key format")
```

---

## Quick Reference: Allow-list Updates

### Add Pattern-Based Exception (Broad)

```yaml
# .secrets-allowlist.yaml
placeholder_patterns:
  prefixes:
    - "dev-"
    - "test-"
    - "staging-"  # <-- Add new prefix
    - "demo-"     # <-- Add new prefix
```

### Add Path-Based Exception (Targeted)

```yaml
# .secrets-allowlist.yaml
excluded_paths:
  file_patterns:
    - ".env.example"
    - ".env.template"
    - "docs/examples/*.md"  # <-- Add new pattern
```

### Add Value-Based Exception (Precise)

```yaml
# .secrets-allowlist.yaml
known_safe_values:
  development:
    - value: "my-safe-dev-value"
      context: "Where/how it's used"
      why_safe: "Why this is safe to commit"
      production_mitigation: "How production handles this"
```

### Add to .gitleaksignore (Last Resort)

```bash
# 1. Get the fingerprint
gitleaks detect --no-git --verbose

# 2. Add to .gitleaksignore with documentation
cat >> .gitleaksignore <<EOF

# [Describe what this is]
# [Explain why it's safe to commit]
# [Document production mitigation]
<fingerprint-here>
EOF

# Example:
# Development SAML certificate - public test cert bundle
# Used only in local docker-compose, production uses real certs
abc123:config/saml/sp.crt:generic-api-key:42
```

---

## Testing Your Changes

```bash
# Test custom ACGS-2 hook
python scripts/check-secrets-pre-commit.py --verbose

# Test gitleaks
gitleaks protect --staged --verbose

# Test all pre-commit hooks
pre-commit run --all-files

# Test specific hook
pre-commit run acgs2-secrets-detection --all-files
pre-commit run gitleaks --all-files
```

---

## Decision Tree: Which Solution to Use?

```
Found a potential secret detected by hooks?
│
├─ Is it a real secret?
│  │
│  ├─ YES → 🚨 EMERGENCY PROCEDURE (see top of document)
│  │        1. Rotate the secret immediately
│  │        2. Remove from git history
│  │        3. Document incident
│  │
│  └─ NO → It's a false positive, continue...
│
└─ Is it a false positive?
   │
   ├─ Development placeholder value?
   │  └─ Use placeholder prefix (e.g., dev-*, test-*)
   │     BEST option - makes it obviously not production
   │
   ├─ Example/documentation file?
   │  ├─ Rename to match exclusion pattern (*.example.*)
   │  └─ OR add to excluded_paths in .secrets-allowlist.yaml
   │
   ├─ Test fixture?
   │  ├─ Use environment variable + placeholder default
   │  └─ OR add fingerprint to .gitleaksignore with docs
   │
   └─ Valid project-wide exception?
      ├─ Add to known_safe_values in .secrets-allowlist.yaml
      │  (with full documentation: context, why_safe, production_mitigation)
      └─ OR add to .gitleaksignore (last resort)
         (requires fingerprint, breaks on file changes)
```

---

## Common Commands Cheat Sheet

```bash
# Get gitleaks fingerprint for exception
gitleaks detect --no-git --verbose

# Run only secrets detection hooks
pre-commit run acgs2-secrets-detection --all-files
pre-commit run gitleaks --all-files

# Check specific file manually
python scripts/check-secrets-pre-commit.py path/to/file.py

# Validate allow-list YAML syntax
yamllint .secrets-allowlist.yaml
python -c "import yaml; yaml.safe_load(open('.secrets-allowlist.yaml'))"

# Search git history for a secret (after removal)
git log -p --all -S "secret-pattern-here"

# Check if secret exists in any branch
git grep "secret-pattern" $(git rev-list --all)

# Remove file from git history (simple case)
git filter-repo --path path/to/file --invert-paths --force

# Remove specific string from git history
git filter-repo --replace-text /tmp/secrets.txt --force

# Force push after history rewrite (DANGEROUS!)
git push --force-with-lease origin main

# Amend last commit (if not pushed)
git commit --amend --no-edit

# Check what will be committed
git diff --cached

# Unstage file
git reset HEAD path/to/file

# Skip hooks temporarily (NOT RECOMMENDED for secrets!)
git commit --no-verify  # ⚠️  Only use for non-secret changes!
```

---

## When to Skip Pre-commit Hooks ⚠️

### NEVER Skip For:
- ❌ Files containing any secrets or credentials
- ❌ Configuration files (`.env`, `.yaml`, `.json`)
- ❌ Python files that import or use secrets
- ❌ "Just this one time" - that's how leaks happen!

### OK to Skip For:
- ✅ Documentation-only changes (after manual review)
- ✅ Binary files that don't contain secrets
- ✅ Emergency hotfixes (with team lead approval + immediate follow-up)

```bash
# If you must skip (approved emergency only):
git commit --no-verify -m "Emergency hotfix - approved by [Name]"

# Immediately follow up with:
# 1. Create ticket to properly fix
# 2. Run hooks manually: pre-commit run --all-files
# 3. Document in commit message why skip was necessary
```

---

## Getting Help

### Check Logs
```bash
# Verbose output from custom hook
python scripts/check-secrets-pre-commit.py --verbose

# Verbose output from gitleaks
gitleaks protect --staged --verbose --redact
```

### Common Issues Reference
See [`SECRETS_DETECTION.md#troubleshooting`](./SECRETS_DETECTION.md#troubleshooting) for detailed troubleshooting of:
- Hook fails on legitimate placeholder
- Hook fails on example files
- Hook performance issues
- Pattern not detected
- False positives

### Contact
- **Security Incidents**: Contact security team immediately
- **Questions**: Ask in `#security` or `#engineering` Slack channels
- **Bug Reports**: Open GitHub issue with `security` label

---

## Best Practices Summary

1. **Never commit real secrets** - Use `secrets_manager.py` + Vault/environment variables
2. **Use safe placeholders** - Prefix with `dev-`, `test-`, `your-`, or wrap in `<>`
3. **Document exceptions** - Every exception needs context and justification
4. **Test before committing** - Run hooks manually on sensitive changes
5. **Rotate immediately** - If a secret leaks, assume it's compromised
6. **Remove from history** - Don't just delete from working tree
7. **Learn from incidents** - Document what happened and how to prevent it

---

**Next Steps:**
- Read full documentation: [`SECRETS_DETECTION.md`](./SECRETS_DETECTION.md)
- Review allow-list config: [`.secrets-allowlist.yaml`](../.secrets-allowlist.yaml)
- Understand patterns: [`secrets_manager.py`](../src/core/shared/secrets_manager.py)
