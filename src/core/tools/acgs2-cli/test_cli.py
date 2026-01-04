#!/usr/bin/env python3
"""
ACGS-2 CLI Tool Test Script
Constitutional Hash: cdd01ef066bc6cf2

SECURITY: Uses shell=False for subprocess calls to prevent command injection.
"""

import subprocess
import sys


def run_command(cmd_args: list, description: str) -> bool:
    """Run a command and return success status.

    SECURITY: Uses shell=False to prevent command injection attacks.
    Args must be passed as a list of strings.
    """
    logger.info(f"🧪 Testing: {description}")
    try:
        # SECURITY: shell=False prevents command injection
        result = subprocess.run(cmd_args, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
    logger.info(f"✅ {description}: PASSED")
            return True
        else:
    logger.info(f"❌ {description}: FAILED")
    logger.info(f"   Error: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
    logger.info(f"❌ {description}: TIMEOUT")
        return False
    except FileNotFoundError:
    logger.info(f"❌ {description}: COMMAND NOT FOUND")
        return False
    except Exception as e:
    logger.info(f"❌ {description}: ERROR - {e}")
        return False


def main():
    """Test the ACGS-2 CLI tool"""

    logger.info("🧪 ACGS-2 CLI Tool Test Suite")
    logger.info("Constitutional Hash: cdd01ef066bc6cf2")
    logger.info("=" * 50)

    tests_passed = 0
    total_tests = 0

    # Test 1: CLI help
    total_tests += 1
    if run_command(["acgs2-cli", "--help"], "CLI help command"):
        tests_passed += 1

    # Test 2: CLI version
    total_tests += 1
    if run_command(["acgs2-cli", "version"], "CLI version command"):
        tests_passed += 1

    # Test 3: CLI health check (will fail without running services, but should show proper error)
    total_tests += 1
    # SECURITY: shell=False to prevent command injection
    result = subprocess.run(["acgs2-cli", "health"], capture_output=True, text=True, timeout=10)
    if "Health check failed" in result.stderr or "Connection refused" in result.stderr:
    logger.info("✅ CLI health check: PASSED (expected failure without services)")
        tests_passed += 1
    else:
    logger.info("❓ CLI health check: UNEXPECTED RESULT")
    logger.info(f"   stdout: {result.stdout.strip()}")
    logger.info(f"   stderr: {result.stderr.strip()}")

    # Test 4: HITL commands help
    total_tests += 1
    if run_command(["acgs2-cli", "hitl", "--help"], "HITL commands help"):
        tests_passed += 1

    # Test 5: ML commands help
    total_tests += 1
    if run_command(["acgs2-cli", "ml", "--help"], "ML commands help"):
        tests_passed += 1

    # Test 6: Policy commands help
    total_tests += 1
    if run_command(["acgs2-cli", "policy", "--help"], "Policy commands help"):
        tests_passed += 1

    # Test 7: Playground help
    total_tests += 1
    if run_command(["acgs2-cli", "playground", "--help"], "Playground command help"):
        tests_passed += 1

    # Summary
    logger.info("\n" + "=" * 50)
    logger.info(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")

    if tests_passed == total_tests:
    logger.info("🎉 All tests passed! CLI tool is working correctly.")
        return 0
    else:
    logger.info(f"⚠️  {total_tests - tests_passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
