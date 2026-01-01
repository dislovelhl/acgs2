# Scripts Directory

This directory contains utility scripts and automation tools for the ACGS-2 project.

## Categories

### Development & Testing Scripts
- `test_all.py` - Comprehensive test runner for the entire project
- `performance_monitor.py` - Real-time performance monitoring and profiling
- `fix_coverage_reporting.py` - Coverage reporting fixes and utilities

### Code Quality Scripts
- `import_health_check.py` - Import dependency analysis and health checks
- `import_optimizer.py` - Automated import optimization and cleanup
- `import_refactor.py` - Import refactoring utilities
- `import_simplifier.py` - Import simplification tools

### Documentation Scripts
- `docs_enhancement_tool.py` - Documentation enhancement and generation tools
- `coordination_plan.py` - Project coordination and planning utilities

### Print Statement Cleanup Scripts
- `fix_print_statements.py` - Remove debug print statements (main)
- `fix_print_statements_qual_001.py` - Quality assurance version 1
- `fix_print_statements_qual_001_v2.py` - Quality assurance version 2

### System Scripts
- `start-kilocode-nvidia.sh` - Startup script for KiloCode NVIDIA environment

## Usage

Most scripts can be run directly with Python:

```bash
python scripts/script_name.py [arguments]
```

For shell scripts:
```bash
./scripts/script_name.sh [arguments]
```

## Constitutional Compliance

**Constitutional Hash**: `cdd01ef066bc6cf2`

All scripts in this directory are designed to maintain constitutional compliance and follow established governance patterns.

## Maintenance

- Scripts should include proper error handling and logging
- Add new scripts to the appropriate category above
- Update this README when adding new scripts
- Ensure scripts follow the project's coding standards
