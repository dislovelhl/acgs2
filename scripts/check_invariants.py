#!/usr/bin/env python3
import sys


def assert_invariants():
    # In a real system, these would pull from live state or configuration
    invariants = [
        {"name": "MIN_QUORUM", "current": 0.15, "min": 0.10, "desc": "Quorum must be at least 10%"},
        {
            "name": "MAX_VOTING_WEIGHT",
            "current": 0.30,
            "max": 0.40,
            "desc": "No single agent should hold >40% power",
        },
        {
            "name": "MIN_VOTING_PERIOD",
            "current": 172800,
            "min": 86400,
            "desc": "Voting must last at least 24h",
        },
    ]

    failed = False
    print("📋 Checking Governance Invariants...")
    for inv in invariants:
        status = "✅ PASS"
        if "min" in inv and inv["current"] < inv["min"]:
            status = "❌ FAIL"
            failed = True
        if "max" in inv and inv["current"] > inv["max"]:
            status = "❌ FAIL"
            failed = True

        print(f"{status} | {inv['name']}: {inv['current']} ({inv['desc']})")

    if failed:
        print("\n❌ One or more invariants failed!")
        return 1

    print("\n✅ All invariants satisfied.")
    return 0


if __name__ == "__main__":
    sys.exit(assert_invariants())
