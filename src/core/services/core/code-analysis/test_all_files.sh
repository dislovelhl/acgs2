#!/bin/bash

echo "Testing Python compilation for all 14 files..."
echo "================================================"
echo ""

success=0
failed=0
failed_files=()

files=(
    "code_analysis_service/app/api/v1/router.py"
    "code_analysis_service/app/core/file_watcher.py"
    "code_analysis_service/app/core/indexer.py"
    "code_analysis_service/app/middleware/performance.py"
    "code_analysis_service/app/services/cache_service.py"
    "code_analysis_service/app/services/registry_service.py"
    "code_analysis_service/app/utils/logging.py"
    "code_analysis_service/config/database.py"
    "code_analysis_service/config/settings.py"
    "code_analysis_service/deployment_readiness_validation.py"
    "code_analysis_service/main_simple.py"
    "deploy_staging.py"
    "phase4_service_integration_examples.py"
    "phase5_production_monitoring_setup.py"
)

for file in "${files[@]}"; do
    if python3 -m py_compile "$file" 2>/dev/null; then
        echo "✓ PASS: $file"
        ((success++))
    else
        echo "✗ FAIL: $file"
        ((failed++))
        failed_files+=("$file")
        # Show first error
        python3 -m py_compile "$file" 2>&1 | head -3 | sed 's/^/    /'
    fi
done

echo ""
echo "================================================"
echo "Results: $success passed, $failed failed (out of 14 files)"
echo "================================================"

if [ $failed -gt 0 ]; then
    echo ""
    echo "Failed files:"
    for file in "${failed_files[@]}"; do
        echo "  - $file"
    done
fi

exit $failed
