# SOP: Standard Operating Procedure for Secrets Remediation

If a secret (private key, API token, password) has been accidentally committed to the repository, follow these steps immediately.

## 1. Rotate the Secret

The most important step is to nullify the leaked secret by generating a new one and updating all systems that use it.

- **Revoke** the old credential.
- **Generate** a new strong credential.
- **Update** CI/CD secrets, configuration files, and environment variables.

## 2. Remove the Secret from the Current Version

Delete the file or remove the secret string from the code and commit the change.

```bash
git rm --cached <path_to_secret_file>
# Or edit the code to remove the secret
git add .
git commit -m "SEC: Remove accidentally committed secret"
```

## 3. Clean Git History

Simply removing the secret in a new commit is NOT enough because it remains in the Git history. Use `git-filter-repo` (recommended) or `BFG Repo-Cleaner`.

### Using git-filter-repo

```bash
# Install tool
pip install git-filter-repo

# Remove a file from all history
git filter-repo --path src/path/to/secret.key --invert-paths
```

## 4. Notify Security Officers

Report the incident to the security team so they can assess potential impact and audit logs for unauthorized access during the exposure window.

## 5. Prevention

- Ensure `.gitignore` is correctly configured.
- Use pre-commit hooks (like `gitleaks` or `detect-secrets`).
- Never use production secrets in development.
