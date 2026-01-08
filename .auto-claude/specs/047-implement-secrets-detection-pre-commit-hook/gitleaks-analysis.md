# Gitleaks Configuration Analysis

**Date:** 2026-01-03
**Subtask:** 1.1 - Analyze existing gitleaks configuration
**Status:** Complete

## Executive Summary

Gitleaks is currently integrated into CI/CD via GitHub Actions but **NOT** in pre-commit hooks. The existing setup is minimal with only one ignored secret (development SAML certificate). This analysis documents current usage patterns to inform pre-commit integration.

---

## 1. Current Gitleaks Usage in CI/CD

### GitHub Workflow Configuration
**File:** `.github/workflows/reusable-security.yml`

```yaml
- name: Check for secrets
  uses: gitleaks/gitleaks-action@v2
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**Analysis:**
- **Version:** gitleaks-action@v2
- **Trigger:** Runs in `compliance-check` job as part of security workflow
- **Scope:** Full repository scan (fetch-depth: 0 in checkout)
- **Configuration:** Uses defaults (no custom .gitleaks.toml)
- **Ignore file:** Automatically respects `.gitleaksignore`
- **Exit behavior:** Blocks PR/push if secrets detected

**Strengths:**
- Catches secrets before they reach main branch
- Industry-standard tool with regular updates
- Integrated with GitHub Security tab

**Weaknesses:**
- Only runs in CI - developer doesn't know until after push
- No early feedback during development
- Can be bypassed by force-pushing or disabling CI

---

## 2. Current .gitleaksignore Configuration

**File:** `.gitleaksignore`

```
# Gitleaks ignore file
# https://github.com/gitleaks/gitleaks#gitleaksignore
# Use fingerprints from gitleaks findings to ignore specific secrets

