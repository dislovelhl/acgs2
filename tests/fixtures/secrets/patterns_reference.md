# ACGS-2 Secrets Detection Patterns Reference

**Constitutional Hash:** cdd01ef066bc6cf2

This document provides a comprehensive reference for all credential patterns used in ACGS-2 secrets detection, with examples of safe and unsafe values for testing.

## Overview

All patterns are defined in `acgs2-core/shared/secrets_manager.py` in the `CREDENTIAL_PATTERNS` dictionary. The secrets detection system validates credentials against these regex patterns.

## Pattern Reference Table

| # | Pattern Name            | Regex Pattern                              | Description                                |
|---|-------------------------|--------------------------------------------|--------------------------------------------|
| 1 | CLAUDE_CODE_OAUTH_TOKEN | `^sk-ant-oat\d{2}-[A-Za-z0-9_-]{60,}$`    | Claude Code OAuth access tokens           |
| 2 | OPENAI_API_KEY          | `^sk-[A-Za-z0-9]{20,}$`                   | OpenAI API keys (including project keys)  |
| 3 | OPENROUTER_API_KEY      | `^sk-or-v1-[A-Za-z0-9]{60,}$`             | OpenRouter API keys                       |
| 4 | HF_TOKEN                | `^hf_[A-Za-z0-9]{30,}$`                   | HuggingFace access tokens                 |
| 5 | ANTHROPIC_API_KEY       | `^sk-ant-[A-Za-z0-9_-]{80,}$`             | Anthropic API keys                        |
| 6 | AWS_ACCESS_KEY_ID       | `^AKIA[A-Z0-9]{16}$`                      | AWS access key IDs                        |
| 7 | JWT_SECRET              | `^[A-Fa-f0-9]{64}$`                       | JWT signing secrets (64-char hex)         |
| 8 | VAULT_TOKEN             | `^(hvs\.|s\.)[A-Za-z0-9]{20,}$`           | HashiCorp Vault tokens                    |

---

## Detailed Pattern Breakdowns

### 1. CLAUDE_CODE_OAUTH_TOKEN

**Pattern:** `^sk-ant-oat\d{2}-[A-Za-z0-9_-]{60,}$`

**Format:**
- Prefix: `sk-ant-oat`
- Version: 2 digits (e.g., `01`, `99`)
- Separator: `-`
- Token body: 60+ characters (alphanumeric, underscore, hyphen)

**✅ Safe Examples:**
```
dev-claude-code-token-placeholder
test-claude-code-oauth-token
<your-claude-code-token>
your-claude-code-token-here
sk-ant-oat01-XXX...XXX
```

**❌ Unsafe Examples (Fake - for testing only):**
```
sk-ant-oat01-RealLookingButFakePleaseDontUseThisToken123456789012345678901234567890ABC
sk-ant-oat99-AnotherFakeTokenThatLooksLikeItCouldBeRealButIsntTrustMeXYZ1234567890
```

**Detection Logic:**
- Must start with `sk-ant-oat` followed by exactly 2 digits
- Token body must be 60+ characters
- Only alphanumeric, underscore, and hyphen allowed

---

### 2. OPENAI_API_KEY

**Pattern:** `^sk-[A-Za-z0-9]{20,}$`

**Format:**
- Prefix: `sk-`
- Key body: 20+ alphanumeric characters
- Variations: `sk-proj-` for project keys

**✅ Safe Examples:**
```
test-openai-api-key-12345
dev-openai-key
your-openai-api-key-here
<insert-openai-key>
sk-XXX...XXX
```

**❌ Unsafe Examples (Fake - for testing only):**
```
sk-FakeButValidFormatOpenAIKey123456789012345
sk-proj-1234567890ABCDEFGHIJKLMNOPabcdefghijklmnop
sk-AnotherFakeLookingKey987654321ABCDEF
```

**Detection Logic:**
- Must start with `sk-`
- Minimum 20 alphanumeric characters after prefix
- No special characters allowed (except hyphen in prefix)

---

### 3. OPENROUTER_API_KEY

**Pattern:** `^sk-or-v1-[A-Za-z0-9]{60,}$`

**Format:**
- Prefix: `sk-or-v1-`
- Key body: 60+ alphanumeric characters

**✅ Safe Examples:**
```
dev-openrouter-api-key
test-openrouter-key
your-openrouter-key-here
<insert-openrouter-key>
sk-or-v1-XXX...XXX
```

**❌ Unsafe Examples (Fake - for testing only):**
```
sk-or-v1-FakeLookingOpenRouterKeyThatMatchesPatternExactly123456789012345678901234567890
sk-or-v1-AnotherFakeTokenForTestingPurposesOnlyDoNotUse987654321ABCDEFabcdef
```

**Detection Logic:**
- Must start with `sk-or-v1-`
- Minimum 60 alphanumeric characters after prefix
- No special characters allowed

