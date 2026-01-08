#!/usr/bin/env python3
import os
import subprocess
import sys


def get_changed_files():
    try:
        # Get base branch (usually develop or main)
        base_ref = os.environ.get("GITHUB_BASE_REF", "develop")
        output = subprocess.check_output(
            ["git", "diff", "--name-only", f"origin/{base_ref}...HEAD"]
        ).decode("utf-8")
        return output.splitlines()
    except Exception:
        return []


def check_policy_gates():
    changed_files = get_changed_files()

    policy_changed = any(f.startswith("src/core/policies/") for f in changed_files)
    changelog_updated = "docs/GOVERNANCE_CHANGELOG.md" in changed_files

    if policy_changed and not changelog_updated:
        print("❌ ERROR: Policy files changed but docs/GOVERNANCE_CHANGELOG.md was not updated.")
        return 1

    print("✅ Policy gates passed.")
    return 0


if __name__ == "__main__":
    sys.exit(check_policy_gates())
