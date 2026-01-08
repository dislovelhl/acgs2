# ACGS-2 Large File Refactoring Plan

Generated for 480 oversized files

## 1. src/integration-service/integration-service/tests/integrations/test_pagerduty.py

- **Lines:** 2919
- **Classes:** 11
- **Functions:** 80
- **Imports:** 23

### Suggestions

- Split into multiple modules (one per class)
- Extract utility functions into separate module
- Break up large test file into multiple test modules

## 2. src/adaptive-learning/adaptive-learning-engine/src/safety/bounds_checker.py

- **Lines:** 2315
- **Classes:** 6
- **Functions:** 29
- **Imports:** 6

### Suggestions

- Split into multiple modules (one per class)
- Extract utility functions into separate module

## 3. src/core/enhanced_agent_bus/tests/test_agent_bus.py

- **Lines:** 2309
- **Classes:** 54
- **Functions:** 62
- **Imports:** 25

### Suggestions

- Split into multiple modules (one per class)
- Extract utility functions into separate module
- Break up large test file into multiple test modules

## 4. src/adaptive-learning/adaptive-learning-engine/tests/unit/test_monitoring.py

- **Lines:** 2243
- **Classes:** 29
- **Functions:** 137
- **Imports:** 10

### Suggestions

- Split into multiple modules (one per class)
- Extract utility functions into separate module
- Break up large test file into multiple test modules

## 5. src/core/services/hitl-approvals/app/core/escalation.py

- **Lines:** 2113
- **Classes:** 12
- **Functions:** 53
- **Imports:** 12

### Suggestions

- Split into multiple modules (one per class)
- Extract utility functions into separate module
- Extract business logic into separate service classes

## 6. src/adaptive-learning/adaptive-learning-engine/src/monitoring/drift_detector.py

- **Lines:** 2029
- **Classes:** 5
- **Functions:** 27
- **Imports:** 14

### Suggestions

- Extract utility functions into separate module

## 7. src/integration-service/integration-service/src/integrations/pagerduty_adapter.py

- **Lines:** 1957
- **Classes:** 3
- **Functions:** 11
- **Imports:** 17

### Suggestions

- Extract business logic into separate service classes

## 8. src/core/enhanced_agent_bus/tests/test_agent_bus_security.py

- **Lines:** 1757
- **Classes:** 42
- **Functions:** 49
- **Imports:** 25

### Suggestions

- Split into multiple modules (one per class)
- Extract utility functions into separate module
- Break up large test file into multiple test modules

## 9. src/adaptive-learning/adaptive-learning-engine/src/models/online_learner.py

- **Lines:** 1709
- **Classes:** 6
- **Functions:** 22
- **Imports:** 9

### Suggestions

- Split into multiple modules (one per class)
- Extract utility functions into separate module

## 10. src/core/enhanced_agent_bus/tests/test_coverage_boost.py

- **Lines:** 1685
- **Classes:** 14
- **Functions:** 7
- **Imports:** 121

### Suggestions

- Split into multiple modules (one per class)
- Consider module reorganization to reduce import complexity
- Break up large test file into multiple test modules
