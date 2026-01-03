# ACGS-2 SDK Publishing Guide

**Constitutional Hash:** `cdd01ef066bc6cf2`

This guide covers publishing the ACGS-2 SDKs to their respective package registries.

## Overview

ACGS-2 provides official SDKs in three languages:
- **Python**: Published to PyPI
- **TypeScript**: Published to npm
- **Go**: Published via Go modules

## Prerequisites

### For All SDKs
- GitHub repository access with write permissions
- GitHub Actions enabled
- Appropriate API tokens configured as GitHub Secrets

### Python SDK
- PyPI account with API token
- GitHub Secret: `PYPI_API_TOKEN`
- Test PyPI token (optional): `TEST_PYPI_API_TOKEN`

### TypeScript SDK
- npm account with access token
- GitHub Secret: `NPM_TOKEN`
- Package scope: `@acgs/sdk`

### Go SDK
- No additional tokens required (distributed via Git tags)
- Module path: `github.com/acgs2/sdk/go`

## Publishing Workflows

### Automated Publishing (Recommended)

Publishing is automated via GitHub Actions. Create a release with the appropriate tag format:

#### Python SDK Release
```bash
git tag -a sdk/python/v2.0.0 -m "Python SDK v2.0.0"
git push origin sdk/python/v2.0.0
```

#### TypeScript SDK Release
```bash
git tag -a sdk/typescript/v2.0.0 -m "TypeScript SDK v2.0.0"
git push origin sdk/typescript/v2.0.0
```

#### Go SDK Release
```bash
git tag -a sdk/go/v2.0.0 -m "Go SDK v2.0.0"
git push origin sdk/go/v2.0.0
```

### Manual Publishing (Alternative)

#### Python SDK

1. Install build tools:
```bash
pip install build twine
```

2. Build the package:
```bash
cd acgs2-core/sdk/python
python -m build
```

3. Check the package:
```bash
twine check dist/*
```

4. Upload to PyPI:
```bash
twine upload dist/*
```

#### TypeScript SDK

1. Install dependencies:
```bash
cd acgs2-core/sdk/typescript
npm ci
```

2. Build the package:
```bash
npm run build
```

3. Publish to npm:
```bash
npm publish --access public
```

#### Go SDK

1. Run the publishing script:
```bash
./scripts/publish-sdk-go.sh v2.0.0
```

This script will:
- Create and push the appropriate tag
- Temporarily update go.mod for publishing
- Validate the module
- Restore the local go.mod

## Version Management

### Version Format
All SDKs use semantic versioning: `MAJOR.MINOR.PATCH`

### Tag Format
- Python: `sdk/python/vMAJOR.MINOR.PATCH`
- TypeScript: `sdk/typescript/vMAJOR.MINOR.PATCH`
- Go: `sdk/go/vMAJOR.MINOR.PATCH`

### Version Files
Update version numbers in:
- Python: `acgs2-core/sdk/python/pyproject.toml`
- TypeScript: `acgs2-core/sdk/typescript/package.json`
- Go: Tag-based versioning (no version file needed)

## GitHub Secrets Configuration

Add these secrets to your GitHub repository:

### Required Secrets
```bash
PYPI_API_TOKEN=your_pypi_api_token
NPM_TOKEN=your_npm_token
```

### Optional Secrets (for testing)
```bash
TEST_PYPI_API_TOKEN=your_test_pypi_token
```

## Testing Before Publishing

### Python SDK Testing
```bash
cd acgs2-core/sdk/python
pip install -e ".[dev]"
pytest
```

### TypeScript SDK Testing
```bash
cd acgs2-core/sdk/typescript
npm install
npm test
npm run build
```

### Go SDK Testing
```bash
cd acgs2-core/sdk/go
go test -v ./...
go build ./...
```

## Post-Publishing Verification

### Python SDK
```bash
pip install acgs2-sdk==2.0.0
python -c "import acgs2_sdk; print('✅ Python SDK installed')"
```

### TypeScript SDK
```bash
npm install @acgs/sdk@2.0.0
node -e "const sdk = require('@acgs/sdk'); console.log('✅ TypeScript SDK installed');"
```

### Go SDK
```bash
go get github.com/acgs2/sdk/go@v2.0.0
go list -m github.com/acgs2/sdk/go@v2.0.0
```

## Troubleshooting

### Python Publishing Issues

**Error: "Package already exists"**
- Increment version number in `pyproject.toml`
- Delete the release if it was a mistake

**Error: "Invalid API token"**
- Verify `PYPI_API_TOKEN` secret is correct
- Check PyPI account has maintainer permissions

### TypeScript Publishing Issues

**Error: "Package name already exists"**
- The `@acgs/sdk` scope should be pre-registered
- Contact npm support if needed

**Error: "Invalid npm token"**
- Verify `NPM_TOKEN` secret is correct
- Check npm account has publish permissions for the scope

### Go Publishing Issues

**Error: "Module path mismatch"**
- Ensure the tag format matches the go.mod module path
- The publishing script handles this automatically

**Error: "Tag already exists"**
- Delete the tag and re-run the publishing script
- Use a different version number

## Changelog Management

Maintain changelogs in each SDK directory:

- `acgs2-core/sdk/python/CHANGELOG.md`
- `acgs2-core/sdk/typescript/CHANGELOG.md`
- `acgs2-core/sdk/go/CHANGELOG.md`

Format follows [Keep a Changelog](https://keepachangelog.com/):

```markdown
## [2.0.0] - 2025-01-03

### Added
- New Policy Registry service
- API Gateway integration
- Constitutional hash validation

### Changed
- Updated retry logic
- Improved error handling

### Fixed
- Memory leak in connection pooling
```

## Release Process Checklist

- [ ] Update version numbers in all relevant files
- [ ] Update changelogs with release notes
- [ ] Run full test suite for all SDKs
- [ ] Create git tag with correct format
- [ ] Push tag to trigger CI/CD
- [ ] Verify package appears in registry
- [ ] Update documentation if needed
- [ ] Announce release in appropriate channels

## Support

For issues with SDK publishing:
1. Check GitHub Actions logs
2. Verify GitHub secrets are configured
3. Test locally before publishing
4. Check package registry status pages

## Security Notes

- Never commit API tokens to git
- Use GitHub repository secrets for all tokens
- Rotate tokens regularly
- Use separate tokens for production vs test registries
