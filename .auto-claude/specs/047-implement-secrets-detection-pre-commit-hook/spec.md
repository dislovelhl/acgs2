# Specification: Implement Secrets Detection Pre-commit Hook

## Overview

To prevent accidental leakage of sensitive information (API keys, passwords, private keys), ACGS-2 requires an automated secrets detection mechanism. This task implements a `pre-commit` hook using `detect-secrets` to scan for potential credentials before code is committed to the repository.

## Rationale

Secret leakage is a common source of security breaches. Once a secret is committed to a git repository, it remains in the history even if deleted in a later commit, requiring complex cleanup (e.g., rewriting history with BFG or `git-filter-repo`) and immediate revocation of the secret.

- **OWASP A05:2021**: Security Misconfiguration.
- **Proactive Security**: Catching secrets before they leave the developer's machine is the most effective defense.

## Task Scope

### This Task Will:

- [ ] Initialize a `.pre-commit-config.yaml` file in the repository root.
- [ ] Integrate the `detect-secrets` hook.
- [ ] Create an initial baseline (`.secrets.baseline`) to ignore existing false positives and manage existing secrets securely.
- [ ] Add `detect-secrets` to the development dependencies.
- [ ] Provide documentation on how developers can handle false positives using inline comments.

## Implementation Details

### Configuration (`.pre-commit-config.yaml`)

```yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ["--baseline", ".secrets.baseline"]
        exclude: .*/tests/.*|.*\.ipynb
```

### Baseline Creation

1.  Install `detect-secrets`: `pip install detect-secrets`.
2.  Generate baseline: `detect-secrets scan > .secrets.baseline`.
3.  Audit baseline: Manually review `.secrets.baseline` to ensure no actual secrets are being ignored.

### Developer Workflow

Add instructions to `CONTRIBUTING.md` or a new `docs/security/secrets_management.md`:

- **Excluding false positives**: Use `# pragma: allowlist secret`.
- **Updating baseline**: `detect-secrets scan --baseline .secrets.baseline`.

## Verification Plan

### Automated Tests

1.  **Positive Test**:
    - Create a temporary file with a string that looks like an AWS API Key (e.g., `AKIAIMNO7CQH6O5AABC`).
    - Run `pre-commit run --all-files`.
    - **Expected Result**: The hook fails and identifies the secret.
2.  **Negative Test**:
    - Commit a regular code change.
    - Run `pre-commit run --all-files`.
    - **Expected Result**: The hook passes.

### Manual Verification

1.  Verify that `.secrets.baseline` is present and doesn't contain sensitive data (only hashes and metadata).
2.  Ensure `pre-commit install` is documented for new developers.

## Risks & Dependencies

- **False Positives**: Overly aggressive detection can frustrate developers.
- **Dependency**: Requires developers to have `pre-commit` installed on their local machine.
