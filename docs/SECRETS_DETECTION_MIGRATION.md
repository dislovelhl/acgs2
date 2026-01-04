# Secrets Detection Migration Guide

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

> **Version**: 1.0.0
> **Last Updated**: 2026-01-04
> **Status**: Active

This guide helps existing ACGS-2 developers migrate to the new secrets detection pre-commit hooks. If you're a new developer setting up ACGS-2 for the first time, this migration is already included in the standard setup process.

---

## 🎯 Overview

ACGS-2 now includes automated secrets detection to prevent accidental credential commits. This adds two new pre-commit hooks:

1. **Gitleaks** - Industry-standard secret scanning (140+ patterns)
2. **ACGS-2 Custom Hook** - Project-specific patterns from `secrets_manager.py`

**Impact**: These hooks run automatically before each commit and may block commits containing secrets.

---

## 📋 Prerequisites

Before migrating, ensure you have:

- [ ] Python 3.11+ installed
- [ ] Git installed
- [ ] pre-commit framework installed (should already be installed if you've contributed before)
- [ ] Current work committed or stashed

---

## 🚀 Migration Steps

### Step 1: Update Your Pre-commit Hooks

The new hooks are already configured in `.pre-commit-config.yaml`. You just need to update your local installation:

```bash
# Update pre-commit hooks to latest configuration
pre-commit install --install-hooks

# Verify installation
pre-commit --version
```

**Expected Output:**
```
pre-commit installed at .git/hooks/pre-commit
```

#### Verify Hook Installation

Run a test to confirm hooks are working:

```bash
# Run hooks on all files (this may take a few minutes)
pre-commit run --all-files
```

**Expected**: All hooks should pass (or show specific issues to fix).

---

### Step 2: Install Gitleaks (if not already installed)

Gitleaks is required for the secrets detection. Check if it's installed:

```bash
gitleaks version
```

If not installed, install it:

**macOS (Homebrew):**
```bash
brew install gitleaks
```

**Linux:**
```bash
# Download from GitHub releases
wget https://github.com/gitleaks/gitleaks/releases/download/v8.21.2/gitleaks_8.21.2_linux_x64.tar.gz
tar -xzf gitleaks_8.21.2_linux_x64.tar.gz
sudo mv gitleaks /usr/local/bin/
```

**Windows (Scoop):**
```bash
scoop install gitleaks
```

**Verify installation:**
```bash
gitleaks version
# Expected: v8.21.2 or later
```

---

### Step 3: Scan Your Current Branch for Secrets

**IMPORTANT**: Before continuing your work, scan your current branch to identify any existing secrets that might block future commits.

#### Option A: Scan Staged Files Only (Quick)

```bash
# Scan only the files you've modified
gitleaks protect --staged --verbose --redact
```

#### Option B: Scan Your Entire Branch (Recommended)

```bash
# Scan all changes since branching from main
gitleaks detect --source=. --verbose --redact --log-opts="origin/main..HEAD"
```

#### Option C: Scan Specific Files

```bash
# Scan specific files you're working on
gitleaks detect --source=. --verbose --redact --no-git path/to/file.py
```

---

### Step 4: Handle Any Found Secrets

If secrets are detected, **DO NOT PANIC**. Follow the remediation steps below based on the type of secret found.

#### Scenario A: False Positive (Development Placeholder)

If the detected "secret" is actually a safe placeholder like `dev-jwt-secret-min-32-chars-required`:

**Solution 1: Use Safe Placeholder Prefixes** (Preferred)
```python
# ✅ SAFE - Will be allowed by hooks
API_KEY = "dev-your-api-key-here"
JWT_SECRET = "dev-jwt-secret-min-32-chars-required"
PASSWORD = "test-password-123"
TOKEN = "<your-token-here>"
```

**Solution 2: Add to Allow-list**
```bash
# Edit the allow-list configuration
vim .secrets-allowlist.yaml

# Add under known_safe_values.development:
development:
  - value: "your-specific-dev-value"
    context: "Brief explanation of what this is"
    why_safe: "Why it's safe to commit (e.g., development only)"
    production_mitigation: "How real secrets are managed in production"
```

**Solution 3: Add Fingerprint to .gitleaksignore**
```bash
# Run gitleaks to get the fingerprint
gitleaks detect --source=. --verbose

# Copy the fingerprint from output (looks like: abc123:path/to/file:line_number)
# Add to .gitleaksignore with a comment:
echo "abc123:path/to/file:line_number  # Safe because: explanation" >> .gitleaksignore
```

See [`SECRETS_QUICK_FIX.md`](./SECRETS_QUICK_FIX.md) for detailed resolution steps.

#### Scenario B: Real Secret in Working Branch

**🚨 CRITICAL**: If you've identified a real secret in your branch:

1. **Rotate the secret immediately** in the provider console
2. **Remove it from your code** using one of these methods:

**Method 1: Use secrets_manager.py** (Preferred)
```python
# Before (UNSAFE):
ANTHROPIC_API_KEY = "sk-ant-api03-abc123..."

# After (SAFE):
from acgs2.shared.secrets_manager import get_secret
ANTHROPIC_API_KEY = get_secret("ANTHROPIC_API_KEY")
```

**Method 2: Environment Variables**
```python
# Before (UNSAFE):
import os
API_KEY = "sk-abc123..."

# After (SAFE):
import os
API_KEY = os.getenv("API_KEY")
```

3. **Clean git history** if the secret was already committed:

```bash
# If not yet pushed to remote
git reset HEAD~1  # Undo last commit
# Fix the code, then commit again

# If already pushed to remote
# See SECRETS_QUICK_FIX.md for git filter-repo method
```

#### Scenario C: Secret in .env Files

If secrets are in `.env` files:

```bash
# Ensure .env files are gitignored
echo ".env" >> .gitignore
echo ".env.local" >> .gitignore

# Move real secrets to .env (gitignored)
mv .env.dev .env  # if .env.dev contains real secrets

# Keep only safe placeholders in .env.dev (tracked in git)
# Example .env.dev:
# API_KEY=dev-your-key-here
# JWT_SECRET=dev-jwt-secret-min-32-chars-required
```

---

### Step 5: Test Your First Commit with New Hooks

Make a small, safe change to test the hooks:

```bash
# Make a trivial change
echo "# Test comment" >> README.md

# Stage and commit
git add README.md
git commit -m "test: verify secrets detection hooks"
```

**Expected Output:**
```
Gitleaks Secret Detection..........................................Passed
ACGS-2 Secrets Detection...........................................Passed
ruff...................................................................Passed
bandit.................................................................Passed
[other hooks]..........................................................Passed
```

If hooks fail, review the error messages for remediation steps.

---

## 🔍 Scanning Existing Branches Before Merging

Before merging your branch to main, scan it for secrets:

### Full Branch Scan

```bash
# Scan all commits on your branch
gitleaks detect --source=. --verbose --redact --log-opts="origin/main..HEAD"
```

### Check Specific File Types

```bash
# Scan only Python files
gitleaks detect --source=. --verbose --redact --log-opts="origin/main..HEAD" -- "*.py"

# Scan only environment files
gitleaks detect --source=. --verbose --redact --log-opts="origin/main..HEAD" -- "*.env*"
```

### Automated Branch Scan Script

For convenience, use this script to scan before merging:

```bash
#!/bin/bash
# scripts/scan-branch-secrets.sh

set -e

BRANCH=$(git rev-parse --abbrev-ref HEAD)
BASE_BRANCH=${1:-origin/main}

echo "🔍 Scanning branch '$BRANCH' for secrets..."
echo "📊 Comparing against: $BASE_BRANCH"
echo ""

# Scan commits
if gitleaks detect --source=. --verbose --redact --log-opts="$BASE_BRANCH..HEAD"; then
    echo ""
    echo "✅ No secrets detected in branch!"
    echo "✅ Safe to merge."
else
    echo ""
    echo "❌ Secrets detected in branch!"
    echo "🔧 Fix secrets before merging. See docs/SECRETS_QUICK_FIX.md"
    exit 1
fi
```

**Usage:**
```bash
# Make script executable
chmod +x scripts/scan-branch-secrets.sh

# Scan your branch
./scripts/scan-branch-secrets.sh

# Or scan against a different base branch
./scripts/scan-branch-secrets.sh origin/develop
```

---

## 🔧 Troubleshooting

### Hook Installation Issues

**Problem**: `pre-commit: command not found`

**Solution**:
```bash
# Install pre-commit
pip install pre-commit

# Or with Homebrew (macOS)
brew install pre-commit
```

---

**Problem**: `gitleaks: command not found`

**Solution**: See [Step 2](#step-2-install-gitleaks-if-not-already-installed) above.

---

**Problem**: Hooks not running on commit

**Solution**:
```bash
# Reinstall hooks
pre-commit uninstall
pre-commit install --install-hooks

# Verify
ls -la .git/hooks/pre-commit
```

---

### Performance Issues

**Problem**: Hooks are slow (>10 seconds)

**Solutions**:

1. **Update pre-commit**:
```bash
pre-commit autoupdate
```

2. **Clear pre-commit cache**:
```bash
pre-commit clean
pre-commit gc
```

3. **Run only on changed files** (default behavior):
```bash
# This is automatic, but verify you're not using --all-files
git commit -m "message"  # Only scans staged files
```

---

### False Positives

**Problem**: Legitimate code is flagged as a secret

**Solution**: See [Step 4, Scenario A](#scenario-a-false-positive-development-placeholder) above.

**Quick reference**:
1. Use safe placeholder prefixes (`dev-`, `test-`, `example-`)
2. Add to `.secrets-allowlist.yaml` with justification
3. Add fingerprint to `.gitleaksignore` as last resort

---

### Bypass Hooks (Emergency Only)

**⚠️ WARNING**: Only use in true emergencies. All bypassed commits will be scanned in CI and may fail.

```bash
# Skip all pre-commit hooks (NOT RECOMMENDED)
git commit --no-verify -m "emergency: bypassing hooks"

# Better: Skip specific hooks via SKIP environment variable
SKIP=gitleaks git commit -m "message"  # Skip only gitleaks
```

**When to bypass**:
- ✅ Documented false positive that can't be resolved immediately
- ✅ Emergency hotfix (but fix properly afterward)
- ❌ **NEVER** bypass for real secrets
- ❌ **NEVER** bypass to save time

---

## 📚 Additional Resources

- **Full Documentation**: [`SECRETS_DETECTION.md`](./SECRETS_DETECTION.md)
- **Quick-Fix Guide**: [`SECRETS_QUICK_FIX.md`](./SECRETS_QUICK_FIX.md)
- **Allow-list README**: [`.secrets-allowlist.README.md`](../.secrets-allowlist.README.md)
- **Contributing Guidelines**: [`CONTRIBUTING.md`](../CONTRIBUTING.md)
- **Secrets Manager Source**: [`acgs2-core/shared/secrets_manager.py`](../src/core/shared/secrets_manager.py)

---

## ❓ FAQ

### Q: Do I need to re-scan my entire git history?

**A**: No. The hooks only scan changes you're about to commit. However, we recommend scanning your current branch before merging (see [Step 3](#step-3-scan-your-current-branch-for-secrets)).

### Q: Will this block my work?

**A**: Only if you're committing real secrets or values that look like secrets. Use safe placeholder prefixes (`dev-`, `test-`) to avoid false positives.

### Q: What if I'm working offline?

**A**: The hooks work offline. They only scan local files and don't require internet connectivity.

### Q: Can I disable secrets detection temporarily?

**A**: Yes, but not recommended:
```bash
# Disable for one commit
SKIP=gitleaks,acgs2-secrets-detection git commit -m "message"

# Disable globally (NOT RECOMMENDED)
git config --global --add pre-commit.disable gitleaks
```

### Q: How do I update the hooks when .pre-commit-config.yaml changes?

**A**: Run:
```bash
pre-commit install --install-hooks
```

This is automatic when you pull changes, but you can force it with the command above.

### Q: What's the difference between gitleaks and ACGS-2 custom hook?

**A**:
- **Gitleaks**: Industry-standard tool with 140+ generic patterns (API keys, passwords, etc.)
- **ACGS-2 Custom Hook**: Project-specific patterns from `secrets_manager.py` (Anthropic, OpenRouter, etc.)

Both run together for comprehensive protection.

### Q: I added a secret to .gitleaksignore but it's still failing

**A**: You might need to:
1. Ensure the fingerprint is correct (format: `hash:path:line_number`)
2. Check if the ACGS-2 custom hook is catching it (different from gitleaks)
3. Add to `.secrets-allowlist.yaml` if caught by ACGS-2 custom hook

### Q: How do I scan commits from last week?

**A**:
```bash
# Scan last 7 days
gitleaks detect --source=. --verbose --redact --log-opts="--since='7 days ago'"

# Scan last 10 commits
gitleaks detect --source=. --verbose --redact --log-opts="-10"

# Scan specific date range
gitleaks detect --source=. --verbose --redact --log-opts="--since=2024-01-01 --until=2024-01-07"
```

---

## ✅ Migration Checklist

Before considering your migration complete, verify:

- [ ] Pre-commit hooks updated (`pre-commit install --install-hooks`)
- [ ] Gitleaks installed and working (`gitleaks version`)
- [ ] Current branch scanned for secrets (`gitleaks detect --log-opts="origin/main..HEAD"`)
- [ ] Any found secrets remediated (using `secrets_manager.py` or safe placeholders)
- [ ] Test commit successful (hooks pass)
- [ ] Read [`SECRETS_DETECTION.md`](./SECRETS_DETECTION.md) for detailed documentation
- [ ] Bookmarked [`SECRETS_QUICK_FIX.md`](./SECRETS_QUICK_FIX.md) for future reference

---

## 🆘 Getting Help

If you encounter issues during migration:

1. **Check troubleshooting section** above
2. **Review [`SECRETS_QUICK_FIX.md`](./SECRETS_QUICK_FIX.md)** for common scenarios
3. **Ask in team chat** with:
   - Error message (redacted if contains sensitive info)
   - What you were trying to do
   - Steps you've already tried
4. **Create an issue** for persistent problems or documentation gaps

---

## 📝 Notes for Maintainers

### Updating This Guide

When updating secrets detection:
- Update hook versions in examples
- Add new troubleshooting scenarios as they arise
- Keep FAQ in sync with common questions
- Test all example commands before publishing

### Monitoring Migration Success

Track these metrics:
- [ ] Number of developers who've updated hooks
- [ ] Pre-commit success/failure rate
- [ ] Common false positives (update allow-lists)
- [ ] Secret detection in CI (should decrease as hooks are adopted)

---

**Last Updated**: 2026-01-04
**Document Version**: 1.0.0
**Spec**: `047-implement-secrets-detection-pre-commit-hook`
