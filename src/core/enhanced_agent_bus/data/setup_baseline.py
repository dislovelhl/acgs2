#!/usr/bin/env python3
"""
Setup Baseline Dataset for Drift Detection
Constitutional Hash: cdd01ef066bc6cf2

This script converts the CSV baseline dataset to parquet format for optimal
performance with Evidently AI drift detection. Run this script once during
environment setup or CI/CD pipeline initialization.

Usage:
    python data/setup_baseline.py

The script will:
1. Read the CSV baseline from data/reference/training_baseline.csv
2. Convert to parquet format at data/reference/training_baseline.parquet
3. Validate the resulting dataset has 100+ samples
"""

import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def setup_baseline():
    """Convert CSV baseline to parquet format."""
    try:
        import pandas as pd
    except ImportError:
        logger.error("pandas is required. Install with: pip install pandas pyarrow")
        sys.exit(1)

    try:
        import pyarrow  # noqa: F401 - Required for parquet support
    except ImportError:
        logger.error("pyarrow is required for parquet support. Install with: pip install pyarrow")
        sys.exit(1)

    # Define paths
    script_dir = Path(__file__).parent
    csv_path = script_dir / "reference" / "training_baseline.csv"
    parquet_path = script_dir / "reference" / "training_baseline.parquet"

    # Check CSV exists
    if not csv_path.exists():
        logger.error(f"CSV baseline not found at: {csv_path}")
        logger.info("Run 'python data/generate_baseline.py' first to create the baseline")
        sys.exit(1)

    # Read CSV
    logger.info(f"Reading CSV baseline from: {csv_path}")
    df = pd.read_csv(csv_path)

    # Validate sample count
    sample_count = len(df)
    if sample_count < 100:
        logger.warning(
            f"Baseline has {sample_count} samples. "
            "Evidently requires minimum 100 samples for valid drift detection."
        )

    # Convert timestamp column if present
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Save as parquet
    logger.info(f"Writing parquet baseline to: {parquet_path}")
    df.to_parquet(parquet_path, index=False)

    # Validate output
    df_check = pd.read_parquet(parquet_path)
    logger.info(
        f"Successfully created parquet baseline: "
        f"{len(df_check)} samples, {len(df_check.columns)} columns"
    )

    # Print column info
    logger.info(f"Feature columns: {list(df_check.columns)}")

    return parquet_path


def validate_baseline(path: Path = None):
    """Validate the baseline dataset meets requirements."""
    try:
        import pandas as pd
    except ImportError:
        logger.error("pandas required for validation")
        return False

    if path is None:
        script_dir = Path(__file__).parent
        path = script_dir / "reference" / "training_baseline.parquet"

    if not path.exists():
        logger.error(f"Baseline not found at: {path}")
        return False

    df = pd.read_parquet(path)

    # Check sample count
    if len(df) < 100:
        logger.error(f"Insufficient samples: {len(df)} < 100")
        return False

    # Check required columns
    required_columns = [
        "message_length",
        "agent_count",
        "tenant_complexity",
        "temporal_mean",
        "temporal_std",
        "semantic_similarity",
        "historical_precedence",
        "resource_utilization",
        "network_isolation",
        "risk_score",
        "confidence_level",
    ]

    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        logger.error(f"Missing required columns: {missing}")
        return False

    logger.info(f"Baseline validation passed: {len(df)} samples, all columns present")
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Setup baseline dataset for drift detection")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate existing baseline, don't convert",
    )
    args = parser.parse_args()

    if args.validate_only:
        success = validate_baseline()
        sys.exit(0 if success else 1)
    else:
        setup_baseline()
        success = validate_baseline()
        sys.exit(0 if success else 1)
