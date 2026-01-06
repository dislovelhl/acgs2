#!/usr/bin/env python3
"""
Baseline Dataset Generator for Drift Detection
Constitutional Hash: cdd01ef066bc6cf2

Generates reference baseline dataset from existing training data patterns
for use with Evidently AI drift detection. The dataset follows the feature
structure used by AdaptiveGovernanceEngine and ImpactScorer models.

Features generated match the _extract_feature_vector method in adaptive_governance.py:
- message_length: Message content length (int)
- agent_count: Number of active agents (int)
- tenant_complexity: Tenant complexity score (float 0-1)
- temporal_mean: Mean of temporal patterns (float)
- temporal_std: Std of temporal patterns (float)
- semantic_similarity: Semantic content risk score (float 0-1)
- historical_precedence: Number of similar past decisions (int)
- resource_utilization: Expected resource consumption (float 0-1)
- network_isolation: Network/data isolation strength (float 0-1)
- risk_score: Computed risk score (float 0-1)
- confidence_level: Confidence in assessment (float 0-1)
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np

# Optional pandas import
try:
    import pandas as pd

    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None

logger = logging.getLogger(__name__)

# Feature definitions with realistic distributions
FEATURE_DEFINITIONS = {
    "message_length": {
        "distribution": "lognormal",
        "params": {"mean": 6.5, "sigma": 1.0},  # Log-normal: median ~665 chars
        "dtype": "int",
        "min_value": 10,
        "max_value": 50000,
    },
    "agent_count": {
        "distribution": "poisson",
        "params": {"lam": 3.0},  # Most systems have 1-5 agents
        "dtype": "int",
        "min_value": 1,
        "max_value": 20,
    },
    "tenant_complexity": {
        "distribution": "beta",
        "params": {"a": 2.0, "b": 5.0},  # Skewed towards simpler tenants
        "dtype": "float",
        "min_value": 0.0,
        "max_value": 1.0,
    },
    "temporal_mean": {
        "distribution": "normal",
        "params": {"mean": 0.15, "std": 0.05},  # Low baseline temporal risk
        "dtype": "float",
        "min_value": 0.0,
        "max_value": 1.0,
    },
    "temporal_std": {
        "distribution": "exponential",
        "params": {"scale": 0.02},  # Low variance in temporal patterns
        "dtype": "float",
        "min_value": 0.0,
        "max_value": 0.5,
    },
    "semantic_similarity": {
        "distribution": "beta",
        "params": {"a": 3.0, "b": 4.0},  # Centered around 0.3-0.5
        "dtype": "float",
        "min_value": 0.0,
        "max_value": 1.0,
    },
    "historical_precedence": {
        "distribution": "poisson",
        "params": {"lam": 2.0},  # Most have 0-5 precedents
        "dtype": "int",
        "min_value": 0,
        "max_value": 100,
    },
    "resource_utilization": {
        "distribution": "beta",
        "params": {"a": 2.0, "b": 8.0},  # Skewed towards low utilization
        "dtype": "float",
        "min_value": 0.0,
        "max_value": 1.0,
    },
    "network_isolation": {
        "distribution": "beta",
        "params": {"a": 8.0, "b": 2.0},  # Skewed towards high isolation
        "dtype": "float",
        "min_value": 0.0,
        "max_value": 1.0,
    },
    "risk_score": {
        "distribution": "derived",  # Calculated from other features
        "params": {},
        "dtype": "float",
        "min_value": 0.0,
        "max_value": 1.0,
    },
    "confidence_level": {
        "distribution": "beta",
        "params": {"a": 5.0, "b": 2.0},  # Skewed towards higher confidence
        "dtype": "float",
        "min_value": 0.5,
        "max_value": 1.0,
    },
}


def generate_feature_values(
    feature_name: str,
    n_samples: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Generate values for a single feature based on its distribution.

    Args:
        feature_name: Name of the feature to generate
        n_samples: Number of samples to generate
        rng: Numpy random generator for reproducibility

    Returns:
        Array of generated values
    """
    config = FEATURE_DEFINITIONS[feature_name]
    distribution = config["distribution"]
    params = config["params"]
    dtype = config["dtype"]
    min_val = config["min_value"]
    max_val = config["max_value"]

    # Skip derived features (will be calculated later)
    if distribution == "derived":
        return np.zeros(n_samples)

    # Generate based on distribution type
    if distribution == "lognormal":
        values = rng.lognormal(mean=params["mean"], sigma=params["sigma"], size=n_samples)
    elif distribution == "normal":
        values = rng.normal(loc=params["mean"], scale=params["std"], size=n_samples)
    elif distribution == "beta":
        values = rng.beta(a=params["a"], b=params["b"], size=n_samples)
    elif distribution == "poisson":
        values = rng.poisson(lam=params["lam"], size=n_samples)
    elif distribution == "exponential":
        values = rng.exponential(scale=params["scale"], size=n_samples)
    else:
        raise ValueError(f"Unknown distribution: {distribution}")

    # Clip to valid range
    values = np.clip(values, min_val, max_val)

    # Convert to appropriate dtype
    if dtype == "int":
        values = values.astype(int)

    return values


