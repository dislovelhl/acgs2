#!/bin/bash
# Batch fix all Python files by removing duplicated boilerplate and fixing broken syntax

fix_python_file() {
    local file="$1"
    echo "Processing $file..."
    
    # Remove duplicate FastAPI boilerplate at the beginning
    sed -i '/^# FastAPI Integration - Constitutional Hash:/,/^logger = logging.getLogger(__name__)$/d' "$file"
    
    # Fix broken multi-line imports
    sed -i 's/from \([^,]*\), from \(.*\)/from \1\nfrom \2/g' "$file"
    sed -i 's/import \([^,]*\), from \(.*\)/import \1\nfrom \2/g' "$file"
    sed -i 's/import \([^,]*\), import \(.*\)/import \1\nimport \2/g' "$file"
    sed -i 's/import \([^,]*\), #/import \1\n#/g' "$file"
    
    # Fix broken docstrings
    sed -i '/^"""$/,/^[A-Z]/ {
        /^"""$/a\
"""
        /^[A-Z]/s/^/"""\n/
    }' "$file"
    
    # Remove orphaned Pydantic class definitions
    sed -i '/^# Pydantic Models for Constitutional Compliance$/,/^tus="success"$/d' "$file"
    
    # Fix unterminated docstrings ("""text" -> """text""")
    sed -i 's/"""[^"]*"$/&""/g' "$file"
    
    # Remove stray try-except blocks
    sed -i '/^        except requests.RequestException/,/^            raise$/d' "$file"
    sed -i '/^        except Exception/,/^            raise$/d' "$file"
    
    echo "  ✓ Fixed $file"
}

# Fix all Python files
cd /home/dislove/acgs2/services/core/code-analysis

for file in \
    code_analysis_service/app/api/v1/router.py \
    code_analysis_service/app/core/file_watcher.py \
    code_analysis_service/app/core/indexer.py \
    code_analysis_service/app/middleware/performance.py \
    code_analysis_service/app/services/cache_service.py \
    code_analysis_service/app/services/registry_service.py \
    code_analysis_service/app/utils/logging.py \
    code_analysis_service/config/database.py \
    code_analysis_service/config/settings.py \
    code_analysis_service/deployment_readiness_validation.py \
    code_analysis_service/main_simple.py \
    deploy_staging.py \
    phase4_service_integration_examples.py \
    phase5_production_monitoring_setup.py; do
    if [ -f "$file" ]; then
        fix_python_file "$file"
    fi
done

echo ""
echo "✓ Batch fixing completed"
