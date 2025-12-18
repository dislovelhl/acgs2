# ACGS-2 Version Control Strategy

**Constitutional Hash**: `cdd01ef066bc6cf2`

## 1. Branching Model: Gitflow

ACGS-2 uses the **Gitflow** branching model to manage complex release cycles and ensure production stability.

### Branch Types

| Branch | Purpose | Source | Target |
|--------|---------|--------|--------|
| `main` | Production-ready code. Always stable. | `release/*`, `hotfix/*` | - |
| `develop` | Integration branch for features. | `main` | `main` (via release) |
| `feature/*` | New features or enhancements. | `develop` | `develop` |
| `release/*` | Preparation for a new production release. | `develop` | `main`, `develop` |
| `hotfix/*` | Urgent fixes for production issues. | `main` | `main`, `develop` |

### Workflow

1.  **Feature Development**: Create `feature/my-feature` from `develop`. Merge back to `develop` via Pull Request.
2.  **Release Preparation**: When `develop` is ready for release, create `release/vX.Y.Z`. Perform final testing and bug fixes.
3.  **Production Release**: Merge `release/vX.Y.Z` into `main` and tag it. Merge back into `develop`.
4.  **Emergency Fixes**: Create `hotfix/my-fix` from `main`. Merge into `main` and `develop`.

## 2. Commit Message Convention: Conventional Commits

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification.

### Format

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types

- `feat`: A new feature.
- `fix`: A bug fix.
- `docs`: Documentation only changes.
- `style`: Changes that do not affect the meaning of the code (white-space, formatting, etc).
- `refactor`: A code change that neither fixes a bug nor adds a feature.
- `perf`: A code change that improves performance.
- `test`: Adding missing tests or correcting existing tests.
- `build`: Changes that affect the build system or external dependencies.
- `ci`: Changes to CI configuration files and scripts.
- `chore`: Other changes that don't modify src or test files.
- `revert`: Reverts a previous commit.

### Constitutional Requirement

Any commit that modifies core governance logic, the `enhanced_agent_bus`, or `deliberation_layer` **MUST** include the constitutional hash in the footer:

```
feat(bus): implement rust-based message validation

Constitutional-Hash: cdd01ef066bc6cf2
```

## 3. Pull Request (PR) Guidelines

### Requirements for Merging

1.  **Code Review**: Minimum of **2 approvals** from senior engineers.
2.  **CI/CD**: All automated checks must pass (Linting, Type Checking, Security Scans).
3.  **Testing**:
    *   Minimum **80% code coverage** for new code.
    *   All existing tests must pass.
    *   Performance benchmarks must not regress (for core bus changes).
4.  **Documentation**: Update relevant `.md` files and API references.
5.  **Constitutional Validation**: PRs affecting governance must be verified against the constitutional hash.

### PR Template

```markdown
## Description
[Describe the changes and the motivation]

## Type of Change
- [ ] feat
- [ ] fix
- [ ] docs
- [ ] refactor
- [ ] perf

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Coverage >= 80%

## Constitutional Compliance
- [ ] Constitutional Hash included in commits
- [ ] Governance impact analyzed

## Checklist
- [ ] Documentation updated
- [ ] CI checks passing
```
