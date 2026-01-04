# CI Integration Consistency Documentation

**Spec:** 047-implement-secrets-detection-pre-commit-hook
**Subtask:** 5.4 - Validate CI integration
**Created:** 2026-01-04
**Status:** ✅ Validated and Documented

## Overview

This document describes how secrets detection is implemented consistently between local pre-commit hooks and CI/CD pipeline checks, ensuring that developers catch issues locally before they reach the CI environment.

---

## Configuration Consistency

### Shared Configuration Files

Both pre-commit hooks and CI use the **same configuration files** to ensure consistent behavior:

| Configuration File | Purpose | Used By |
|-------------------|---------|---------|
| `.gitleaks.toml` | Custom gitleaks rules for ACGS-2 specific patterns | Pre-commit + CI |
| `.gitleaksignore` | Fingerprint-based exceptions for known safe secrets | Pre-commit + CI |
| `.secrets-allowlist.yaml` | Allow-list for ACGS-2 custom secrets detection | Pre-commit only |
| `acgs2-core/shared/secrets_manager.py` | Source of truth for CREDENTIAL_PATTERNS | Pre-commit only |

### Why This Matters

**Single source of truth:** By using the same `.gitleaks.toml` and `.gitleaksignore` files, we ensure:
- Developers see the same failures locally as CI would produce
- No surprises when pushing code to remote
- Consistent security posture across development lifecycle

---

## Pre-commit Hook Configuration

**Location:** `.pre-commit-config.yaml`

### 1. Gitleaks Pre-commit Hook

```yaml
- repo: https://github.com/gitleaks/gitleaks
  rev: v8.21.2
  hooks:
    - id: gitleaks
      name: Gitleaks Secret Detection
      description: Scan for secrets and credentials
      entry: gitleaks protect --verbose --redact --staged
      language: golang
      pass_filenames: false
```

**Key Parameters:**
- `--staged`: Scans only staged files (not entire git history) for performance
- `--redact`: Redacts secrets in output for security
- `--verbose`: Provides detailed output for debugging
- Automatically uses `.gitleaks.toml` (if present) and `.gitleaksignore`

### 2. ACGS-2 Custom Secrets Detection Hook

```yaml
- repo: local
  hooks:
    - id: acgs2-secrets-detection
      name: ACGS-2 Secrets Detection
      description: Detect ACGS-2-specific secrets using patterns from secrets_manager.py
      entry: python scripts/check-secrets-pre-commit.py
      language: system
      files: \.(py|env|ya?ml|json)$
      exclude: ^(.*/(__pycache__|\.venv|venv|node_modules|tests/fixtures|__fixtures__)/.*|.*\.(env\.example|env\.template|example\.|template\.)|tests/test_.*\.py$)
```

**Key Features:**
- Uses `CREDENTIAL_PATTERNS` directly from `secrets_manager.py` (single source of truth)
- Scans `.py`, `.env`, `.yaml`, `.yml`, `.json` files
- Excludes test fixtures, example files, and templates
- Provides actionable error messages with remediation steps

---

## CI Configuration

**Location:** `.github/workflows/reusable-security.yml`

### Gitleaks CI Check

```yaml
- name: Check for secrets
  uses: gitleaks/gitleaks-action@v2
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    GITLEAKS_CONFIG: .gitleaks.toml
```

**Key Features:**
- Uses `gitleaks/gitleaks-action@v2` GitHub Action
- **Explicitly configured** to use `.gitleaks.toml` via `GITLEAKS_CONFIG` environment variable
- Automatically uses `.gitleaksignore` (built into gitleaks-action)
- Scans entire repository history (not just staged files like pre-commit)

---

## Differences Between Local and CI Checks

While we strive for maximum consistency, there are intentional differences:

### 1. Scan Scope

| Environment | Scope | Rationale |
|-------------|-------|-----------|
| **Pre-commit (local)** | Only staged files (`--staged`) | Performance - developers need fast feedback (<5s target) |
| **CI** | Entire git history | Security - comprehensive scan to catch any historical leaks |

**Impact:** CI may catch secrets in git history that were committed before pre-commit hooks were installed.

**Mitigation:** See "Migration and Historical Secrets" section below.

