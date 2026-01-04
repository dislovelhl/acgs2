# ACGS-2 Codebase Consolidation Report

**Generated**: Sat 03 Jan 2026 04:24:56 AM EST
**Analysis Target**: 52k+ Python files

## Duplicate Functions

Found 22 opportunities:

### Function 'to_dict' appears in 47 files with similar implementations
- **Risk Level**: medium
- **Estimated Savings**: 470 lines
- **Files**: 47 affected
- **Recommendation**: Consider extracting 'to_dict' to a shared utility module

### Function '__init__' appears in 178 files with similar implementations
- **Risk Level**: medium
- **Estimated Savings**: 1780 lines
- **Files**: 178 affected
- **Recommendation**: Consider extracting '__init__' to a shared utility module

### Function 'get_metrics' appears in 13 files with similar implementations
- **Risk Level**: medium
- **Estimated Savings**: 130 lines
- **Files**: 13 affected
- **Recommendation**: Consider extracting 'get_metrics' to a shared utility module

### Function '__post_init__' appears in 9 files with similar implementations
- **Risk Level**: medium
- **Estimated Savings**: 90 lines
- **Files**: 9 affected
- **Recommendation**: Consider extracting '__post_init__' to a shared utility module

### Function 'validate' appears in 5 files with similar implementations
- **Risk Level**: medium
- **Estimated Savings**: 50 lines
- **Files**: 5 affected
- **Recommendation**: Consider extracting 'validate' to a shared utility module

### Function 'from_dict' appears in 3 files with similar implementations
- **Risk Level**: medium
- **Estimated Savings**: 30 lines
- **Files**: 3 affected
- **Recommendation**: Consider extracting 'from_dict' to a shared utility module

### Function 'get_stats' appears in 2 files with similar implementations
- **Risk Level**: medium
- **Estimated Savings**: 20 lines
- **Files**: 2 affected
- **Recommendation**: Consider extracting 'get_stats' to a shared utility module

### Function 'decorator' appears in 6 files with similar implementations
- **Risk Level**: medium
- **Estimated Savings**: 60 lines
- **Files**: 6 affected
- **Recommendation**: Consider extracting 'decorator' to a shared utility module

### Function 'main' appears in 4 files with similar implementations
- **Risk Level**: medium
- **Estimated Savings**: 40 lines
- **Files**: 4 affected
- **Recommendation**: Consider extracting 'main' to a shared utility module

### Function 'decode' appears in 2 files with similar implementations
- **Risk Level**: medium
- **Estimated Savings**: 20 lines
- **Files**: 2 affected
- **Recommendation**: Consider extracting 'decode' to a shared utility module

## Similar Classes

Found 15 opportunities:

### Class 'GovernanceMetrics' defined in 3 files
- **Risk Level**: high
- **Estimated Savings**: 45 lines
- **Files**: 3 affected
- **Recommendation**: Review 'GovernanceMetrics' implementations for consolidation or inheritance

### Class 'GovernanceDecision' defined in 3 files
- **Risk Level**: high
- **Estimated Savings**: 45 lines
- **Files**: 3 affected
- **Recommendation**: Review 'GovernanceDecision' implementations for consolidation or inheritance

### Class 'ValidationResult' defined in 7 files
- **Risk Level**: high
- **Estimated Savings**: 105 lines
- **Files**: 7 affected
- **Recommendation**: Review 'ValidationResult' implementations for consolidation or inheritance

### Class 'SearchPlatformSettings' defined in 3 files
- **Risk Level**: high
- **Estimated Savings**: 45 lines
- **Files**: 3 affected
- **Recommendation**: Review 'SearchPlatformSettings' implementations for consolidation or inheritance

### Class 'Settings' defined in 4 files
- **Risk Level**: high
- **Estimated Savings**: 60 lines
- **Files**: 4 affected
- **Recommendation**: Review 'Settings' implementations for consolidation or inheritance

### Class 'AccessDeniedError' defined in 3 files
- **Risk Level**: high
- **Estimated Savings**: 45 lines
- **Files**: 3 affected
- **Recommendation**: Review 'AccessDeniedError' implementations for consolidation or inheritance

### Class 'ApprovalStatus' defined in 3 files
- **Risk Level**: high
- **Estimated Savings**: 45 lines
- **Files**: 3 affected
- **Recommendation**: Review 'ApprovalStatus' implementations for consolidation or inheritance

### Class 'ApprovalRequest' defined in 3 files
- **Risk Level**: high
- **Estimated Savings**: 45 lines
- **Files**: 3 affected
- **Recommendation**: Review 'ApprovalRequest' implementations for consolidation or inheritance

### Class 'Config' defined in 17 files
- **Risk Level**: high
- **Estimated Savings**: 255 lines
- **Files**: 17 affected
- **Recommendation**: Review 'Config' implementations for consolidation or inheritance

### Class 'ApprovalDecision' defined in 3 files
- **Risk Level**: high
- **Estimated Savings**: 45 lines
- **Files**: 3 affected
- **Recommendation**: Review 'ApprovalDecision' implementations for consolidation or inheritance

## Redundant Utilities

Found 5 opportunities:

### Pattern 'def (get_|set_|create_|delete_|update_)' appears 7 times in 9 files
- **Risk Level**: medium
- **Estimated Savings**: 56 lines
- **Files**: 5 affected
- **Recommendation**: Consider extracting common (get_|set_|ceate_|delete_|update_) utilities to shared modules

### Pattern 'def (get_|set_|create_|delete_|update_)' appears 6 times in 15 files
- **Risk Level**: medium
- **Estimated Savings**: 48 lines
- **Files**: 5 affected
- **Recommendation**: Consider extracting common (get_|set_|ceate_|delete_|update_) utilities to shared modules