---

### 4. HF_TOKEN (HuggingFace)

**Pattern:** `^hf_[A-Za-z0-9]{30,}$`

**Format:**
- Prefix: `hf_`
- Token body: 30+ alphanumeric characters

**✅ Safe Examples:**
```
test-huggingface-token
dev-hf-token
your-hf-token
<your-huggingface-token>
hf_XXX...XXX
```

**❌ Unsafe Examples (Fake - for testing only):**
```
hf_FakeLookingHuggingFaceTokenForTestingOnly123456789012345678
hf_AnotherFakeTokenThatLooksRealistic987654321ABCDEFGHIJKLMabcdefgh
```

**Detection Logic:**
- Must start with `hf_`
- Minimum 30 alphanumeric characters after prefix
- No special characters allowed

---

### 5. ANTHROPIC_API_KEY

**Pattern:** `^sk-ant-[A-Za-z0-9_-]{80,}$`

**Format:**
- Prefix: `sk-ant-`
- Key body: 80+ characters (alphanumeric, underscore, hyphen)

**✅ Safe Examples:**
```
dev-anthropic-key-placeholder
test-anthropic-api-key
your-anthropic-key-here
<your-anthropic-key>
sk-ant-XXX...XXX
```

**❌ Unsafe Examples (Fake - for testing only):**
```
sk-ant-FakeAnthropicKeyForTestingPurposesOnlyDoNotUseInProductionOrDevelopment1234567890ABCDEFGHIJKLMNOP
sk-ant-AnotherFakeLookingAnthropicKeyThatMatchesThePatternButIsCompletelyRandomData987654321XYZ
```

**Detection Logic:**
- Must start with `sk-ant-`
- Minimum 80 characters after prefix
- Only alphanumeric, underscore, and hyphen allowed
- Distinguishes from CLAUDE_CODE_OAUTH_TOKEN by lack of `oat\d{2}-` pattern

---

### 6. AWS_ACCESS_KEY_ID

**Pattern:** `^AKIA[A-Z0-9]{16}$`

**Format:**
- Prefix: `AKIA`
- Key body: Exactly 16 uppercase alphanumeric characters
- Total length: Exactly 20 characters

**✅ Safe Examples:**
```
dev-aws-access-key-id
test-aws-key
your-aws-access-key-id
<your-aws-key>
AKIA****************
```

**❌ Unsafe Examples (Fake - for testing only):**
```
AKIAFAKE1234567890AB
AKIATEST9876543210XY
AKIARANDOMFAKEKEY123
```

**Detection Logic:**
- Must start with `AKIA` (AWS IAM Access Key prefix)
- Exactly 16 uppercase alphanumeric characters after prefix
- Total length must be exactly 20 characters
- Very strict format - one of the most specific patterns

---

### 7. JWT_SECRET

**Pattern:** `^[A-Fa-f0-9]{64}$`

**Format:**
- 64 hexadecimal characters (0-9, A-F, a-f)
- No prefix or separators
- Case-insensitive hex

**✅ Safe Examples:**
```
dev-jwt-secret-min-32-chars-required
test-jwt-secret
your-jwt-secret-here
<your-jwt-secret>
************************************************************
```

**❌ Unsafe Examples (Fake - for testing only):**
```
abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890
FEDCBA0987654321FEDCBA0987654321FEDCBA0987654321FEDCBA0987654321
0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
```

**Detection Logic:**
- Must be exactly 64 characters
- Only hexadecimal characters allowed (0-9, A-F, a-f)
- Commonly used for SHA-256 derived secrets
- No prefix or separators

**Important Notes:**
- This pattern can have false positives with SHA-256 hashes in documentation
- Use placeholder patterns (dev-*, test-*) to avoid false positives
- Real JWT secrets should be loaded from environment/Vault via secrets_manager.py

---

### 8. VAULT_TOKEN

**Pattern:** `^(hvs\.|s\.)[A-Za-z0-9]{20,}$`

**Format:**
- Prefix: `hvs.` (Vault service token) or `s.` (legacy)
- Token body: 20+ alphanumeric characters

**✅ Safe Examples:**
```
dev-vault-token-placeholder
test-vault-token
your-vault-token-here
<your-vault-token>
hvs.XXX...XXX
s.XXX...XXX
```

**❌ Unsafe Examples (Fake - for testing only):**
```
hvs.FakeVaultTokenForTestingOnly123456789012345
s.AnotherFakeVaultTokenThatLooksRealButIsnt987654321
hvs.RandomlyGeneratedFakeVaultTokenABCDEF
```

**Detection Logic:**
- Must start with `hvs.` or `s.`
- Minimum 20 alphanumeric characters after prefix
- `hvs.` is the modern Vault service token format
- `s.` is legacy Vault token format

---

## Safe Placeholder Patterns

