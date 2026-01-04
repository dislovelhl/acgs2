#!/usr/bin/env python3
"""
ACGS-2 Secrets Rotation Checker
Constitutional Hash: cdd01ef066bc6cf2

Run periodically or as a CI check to verify secrets rotation compliance.

Usage:
    python scripts/check-secrets-rotation.py [--warn-days 30] [--fail-on-expired]
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "acgs2-core"))

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


def check_rotation_status(warn_days: int = 30, fail_on_expired: bool = False) -> int:
    """
    Check secrets rotation status.

    Args:
        warn_days: Days before expiry to warn
        fail_on_expired: Exit with error if any secrets expired

    Returns:
        Exit code (0 = ok, 1 = warnings, 2 = expired)
    """
    print(f"🔐 ACGS-2 Secrets Rotation Check")
    print(f"   Constitutional Hash: {CONSTITUTIONAL_HASH}")
    print(f"   Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print()

    # Try to use SecretsManager
    try:
        from src.core.shared.secrets_manager import get_secrets_manager

        manager = get_secrets_manager()
        report = manager.rotation_report()

        expired = report["needs_rotation"]
        ok = report["ok"]

        if expired:
            print("❌ SECRETS NEEDING ROTATION:")
            for secret in expired:
                print(
                    f"   - {secret['name']} (category: {secret['category']}, "
                    f"age: {secret['age_days']} days, limit: {secret['rotation_days']} days)"
                )
            print()

        # Check for upcoming expirations
        warnings = []
        for secret in ok:
            days_left = secret["rotation_days"] - secret["age_days"]
            if days_left <= warn_days:
                warnings.append(
                    f"   - {secret['name']} expires in {days_left} days"
                )

        if warnings:
            print("⚠️  SECRETS EXPIRING SOON:")
            for warning in warnings:
                print(warning)
            print()

        if ok and not expired and not warnings:
            print("✅ All secrets are within rotation limits")

        # Determine exit code
        if expired and fail_on_expired:
            return 2
        elif expired or warnings:
            return 1
        return 0

    except ImportError:
        # Fallback: check metadata file directly
        print("⚠️  SecretsManager not available, checking metadata file...")

        metadata_path = Path.home() / ".acgs2" / "secrets.meta.json"
        if not metadata_path.exists():
            print("   No secrets metadata found. Run setup-secrets.sh first.")
            return 0

        try:
            metadata = json.loads(metadata_path.read_text())
            now = datetime.now(timezone.utc)
            expired = []
            warnings = []

            for name, meta in metadata.items():
                created = datetime.fromisoformat(meta["created_at"])
                rotated = (
                    datetime.fromisoformat(meta["last_rotated"])
                    if meta.get("last_rotated")
                    else created
                )
                rotation_days = meta.get("rotation_days", 90)
                age = (now - rotated).days

                if age > rotation_days:
                    expired.append(f"   - {name} (age: {age} days, limit: {rotation_days})")
                elif age > rotation_days - warn_days:
                    days_left = rotation_days - age
                    warnings.append(f"   - {name} expires in {days_left} days")

            if expired:
                print("❌ SECRETS NEEDING ROTATION:")
                for exp in expired:
                    print(exp)
                print()

            if warnings:
                print("⚠️  SECRETS EXPIRING SOON:")
                for warn in warnings:
                    print(warn)
                print()

            if not expired and not warnings:
                print("✅ All secrets are within rotation limits")

            if expired and fail_on_expired:
                return 2
            elif expired or warnings:
                return 1
            return 0

        except Exception as e:
            print(f"❌ Error reading metadata: {e}")
            return 1


def main():
    parser = argparse.ArgumentParser(
        description="Check ACGS-2 secrets rotation status"
    )
    parser.add_argument(
        "--warn-days",
        type=int,
        default=30,
        help="Days before expiry to show warning (default: 30)",
    )
    parser.add_argument(
        "--fail-on-expired",
        action="store_true",
        help="Exit with error code 2 if any secrets are expired",
    )
    args = parser.parse_args()

    sys.exit(check_rotation_status(args.warn_days, args.fail_on_expired))


if __name__ == "__main__":
    main()