### Pattern 'def (get_|set_|create_|delete_|update_)' appears 11 times in 2 files
- **Risk Level**: medium
- **Estimated Savings**: 88 lines
- **Files**: 2 affected
- **Recommendation**: Consider extracting common (get_|set_|ceate_|delete_|update_) utilities to shared modules

### Pattern 'def (get_|set_|create_|delete_|update_)' appears 13 times in 2 files
- **Risk Level**: medium
- **Estimated Savings**: 104 lines
- **Files**: 2 affected
- **Recommendation**: Consider extracting common (get_|set_|ceate_|delete_|update_) utilities to shared modules

### Pattern 'def (get_|set_|create_|delete_|update_)' appears 8 times in 3 files
- **Risk Level**: medium
- **Estimated Savings**: 64 lines
- **Files**: 3 affected
- **Recommendation**: Consider extracting common (get_|set_|ceate_|delete_|update_) utilities to shared modules

## Import Consolidation

Found 52 opportunities:

### File has 26 imports - consider consolidation
- **Risk Level**: low
- **Estimated Savings**: 13 lines
- **Files**: 1 affected
- **Recommendation**: Consider using 'from module import *' or consolidating imports

### File has 29 imports - consider consolidation
- **Risk Level**: low
- **Estimated Savings**: 14 lines
- **Files**: 1 affected
- **Recommendation**: Consider using 'from module import *' or consolidating imports

### File has 85 imports - consider consolidation
- **Risk Level**: low
- **Estimated Savings**: 42 lines
- **Files**: 1 affected
- **Recommendation**: Consider using 'from module import *' or consolidating imports

### File has 66 imports - consider consolidation
- **Risk Level**: low
- **Estimated Savings**: 33 lines
- **Files**: 1 affected
- **Recommendation**: Consider using 'from module import *' or consolidating imports

### File has 27 imports - consider consolidation
- **Risk Level**: low
- **Estimated Savings**: 13 lines
- **Files**: 1 affected
- **Recommendation**: Consider using 'from module import *' or consolidating imports

### File has 56 imports - consider consolidation
- **Risk Level**: low
- **Estimated Savings**: 28 lines
- **Files**: 1 affected
- **Recommendation**: Consider using 'from module import *' or consolidating imports

### File has 24 imports - consider consolidation
- **Risk Level**: low
- **Estimated Savings**: 12 lines
- **Files**: 1 affected
- **Recommendation**: Consider using 'from module import *' or consolidating imports

### File has 43 imports - consider consolidation
- **Risk Level**: low
- **Estimated Savings**: 21 lines
- **Files**: 1 affected
- **Recommendation**: Consider using 'from module import *' or consolidating imports

### File has 58 imports - consider consolidation
- **Risk Level**: low
- **Estimated Savings**: 29 lines
- **Files**: 1 affected
- **Recommendation**: Consider using 'from module import *' or consolidating imports

### File has 53 imports - consider consolidation
- **Risk Level**: low
- **Estimated Savings**: 26 lines
- **Files**: 1 affected
- **Recommendation**: Consider using 'from module import *' or consolidating imports

## Archival Candidates

Found 63 opportunities:

### Candidate for archival: very small file, no functions or classes defined
- **Risk Level**: low
- **Estimated Savings**: 13 lines
- **Files**: 1 affected
- **Recommendation**: Review for archival or consolidation

### Candidate for archival: no functions or classes defined
- **Risk Level**: low
- **Estimated Savings**: 123 lines
- **Files**: 1 affected
- **Recommendation**: Review for archival or consolidation

### Candidate for archival: very small file, no functions or classes defined
- **Risk Level**: low
- **Estimated Savings**: 2 lines
- **Files**: 1 affected
- **Recommendation**: Review for archival or consolidation

### Candidate for archival: no functions or classes defined
- **Risk Level**: low
- **Estimated Savings**: 190 lines
- **Files**: 1 affected
- **Recommendation**: Review for archival or consolidation

### Candidate for archival: no functions or classes defined
- **Risk Level**: low
- **Estimated Savings**: 231 lines
- **Files**: 1 affected
- **Recommendation**: Review for archival or consolidation

### Candidate for archival: no functions or classes defined
- **Risk Level**: low
- **Estimated Savings**: 62 lines
- **Files**: 1 affected
- **Recommendation**: Review for archival or consolidation

### Candidate for archival: no functions or classes defined
- **Risk Level**: low
- **Estimated Savings**: 51 lines
- **Files**: 1 affected
- **Recommendation**: Review for archival or consolidation

### Candidate for archival: very small file, no functions or classes defined
- **Risk Level**: low
- **Estimated Savings**: 41 lines
- **Files**: 1 affected
- **Recommendation**: Review for archival or consolidation

### Candidate for archival: no functions or classes defined
- **Risk Level**: low
- **Estimated Savings**: 76 lines
- **Files**: 1 affected
- **Recommendation**: Review for archival or consolidation

### Candidate for archival: no functions or classes defined
- **Risk Level**: low
- **Estimated Savings**: 78 lines
- **Files**: 1 affected
- **Recommendation**: Review for archival or consolidation

## Summary

- **Total Opportunities**: 45
,

## Priority Recommendations

1. **Low-risk consolidation first**: Unused imports, archival candidates
2. **Medium-risk**: Duplicate functions, redundant utilities
3. **High-risk**: Similar classes (requires careful review)

### Implementation Strategy

1. Start with automated cleanup (unused imports)
2. Review archival candidates manually
3. Create shared utility modules for common functions
4. Implement gradual consolidation with testing
