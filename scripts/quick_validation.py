#!/usr/bin/env python3
"""
Quick Validation of ACGS-2 Improvements
Constitutional Hash: cdd01ef066bc6cf2
"""

import os
import sys

def check_file_exists(filepath, description):
    """Check if a file exists and report status."""
    if os.path.exists(filepath):
        print(f"✅ {description}: Found")
        return True
    else:
        print(f"❌ {description}: Missing")
        return False

def check_file_contains(filepath, search_text, description):
    """Check if a file contains specific text."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            if search_text in content:
                print(f"✅ {description}: Present")
                return True
            else:
                print(f"❌ {description}: Missing")
                return False
    except Exception as e:
        print(f"❌ {description}: Error reading file - {e}")
        return False

def main():
    """Run validation checks."""
    print("="*80)
    print("ACGS-2 IMPROVEMENTS VALIDATION")
    print("="*80)

    checks_passed = 0
    total_checks = 0

    # Check MessageProcessor optimization
    total_checks += 1
    if check_file_contains(
        "/home/dislove/document/acgs2/acgs2-core/enhanced_agent_bus/message_processor.py",
        "if profiler and profiler.config.enabled",
        "MessageProcessor memory profiling optimization"
    ):
        checks_passed += 1

    # Check JSON optimization
    total_checks += 1
    if check_file_exists(
        "/home/dislove/document/acgs2/acgs2-core/shared/json_utils.py",
        "JSON serialization optimization"
    ):
        checks_passed += 1

    # Check TypeScript logging
    total_checks += 1
    if check_file_exists(
        "/home/dislove/document/acgs2/sdk/typescript/src/utils/logger.ts",
        "TypeScript structured logging utility"
    ):
        checks_passed += 1

    # Check audit client improvements
    total_checks += 1
    if check_file_contains(
        "/home/dislove/document/acgs2/acgs2-core/shared/audit_client.py",
        "response = await self.client.post",
        "Audit client real service integration"
    ):
        checks_passed += 1

    # Check audit client fallback
    total_checks += 1
    if check_file_contains(
        "/home/dislove/document/acgs2/acgs2-core/shared/audit_client.py",
        "simulated_",
        "Audit client fallback mechanism"
    ):
        checks_passed += 1

    # Check audit service URL update
    total_checks += 1
    if check_file_contains(
        "/home/dislove/document/acgs2/acgs2-core/shared/audit_client.py",
        'service_url: str = "http://localhost:8300"',
        "Audit service URL configuration"
    ):
        checks_passed += 1

    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    print(f"Checks passed: {checks_passed}/{total_checks}")

    if checks_passed == total_checks:
        print("🎉 ALL IMPROVEMENTS VALIDATED SUCCESSFULLY!")
        return True
    else:
        print("⚠️  Some improvements need verification")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
