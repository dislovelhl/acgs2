# Neural Coordination Pattern: Smart Debug Pydantic Migration

**Pattern ID:** smart_debug_pydantic_migration
**Date Created:** 2024-12-30
**Constitutional Hash:** cdd01ef066bc6cf2
**Success Rate:** 100%

## Pattern Overview

This coordination pattern captures a successful debugging workflow for identifying and fixing Pydantic V2 deprecation warnings across multiple files.

## Workflow Phases

### Phase 1: Triage (Fast)
**Actions:**
- `git_status_check` - Review uncommitted changes
- `log_analysis` - Check for recent errors in logs
- `test_suite_execution` - Verify baseline health

**Outcome:** Identified healthy baseline (2,796 tests passing)

### Phase 2: Discovery (Fast)
**Actions:**
- `import_with_warnings_as_errors` - Surface hidden deprecation warnings
- `traceback_analysis` - Trace warning to source file

**Technique:** Python warnings filter
```python
python3 -W error::DeprecationWarning -c "import module"
```

**Outcome:** Found deprecation warning source

### Phase 3: Scope Analysis (Fast)
**Actions:**
- `grep_pattern_search` - Find all occurrences of deprecated pattern
- `file_enumeration` - Count affected files

**Pattern Searched:** `class Config:`
**Outcome:** Identified 7 affected files

### Phase 4: Fix Iteration 1 (Medium)
**Actions:**
- `replace_class_config_with_configdict` - Migrate to Pydantic V2 pattern
- `import_update` - Add required imports

**Learning:** Secondary deprecation revealed (`json_encoders` also deprecated)

### Phase 5: Fix Iteration 2 (Medium)
**Actions:**
- `replace_json_encoders_with_field_serializer` - Use decorator approach
- `handle_optional_fields` - Apply `when_used="unless-none"` parameter

**Technique:** Field serializer decorators
```python
@field_serializer("field_name", when_used="unless-none")
def serialize_field(self, value: datetime) -> str:
    return value.isoformat()
```

**Outcome:** All deprecations resolved

### Phase 6: Validation (Medium)
**Actions:**
- `full_test_suite_run` - Execute all tests
- `import_verification` - Confirm no warnings

**Outcome:** 2,796 tests passed, 0 deprecation warnings

### Phase 7: Documentation (Fast)
**Actions:**
- `summary_report` - Document changes made
- `recommendations` - Suggest preventive measures

**Outcome:** Complete debugging record

## Key Patterns for Neural Training

1. **iterative_fix_approach** - Fix one issue, discover next, repeat
2. **validation_after_each_change** - Run tests after every modification
3. **trace_warning_to_source** - Use Python's warning system for discovery
4. **grep_for_pattern_scope** - Understand blast radius before fixing
5. **test_driven_verification** - Trust tests as source of truth

## Tools Used
- pytest (test execution)
- grep (pattern search)
- python_warnings (deprecation discovery)
- file_edit (code modification)

## Training Metrics
- **Files Modified:** 7
- **Tests Validated:** 2,796
- **Iterations Required:** 2 (initial fix + secondary fix)
- **Total Phases:** 7
- **Success:** Yes

## Application Context
- **Framework:** Pydantic V2 → V3 migration
- **Codebase:** ACGS-2 Enhanced Agent Bus
- **Services Affected:** metering, policy_registry