def calculate_risk_score(df: "pd.DataFrame") -> np.ndarray:
    """
    Calculate risk scores based on feature values.

    This matches the rule-based scoring in ImpactScorer._rule_based_risk_score
    to ensure consistency between baseline and production data.

    Args:
        df: DataFrame with feature columns

    Returns:
        Array of risk scores
    """
    scores = np.zeros(len(df))

    # Length-based risk
    scores += np.where(df["message_length"] > 10000, 0.3, 0.0)
    scores += np.where((df["message_length"] > 1000) & (df["message_length"] <= 10000), 0.1, 0.0)

    # Agent count risk
    scores += np.where(df["agent_count"] > 10, 0.2, 0.0)
    scores += np.where((df["agent_count"] > 5) & (df["agent_count"] <= 10), 0.1, 0.0)

    # Tenant complexity contribution
    scores += df["tenant_complexity"].values * 0.2

    # Resource impact contribution
    scores += df["resource_utilization"].values * 0.3

    # Semantic risk contribution
    scores += df["semantic_similarity"].values * 0.2

    # Clip to [0, 1]
    return np.clip(scores, 0.0, 1.0)


def generate_baseline_dataset(
    n_samples: int = 500,
    seed: int = 42,
    include_target: bool = False,
) -> "pd.DataFrame":
    """
    Generate a baseline dataset with realistic governance feature distributions.

    The generated data represents typical production behavior and serves as
    the reference baseline for Evidently drift detection.

    Args:
        n_samples: Number of samples to generate (minimum 100 for valid drift detection)
        seed: Random seed for reproducibility
        include_target: Whether to include a target column for training

    Returns:
        DataFrame with governance feature columns
    """
    if not PANDAS_AVAILABLE:
        raise ImportError("pandas is required for baseline generation")

    if n_samples < 100:
        logger.warning(
            f"Generating {n_samples} samples. Note: Evidently requires minimum 100 samples "
            "for valid drift detection."
        )

    # Initialize random generator with seed for reproducibility
    rng = np.random.default_rng(seed)

    # Generate all features
    data = {}
    for feature_name in FEATURE_DEFINITIONS.keys():
        if FEATURE_DEFINITIONS[feature_name]["distribution"] != "derived":
            data[feature_name] = generate_feature_values(feature_name, n_samples, rng)

    # Create DataFrame
    df = pd.DataFrame(data)

    # Calculate derived features
    df["risk_score"] = calculate_risk_score(df)

    # Add some noise to risk scores for realism
    noise = rng.normal(0, 0.02, n_samples)
    df["risk_score"] = np.clip(df["risk_score"] + noise, 0.0, 1.0)

    # Optionally add target column (for supervised learning scenarios)
    if include_target:
        # Target: action_allowed based on risk threshold
        threshold = 0.5 + rng.normal(0, 0.1, n_samples)  # Varying thresholds
        df["target"] = (df["risk_score"] <= threshold).astype(int)

    # Add timestamp column for time-series analysis
    df["timestamp"] = pd.date_range(
        start="2024-01-01",
        periods=n_samples,
        freq="h",
    )

    logger.info(
        f"Generated baseline dataset: {n_samples} samples, "
        f"{len(df.columns) - 1} features (excluding timestamp)"
    )

    return df


def save_baseline_dataset(
    output_path: Optional[str] = None,
    n_samples: int = 500,
    seed: int = 42,
    format: str = "parquet",
) -> Path:
    """
    Generate and save the baseline dataset to a file.

    Args:
        output_path: Output file path (default: data/reference/training_baseline.parquet)
        n_samples: Number of samples to generate
        seed: Random seed for reproducibility
        format: Output format ('parquet' or 'csv')

    Returns:
        Path to the saved file
    """
    if not PANDAS_AVAILABLE:
        raise ImportError("pandas is required for saving baseline dataset")

    # Default output path
    if output_path is None:
        script_dir = Path(__file__).parent
        output_path = script_dir / "reference" / "training_baseline.parquet"
    else:
        output_path = Path(output_path)

    # Ensure directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate dataset
    df = generate_baseline_dataset(n_samples=n_samples, seed=seed)

    # Save in specified format
    if format == "parquet":
        df.to_parquet(output_path, index=False)
    elif format == "csv":
        df.to_csv(output_path, index=False)
    else:
        raise ValueError(f"Unsupported format: {format}")

    logger.info(f"Saved baseline dataset to: {output_path}")

    return output_path


def main():
    """Command-line entry point for baseline generation."""
    import argparse

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Generate reference baseline dataset for drift detection",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file path (default: data/reference/training_baseline.parquet)",
    )
    parser.add_argument(
        "--samples",
        "-n",
        type=int,
        default=500,
        help="Number of samples to generate (default: 500)",
    )
    parser.add_argument(
        "--seed",
        "-s",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--format",
        "-f",
        type=str,
        choices=["parquet", "csv"],
        default="parquet",
        help="Output format (default: parquet)",
    )

    args = parser.parse_args()

    try:
        output_path = save_baseline_dataset(
            output_path=args.output,
            n_samples=args.samples,
            seed=args.seed,
            format=args.format,
        )
        logger.info(f"Successfully generated baseline dataset: {output_path}")

    except Exception as e:
        logger.error(f"Failed to generate baseline: {e}")
        raise


if __name__ == "__main__":
    main()
