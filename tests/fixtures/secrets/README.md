# ACGS-2 Secrets Detection Test Fixtures

**⚠️ IMPORTANT: This directory contains FAKE secrets for testing only!**

This directory contains test fixtures for validating the ACGS-2 secrets detection system. All secrets in this directory are **randomly generated test data** and are **NOT real credentials**.

## Purpose

These fixtures test that:
1. ✅ **Safe placeholders** (dev-*, test-*, etc.) are allowed through
2. ❌ **Real-looking secrets** are correctly detected and blocked
3. ✅ **Each CREDENTIAL_PATTERN** from `secrets_manager.py` is tested
4. ✅ **False positives** are minimized via allow-list configuration

## Structure

```
tests/fixtures/secrets/
├── README.md                    # This file
├── safe_placeholders.py         # Python file with safe development values
├── unsafe_secrets.py            # Python file with real-looking fake secrets
├── safe_placeholders.env        # .env file with safe placeholders
├── unsafe_secrets.env           # .env file with dangerous-looking values
├── safe_placeholders.yaml       # YAML config with safe values
├── unsafe_secrets.yaml          # YAML config with dangerous values
└── patterns_reference.md        # Complete patterns reference with examples
```

## Credential Patterns Tested

All fixtures cover these 8 patterns from `secrets_manager.py`:

| Pattern                  | Format                                | Example (Fake)                                          |
|--------------------------|---------------------------------------|---------------------------------------------------------|
| CLAUDE_CODE_OAUTH_TOKEN  | `sk-ant-oat\d{2}-[A-Za-z0-9_-]{60,}` | sk-ant-oat01-FAKE_TOKEN_ABC123...                      |
| OPENAI_API_KEY          | `sk-[A-Za-z0-9]{20,}`                | sk-FAKE12345678901234567                               |
| OPENROUTER_API_KEY      | `sk-or-v1-[A-Za-z0-9]{60,}`          | sk-or-v1-FAKE_TOKEN_ABC123...                          |
| HF_TOKEN                | `hf_[A-Za-z0-9]{30,}`                | hf_FAKE1234567890123456789012345678                    |
| ANTHROPIC_API_KEY       | `sk-ant-[A-Za-z0-9_-]{80,}`          | sk-ant-FAKE_TOKEN_ABC123...                            |
| AWS_ACCESS_KEY_ID       | `AKIA[A-Z0-9]{16}`                   | AKIAFAKE1234567890AB                                   |
| JWT_SECRET              | `[A-Fa-f0-9]{64}`                    | abcd1234...                                            |
| VAULT_TOKEN             | `(hvs\.|s\.)[A-Za-z0-9]{20,}`        | hvs.FAKE1234567890...                                  |

## Safe vs Unsafe Examples

### ✅ Safe Placeholders (Should PASS)
- `dev-jwt-secret-min-32-chars-required` - Development prefix
- `test-api-key-12345` - Test prefix
- `your-anthropic-key-here` - Instructional placeholder
- `<your-api-key>` - Angle bracket placeholder
- `sk-ant-XXX...XXX` - Redacted example
- Empty strings or generic values like `changeme`

### ❌ Unsafe Secrets (Should FAIL)
- `sk-ant-oat01-RealLookingButFakePleaseDontUseThisToken123456789012345678901234567890`
- `sk-FakeButValidFormat123456789012`
- `AKIAFAKE1234567890AB`
- `hf_FakeLookingTokenThatMatchesThePatternExactly12345678`

## Exclusion from Scanning

This directory is **automatically excluded** from secrets scanning via:

1. **Pre-commit config** (`.pre-commit-config.yaml`):
   ```yaml
   exclude: ^(.*/tests/fixtures/.*|...)
   ```

2. **Allow-list config** (`.secrets-allowlist.yaml`):
   ```yaml
   test_paths:
     - "tests/fixtures/"
   ```

3. **Gitleaks config** (`.gitleaks.toml`):
   ```toml
   [allowlist]
   paths = ['''tests/.*''']
   ```

## Usage in Tests

These fixtures are used by `tests/test_secrets_detection.py` to validate:
- Pattern matching accuracy
- False positive rate
- Allow-list effectiveness
- Integration with secrets_manager.py

## Security Note

**These are NOT real secrets!** They are randomly generated test data designed to look like real credentials for testing purposes only. Never use these values in production or development environments.

If you accidentally commit a **real secret**, follow the emergency procedures in `docs/SECRETS_QUICK_FIX.md`.

---

**Constitutional Hash:** cdd01ef066bc6cf2
**Last Updated:** 2026-01-04
