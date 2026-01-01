# CI Migration Guide (v2.3.0)

> **Constitutional Hash**: `cdd01ef066bc6cf2`  
> **From**: .gitlab-ci.yml, Jenkinsfile, scattered workflows  
> **To**: [.github/workflows/acgs2-ci-cd.yml](.github/workflows/acgs2-ci-cd.yml) + Dependabot  
> **Status**: Complete Phase 3.6

## Migration Steps

1. **Backup Old CI**:
   ```
   git mv .gitlab-ci.yml .gitlab-ci.yml.bak
   git mv Jenkinsfile Jenkinsfile.bak
   ```

2. **Enable GitHub Actions**:
   - Settings > Actions > General > Allow all actions

3. **Dependabot**:
   - `.github/dependabot.yml` auto-updates deps weekly.

4. **New Workflow** [acgs2-ci-cd.yml](.github/workflows/acgs2-ci-cd.yml):
   - Lint, test, cov 100%
   - Build Docker
   - Deploy staging
   - Security scan

## Old vs New

| Old | New |
|----|-----|
| .gitlab-ci.yml (scattered) | acgs2-ci-cd.yml (consolidated)
| Jenkinsfile (manual) | GitHub Actions (auto)
| No Dependabot | Dependabot weekly

## Verification

```bash
act  # Local test
.github/workflows/acgs2-ci-cd.yml push
```

**Migration Complete**: All CI consolidated, Dependabot enabled.
