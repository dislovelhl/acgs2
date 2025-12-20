# Known Issues - Code Analysis Service

## Syntax Errors in Python Files

The following files contain syntax errors from a prior automated code modification that corrupted docstrings:

1. `deploy_staging.py`
2. `code_analysis_service/deployment_readiness_validation.py`
3. `code_analysis_service/main_simple.py`
4. `code_analysis_service/config/database.py`
5. `code_analysis_service/app/services/registry_service.py`
6. `code_analysis_service/app/services/cache_service.py` (FIXED)
7. `code_analysis_service/app/middleware/performance.py`

### Root Cause
An automated tool incorrectly split docstrings, placing `Args:` and `Returns:` sections outside of triple-quoted strings.

### Impact
- **LOW**: This service is not imported by any other component in the ACGS-2 project
- The core `enhanced_agent_bus` package and all 564 tests pass correctly
- These files are for a standalone code analysis microservice that is not yet integrated

### Fix Options
1. Run `python3 fix_all_syntax_errors.py` for partial fixes
2. Manually repair docstrings by adding closing `"""` after Args/Returns sections
3. Restore from a clean version if available

### Example Fix Pattern
```python
# BROKEN:
def method(self):
    """Short description."""
    Args:
        param: description

    self.do_something()

# FIXED:
def method(self):
    """Short description.

    Args:
        param: description
    """
    self.do_something()
```
