#!/usr/bin/env python3
import os
import subprocess


def get_governance_diffs():
    # Only diff files in policies directory
    try:
        base_ref = os.environ.get("GITHUB_BASE_REF", "develop")
        diff_output = subprocess.check_output(
            ["git", "diff", f"origin/{base_ref}...HEAD", "--", "acgs2-core/policies/"]
        ).decode("utf-8")

        if not diff_output:
            print("No governance changes detected.")
            return

        print("### ⚖️ Governance Policy Diffs")
        print("```diff")
        print(diff_output)
        print("```")

        # Simple risk assessment (heuristic)
        risk = "LOW"
        if "regulators" in diff_output or "threshold" in diff_output or "quorum" in diff_output:
            risk = "MEDIUM"
        if "admin" in diff_output or "sudo" in diff_output or "override" in diff_output:
            risk = "HIGH"

        print(f"\n**Estimated Risk Level**: {risk}")

    except Exception as e:
        print(f"Error generating diffs: {e}")


if __name__ == "__main__":
    get_governance_diffs()