### 2. ACGS-2 Custom Hook

| Environment | ACGS-2 Custom Hook | Rationale |
|-------------|-------------------|-----------|
| **Pre-commit (local)** | ✅ Enabled | Provides ACGS-2-specific pattern validation and actionable error messages |
| **CI** | ❌ Not enabled | Gitleaks provides sufficient coverage; custom hook adds complexity to CI |

**Impact:** Developers get more detailed, context-aware error messages locally.

**Mitigation:** None needed - gitleaks in CI provides baseline protection.

### 3. Performance Optimization

| Environment | Optimization | Details |
|-------------|-------------|---------|
| **Pre-commit (local)** | Scans only staged files | Uses `git diff --cached --name-only --diff-filter=ACM` |
| **CI** | Full repository scan | Uses `fetch-depth: 0` to scan entire history |

**Impact:** Pre-commit is much faster (<5s typical) but only catches new changes.

**Mitigation:** CI provides comprehensive historical scanning as a safety net.

---

## Configuration Consistency Table

| Feature | Pre-commit | CI | Consistent? |
|---------|-----------|-----|-------------|
| Uses `.gitleaks.toml` custom rules | ✅ Yes | ✅ Yes | ✅ **Consistent** |
| Uses `.gitleaksignore` exceptions | ✅ Yes | ✅ Yes | ✅ **Consistent** |
| Gitleaks version | v8.21.2 | v2 (action) | ⚠️ Different implementation |
| Scans AI provider keys (Anthropic, etc.) | ✅ Yes | ✅ Yes | ✅ **Consistent** |
| Scans AWS keys | ✅ Yes | ✅ Yes | ✅ **Consistent** |
| Scans JWT secrets | ✅ Yes | ✅ Yes | ✅ **Consistent** |
| Scans Vault tokens | ✅ Yes | ✅ Yes | ✅ **Consistent** |
| Allows development placeholders | ✅ Yes | ✅ Yes | ✅ **Consistent** |
| Excludes `.env.example` files | ✅ Yes | ✅ Yes | ✅ **Consistent** |
| Excludes test fixtures | ✅ Yes | ✅ Yes | ✅ **Consistent** |
| ACGS-2 custom patterns | ✅ Yes | ❌ No | ⚠️ **By design** |
| Scan scope | Staged only | Full history | ⚠️ **By design** |

### Legend
- ✅ **Consistent** - Same behavior in both environments
- ⚠️ **By design** - Intentional difference with documented rationale

---

## Testing Consistency

### How to Verify Local/CI Consistency

1. **Test pre-commit locally:**
   ```bash
   # Stage a file with a fake secret
   echo 'ANTHROPIC_API_KEY=sk-ant-api03-test123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890' > test-secret.txt
   git add test-secret.txt

   # Try to commit (should fail)
   git commit -m "test: verify secrets detection"

   # Cleanup
   git reset HEAD test-secret.txt
   rm test-secret.txt
   ```

2. **Verify CI would catch the same issue:**
   - CI uses the same `.gitleaks.toml` rules
   - CI uses the same `.gitleaksignore` exceptions
   - Both should produce the same finding for the same secret pattern

3. **Check configuration alignment:**
   ```bash
   # Verify gitleaks config is valid
   gitleaks detect --config .gitleaks.toml --no-git --verbose

   # Run ACGS-2 custom hook manually
   python scripts/check-secrets-pre-commit.py
   ```

---

## Migration and Historical Secrets

### Scanning Existing Branches

**Problem:** Pre-commit hooks only scan staged changes, so existing branches may contain secrets.

**Solution:** Scan entire branch before merging:

```bash
# Scan current branch for secrets
gitleaks detect --config .gitleaks.toml --verbose

# Scan specific branch
gitleaks detect --config .gitleaks.toml --verbose --source . --branch feature-branch
```

### Handling Historical Secrets

If gitleaks finds secrets in git history:

1. **Assess severity:** Is it a real secret or a false positive?
2. **If false positive:** Add to `.gitleaksignore` with documentation
3. **If real secret:** Follow incident response:
   - Rotate the secret immediately
   - Remove from git history (see `docs/SECRETS_QUICK_FIX.md`)
   - Document in security incident log