# Development SAML SP certificates (self-signed, for testing only)
# These are NOT used in production - production deployments generate their own certificates
# Fingerprint format: file:rule:line
src/core/shared/auth/certs/sp.key:private-key:1
```

**Currently Ignored Secrets:**
1. **SAML SP Private Key** (`src/core/shared/auth/certs/sp.key`)
   - **Rule:** private-key
   - **Line:** 1
   - **Justification:** Self-signed development certificate, not used in production
   - **Risk Level:** Low (documented, development-only)

**Analysis:**
- Very minimal configuration (good - not over-ignoring)
- Uses fingerprint-based ignoring (precise, recommended approach)
- Each exception is well-documented with rationale
- Follows best practice: ignore by fingerprint, not pattern

**File Patterns Currently NOT Excluded:**
- `.env.example` (may contain placeholder secrets)
- `.env.dev` (may contain development secrets)
- Test fixtures
- Documentation examples

---

## 3. Secrets Manager Integration Opportunities

**File:** `src/core/shared/secrets_manager.py`

### CREDENTIAL_PATTERNS Defined

The secrets manager defines regex patterns for validating credentials:

```python
CREDENTIAL_PATTERNS = {
    "CLAUDE_CODE_OAUTH_TOKEN": r"^sk-ant-oat\d{2}-[A-Za-z0-9_-]{60,}$",
    "OPENAI_API_KEY": r"^sk-[A-Za-z0-9]{20,}$",
    "OPENROUTER_API_KEY": r"^sk-or-v1-[A-Za-z0-9]{60,}$",
    "HF_TOKEN": r"^hf_[A-Za-z0-9]{30,}$",
    "ANTHROPIC_API_KEY": r"^sk-ant-[A-Za-z0-9_-]{80,}$",
    "AWS_ACCESS_KEY_ID": r"^AKIA[A-Z0-9]{16}$",
    "JWT_SECRET": r"^[A-Fa-f0-9]{64}$",
    "VAULT_TOKEN": r"^(hvs\.|s\.)[A-Za-z0-9]{20,}$",
}
```

### SECRET_CATEGORIES Defined

Secrets are organized into categories:
- **ai_providers:** Claude, OpenAI, OpenRouter, HuggingFace, Anthropic
- **security:** JWT, API keys, audit signatures
- **infrastructure:** Vault, Redis, DB, Kafka passwords
- **cloud:** AWS credentials, blockchain private keys

**Integration Opportunity:**
- Custom pre-commit hook can use these exact patterns
- Ensures consistency between runtime validation and pre-commit scanning
- Can detect ACGS-2 specific secrets that gitleaks might miss

---

## 4. Placeholder vs Real Secrets

### Known Placeholder Patterns

Based on codebase examination, these placeholder patterns should be allowed:

1. **JWT Secrets:**
   - `dev-jwt-secret-min-32-chars-required` (development placeholder)
   - Pattern: `dev-*`, `test-*`, `placeholder-*`

2. **Development Tokens:**
   - Example values in `.env.example`
   - Test API keys in test fixtures

3. **Documentation Examples:**
   - Redacted examples: `sk-ant-XXX...XXX`
   - Masked values: `***hidden***`, `<your-key-here>`

**Recommendation:**
Create allow-list for these patterns in custom hook to reduce false positives.

---

## 5. Files Requiring Secret Scanning

Based on secrets_manager.py and common patterns:

### High Priority (MUST scan):
- `**/.env` - Environment variable files
- `**/.env.local` - Local overrides
- `**/.env.production` - Production configs
- `**/*.py` - Python source (hardcoded secrets)
- `**/config/*.yaml` - Configuration files
- `**/config/*.json` - JSON configs

### Medium Priority (SHOULD scan):
- `**/*.sh` - Shell scripts (may contain exports)
- `**/*.js`, `**/*.ts` - JavaScript/TypeScript
- `**/docker-compose*.yml` - Container configs
- `**/k8s/**/*.yaml` - Kubernetes manifests

### Low Priority / Exclude:
- `**/.env.example` - Example files (placeholders)
- `**/tests/fixtures/**` - Test data
- `**/docs/**` - Documentation
- `**/__pycache__/**` - Python bytecode
- `**/node_modules/**` - Dependencies

---

## 6. Gap Analysis: CI vs Pre-commit

| Feature | Current CI | Desired Pre-commit |
|---------|-----------|-------------------|
| **Gitleaks scanning** | ✅ Yes | ❌ No |
| **ACGS-2 pattern detection** | ❌ No | ❌ No |
| **Immediate feedback** | ❌ No (after push) | 🎯 Target |
| **Custom allow-lists** | ⚠️ Basic (.gitleaksignore) | 🎯 Target (enhanced) |
| **Placeholder detection** | ❌ No | 🎯 Target |
| **Performance** | N/A (cloud) | 🎯 <5s local |

**Key Gaps:**
1. No early feedback loop (pre-commit)
2. No ACGS-2-specific pattern detection
3. No intelligent placeholder vs real secret distinction
4. No integration with secrets_manager.py patterns

---

## 7. Currently Ignored Secrets Inventory

### Explicit Ignores (.gitleaksignore):
1. ✅ `src/core/shared/auth/certs/sp.key` - Development SAML certificate

### Implicit Ignores (Not Currently Caught):
Based on default gitleaks rules, these may NOT be caught:
- Environment variable placeholders in comments
- Redacted secrets in documentation
- Test fixture secrets

**Action Required:**
- Audit `.env.example` and `.env.dev` for real vs placeholder secrets
- Identify any test certificates or keys
- Document all intentional "secrets" that are safe to commit

---

## 8. File Patterns Needing Scanning

### Derived from codebase structure:

**Python files:** `**/*.py`
- May contain hardcoded API keys
- May have embedded JWTs
- May include credential validators with example data

**Environment files:** `**/.env*`
- Primary location for secrets
- Exclude `.env.example` (placeholders only)
- Scan `.env.local`, `.env.dev`, `.env.production`

**Configuration files:**
- `**/*.yaml`, `**/*.yml` - YAML configs
- `**/*.json` - JSON configs (excluding package.json)
- `**/*.toml` - TOML configs

**Infrastructure as Code:**
- `**/docker-compose*.yml`
- `**/k8s/**/*.yaml`
- `**/helm/**/*.yaml` (exclude templates)
- `**/*.tf` - Terraform files (if present)

---

## 9. Gitleaks Default Rules Coverage

Gitleaks v8 default rules include detection for:
- AWS keys
- GitHub tokens
- Generic API keys
- Private keys (RSA, SSH, etc.)
- JWTs
- Database URLs with embedded credentials
- OAuth tokens

**Coverage for ACGS-2:**
- ✅ AWS keys (AWS_ACCESS_KEY_ID pattern)
- ⚠️ Anthropic/Claude keys (may need custom rule)
- ⚠️ OpenRouter keys (may need custom rule)
- ✅ JWT tokens
- ✅ Generic private keys
- ⚠️ HuggingFace tokens (may need custom rule)

**Recommendation:**
Create `.gitleaks.toml` with custom rules for ACGS-2 specific patterns from secrets_manager.py

---

## 10. Recommendations for Pre-commit Integration

### Phase 1: Basic Integration
1. Add gitleaks to `.pre-commit-config.yaml`
2. Use existing `.gitleaksignore` without changes
3. Test with current repository state

### Phase 2: Custom Configuration
1. Create `.gitleaks.toml` with:
   - ACGS-2 specific rules from CREDENTIAL_PATTERNS
   - Allow-lists for placeholder patterns
   - Optimized file type scanning

### Phase 3: Custom Hook
1. Build `scripts/check-secrets-pre-commit.py`
2. Use CREDENTIAL_PATTERNS from secrets_manager.py
3. Add intelligent placeholder detection
4. Provide actionable error messages

### Phase 4: Documentation
1. Document what gets scanned and why
2. Provide troubleshooting guide
3. Create process for adding exceptions

---

## 11. Performance Considerations

**Current CI performance:**
- Full repository scan (fetch-depth: 0)
- Runs on GitHub Actions (cloud resources)
- No time constraints

**Pre-commit requirements:**
- MUST complete in <5 seconds for typical commits
- Should only scan staged files (not entire history)
- Must provide fast feedback loop

**Optimization strategies:**
1. Scan only staged files: `--staged` flag
2. Exclude large binary files
3. Skip already-scanned committed history
4. Use caching for gitleaks binary
5. Parallelize scanning if multiple files

---

## 12. Known Safe Secrets Audit

### Secrets that appear in codebase and are SAFE:

1. **Development SAML Certificate:**
   - Location: `src/core/shared/auth/certs/sp.key`
   - Status: Already in .gitleaksignore
   - Justification: Self-signed, dev-only

2. **Placeholder JWT Secrets:**
   - Pattern: `dev-jwt-secret-min-32-chars-required`
   - Location: Config examples
   - Action: Add to allow-list

3. **Example API Keys:**
   - Pattern: `sk-ant-XXX...XXX` (redacted format)
   - Location: Documentation
   - Action: Add pattern to allow-list

**Action Required:**
- Full audit of `.env.example` and `.env.dev`
- Verify no real credentials exist in examples
- Document each safe secret with fingerprint

---

## Conclusion

**Current State:**
- Gitleaks is operational in CI but not pre-commit
- Minimal configuration with only one ignored secret
- No custom rules for ACGS-2 specific patterns
- Gap between runtime validation (secrets_manager.py) and commit-time prevention

**Path Forward:**
1. ✅ Analysis complete (this document)
2. 🎯 Next: Review secrets_manager.py patterns (subtask 1.2)
3. 🎯 Next: Design hook strategy (subtask 1.3)
4. 🎯 Next: Implement gitleaks pre-commit integration (phase 2)

**Key Insights:**
- Pre-commit integration is straightforward (gitleaks already in use)
- Custom rules needed for ACGS-2 specific credential types
- Placeholder detection critical to avoid false positives
- Performance optimization required for good developer experience

---

**Acceptance Criteria Met:**
- ✅ Documented list of currently ignored secrets (1 item: SAML cert)
- ✅ Understanding of gitleaks configuration in CI (default rules, v2 action)
- ✅ List of file patterns that need secret scanning (detailed in section 8)
