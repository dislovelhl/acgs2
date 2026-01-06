# ACGS-2 Workspace Rules — Task Management, Commits, Don’ts

## task.md format

```markdown
# Current Task: [Feature/Bug Description]

## Objective

Brief description of what needs to be accomplished.

## Checklist

- [x] Research existing implementation
- [/] Implement core functionality ← In progress
- [ ] Add unit tests (85% coverage)
- [ ] Add integration tests
- [ ] Update documentation
- [ ] Constitutional compliance check

## Notes

- Key decisions made
- Dependencies identified
- Blockers encountered
```

## Status markers

| Marker | Meaning                          |
| ------ | -------------------------------- |
| `[ ]`  | Pending                          |
| `[/]`  | In progress (only ONE at a time) |
| `[x]`  | Completed                        |
| `[-]`  | Cancelled/Not needed             |

## Commit conventions

Follow Conventional Commits:

```
type(scope): description

[optional body]

[optional footer]
```

### Types

| Type       | When to Use                         |
| ---------- | ----------------------------------- |
| `feat`     | New feature                         |
| `fix`      | Bug fix                             |
| `docs`     | Documentation only                  |
| `style`    | Formatting, no code change          |
| `refactor` | Restructure without behavior change |
| `test`     | Adding/modifying tests              |
| `chore`    | Build, CI, dependencies             |
| `perf`     | Performance improvements            |

### Examples

```
feat(agent-bus): add adaptive governance threshold adjustment

- Implement ML-based threshold calculation
- Add RandomForest model for impact scoring
- Integrate with constitutional validation

Refs: #1234
```

```
fix(policy-registry): prevent OPA timeout on large policies

Increase timeout from 5s to 30s for complex Rego evaluation.

Closes: #5678
```

## Don’ts

1. Don’t use `Any` when project types exist in `shared/types.py`
2. Don’t commit secrets (pre-commit hooks will block)
3. Don’t skip tests for new functionality
4. Don’t ignore constitutional compliance validation
5. Don’t hardcode configuration values
6. Don’t bypass MACI role separation
7. Don’t leave `task.md` items incomplete
8. Don’t commit with coverage below 85%

---

**Version**: 4.0 | **Updated**: 2026-01-04 | **Constitutional Hash**: `cdd01ef066bc6cf2`