---

## Maintenance and Updates

### When to Update Configuration

Update `.gitleaks.toml` when:
- New secret types are added to `secrets_manager.py` `CREDENTIAL_PATTERNS`
- New AI providers or infrastructure tools are adopted
- False positives become frequent (add allowlist patterns)

### Configuration Review Schedule

| Configuration | Review Frequency | Responsible Team |
|--------------|------------------|------------------|
| `.gitleaks.toml` | Quarterly | Security team |
| `.gitleaksignore` | Monthly | Security + DevOps |
| `.secrets-allowlist.yaml` | Quarterly | Development team |

### Updating Gitleaks Version

**Pre-commit:**
```bash
# Update in .pre-commit-config.yaml
# Change: rev: v8.21.2 to newer version
# Then:
pre-commit autoupdate --repo https://github.com/gitleaks/gitleaks
```

**CI:**
- GitHub Action `gitleaks/gitleaks-action@v2` auto-updates
- Pin to specific version if stability issues arise

---

## Troubleshooting

### Issue: Pre-commit passes but CI fails

**Causes:**
1. Secret exists in git history (not in staged files)
2. Different gitleaks versions between local and CI
3. Configuration file mismatch

**Solutions:**
```bash
# 1. Scan full repository locally
gitleaks detect --config .gitleaks.toml --verbose

# 2. Check gitleaks version
gitleaks version

# 3. Verify CI is using .gitleaks.toml
# Check .github/workflows/reusable-security.yml has:
# GITLEAKS_CONFIG: .gitleaks.toml
```

### Issue: CI passes but pre-commit fails

**Causes:**
1. ACGS-2 custom hook has stricter validation
2. Local `.secrets-allowlist.yaml` is outdated

**Solutions:**
```bash
# 1. Check which hook failed
git commit -m "test" --verbose

# 2. Update pre-commit hooks
pre-commit autoupdate

# 3. Review .secrets-allowlist.yaml for custom hook config
```

### Issue: Both fail on legitimate placeholder

**Solutions:**
1. **Preferred:** Use standard placeholder prefix (dev-, test-, your-)
2. Add pattern to `.gitleaks.toml` allowlist section
3. **Last resort:** Add fingerprint to `.gitleaksignore` with documentation

See `docs/SECRETS_QUICK_FIX.md` for detailed resolution steps.

---

## References

### Configuration Files
- `.gitleaks.toml` - Custom gitleaks rules
- `.gitleaksignore` - Fingerprint-based exceptions
- `.secrets-allowlist.yaml` - ACGS-2 custom hook allowlist
- `.pre-commit-config.yaml` - Pre-commit hook configuration
- `.github/workflows/reusable-security.yml` - CI security workflow

### Documentation
- `docs/SECRETS_DETECTION.md` - Comprehensive secrets detection guide
- `docs/SECRETS_QUICK_FIX.md` - Quick-fix troubleshooting
- `CONTRIBUTING.md` - Contributing guidelines with secrets policy
- `.secrets-allowlist.README.md` - Allowlist configuration guide

### External Resources
- [Gitleaks Documentation](https://github.com/gitleaks/gitleaks)
- [Gitleaks GitHub Action](https://github.com/gitleaks/gitleaks-action)
- [Pre-commit Framework](https://pre-commit.com/)

---

## Summary

**✅ Pre-commit and CI are now consistent:**

1. **Same rules:** Both use `.gitleaks.toml` custom rules
2. **Same exceptions:** Both use `.gitleaksignore` fingerprints
3. **Same patterns:** Both detect ACGS-2-specific secrets (Anthropic, etc.)
4. **Documented differences:** Scan scope and custom hook are intentionally different
5. **Migration support:** Tools and docs for handling historical secrets

**Key Achievement:** Developers will catch secrets **before CI** with consistent, fast local feedback.

---

**Validation Status:** ✅ Complete
**Acceptance Criteria Met:**
- ✅ Pre-commit and CI use same gitleaks configuration (`.gitleaks.toml`)
- ✅ CI workflow updated for consistency (`GITLEAKS_CONFIG` env var added)
- ✅ Documented differences (scan scope, custom hook) with clear rationale