The following placeholder patterns are **always considered safe** across all credential types:

### Prefix-Based Placeholders
```
dev-*           # Development environment (e.g., dev-api-key)
test-*          # Testing environment (e.g., test-token)
your-*          # Instructional (e.g., your-api-key-here)
example-*       # Example values (e.g., example-token)
sample-*        # Sample data (e.g., sample-key)
placeholder-*   # Explicit placeholders (e.g., placeholder-secret)
staging-*       # Staging environment safe values
local-*         # Local development values
```

### Instructional Markers
```
<...>           # Angle bracket placeholders (e.g., <your-key>)
xxx             # Redacted format (e.g., sk-ant-xxx...xxx)
***             # Asterisk redaction (e.g., ******)
[redacted]      # Explicit redaction marker
<hidden>        # Hidden value marker
example         # Example indicator
template        # Template indicator
changeme        # Placeholder requiring change
replace         # Placeholder requiring replacement
todo            # To be filled (e.g., TODO: add key)
fixme           # To be fixed (e.g., FIXME: replace)
```

### Known Safe Development Values
```
dev-jwt-secret-min-32-chars-required    # From .env.dev
dev_password                             # From .env.dev
mlflow_password                          # From .env.dev
changeme                                 # Generic placeholder
secret                                   # Generic placeholder
password                                 # Generic placeholder
```

---

## Detection System Architecture

### Layer 1: Gitleaks (Industry Standard)
- 140+ generic patterns for common secrets
- Detects AWS, Google Cloud, Azure, GitHub tokens, etc.
- Configuration: `.gitleaks.toml`
- Exceptions: `.gitleaksignore`

### Layer 2: ACGS-2 Custom Hook
- 8 ACGS-2-specific patterns from `secrets_manager.py`
- AI provider credentials (Claude Code, OpenAI, OpenRouter, HuggingFace, Anthropic)
- Infrastructure secrets (AWS, JWT, Vault)
- Configuration: `.secrets-allowlist.yaml`
- Script: `scripts/check-secrets-pre-commit.py`

### Integration Points
1. **Pre-commit hooks** - Runs on every commit
2. **CI/CD pipeline** - Runs on every PR
3. **Runtime validation** - `secrets_manager.py` validates at runtime

---

## Testing Strategy

### Test Coverage

Each pattern should be tested with:

1. ✅ **Safe placeholders** - Should PASS
   - Development prefixes (dev-*, test-*)
   - Instructional markers (<...>, your-*)
   - Redacted examples (XXX...XXX, ***)
   - Known safe values

2. ❌ **Realistic-looking fakes** - Should FAIL
   - Match the regex pattern exactly
   - Look like real credentials
   - Randomly generated for testing
   - Clearly marked as FAKE

3. ✅ **Edge cases** - Should PASS appropriately
   - Empty strings
   - Comments with placeholders
   - Template strings (${VAR}, {{VAR}})
   - Multi-line configurations

### File Types Tested

- **Python files** (`.py`) - Variable assignments, config classes
- **Environment files** (`.env`) - KEY=value format
- **YAML files** (`.yaml`, `.yml`) - Nested configurations
- **JSON files** (`.json`) - Object structures

### Fixture Organization

```
tests/fixtures/secrets/
├── README.md                    # Overview and safety warnings
├── patterns_reference.md        # This file
├── safe_placeholders.py         # Python safe examples
├── unsafe_secrets.py            # Python unsafe examples
├── safe_placeholders.env        # .env safe examples
├── unsafe_secrets.env           # .env unsafe examples
├── safe_placeholders.yaml       # YAML safe examples
└── unsafe_secrets.yaml          # YAML unsafe examples
```

---

## Security Best Practices

### ✅ DO:
- Use development placeholders (dev-*, test-*)
- Load real secrets from environment variables
- Use `secrets_manager.py` for production secrets
- Store production secrets in Vault
- Add legitimate exceptions to `.gitleaksignore` with justification
- Use `.secrets-allowlist.yaml` for pattern-based exceptions

### ❌ DON'T:
- Commit real API keys or tokens
- Use production credentials in development
- Hardcode secrets in source code
- Skip pre-commit hooks to bypass detection
- Remove secrets from git history manually (use `docs/SECRETS_QUICK_FIX.md`)

---

## References

- **Patterns Source:** `acgs2-core/shared/secrets_manager.py`
- **Custom Hook:** `scripts/check-secrets-pre-commit.py`
- **Gitleaks Config:** `.gitleaks.toml`
- **Allow-list Config:** `.secrets-allowlist.yaml`
- **Documentation:** `docs/SECRETS_DETECTION.md`
- **Quick-fix Guide:** `docs/SECRETS_QUICK_FIX.md`

---

**Last Updated:** 2026-01-04
**Maintained by:** ACGS-2 Security Team
