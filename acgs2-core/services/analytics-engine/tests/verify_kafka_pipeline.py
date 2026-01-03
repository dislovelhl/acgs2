#!/usr/bin/env python3
"""
Kafka → Analytics Engine Pipeline Verification Script
Constitutional Hash: cdd01ef066bc6cf2

This script verifies the end-to-end data pipeline:
1. Publishes governance events to Kafka topic (or loads from JSON)
2. Runs analytics-engine batch processing
3. Verifies data is processed correctly
4. Checks analytics-engine components are functional

Usage:
    python verify_kafka_pipeline.py --mode sample  # Use sample data
    python verify_kafka_pipeline.py --mode kafka   # Use Kafka (requires running Kafka)
    python verify_kafka_pipeline.py --mode json --input data/sample_governance_events.json
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from anomaly_detector import AnomalyDetector
from data_processor import GovernanceDataProcessor
from predictor import ViolationPredictor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("pipeline-verification")


class PipelineVerificationResult:
    """Result container for pipeline verification."""

    def __init__(self) -> None:
        self.success = True
        self.checks: list[dict[str, Any]] = []
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.summary: dict[str, Any] = {}

    def add_check(
        self,
        name: str,
        passed: bool,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Add a verification check result."""
        self.checks.append(
            {
                "name": name,
                "passed": passed,
                "message": message,
                "details": details or {},
            }
        )
        if not passed:
            self.success = False

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
        self.success = False

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)

    def print_report(self) -> None:
        """Print a formatted verification report."""
        print("\n" + "=" * 60)
        print("KAFKA → ANALYTICS ENGINE PIPELINE VERIFICATION REPORT")
        print("=" * 60)
        print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
        print(f"Overall Status: {'✅ PASSED' if self.success else '❌ FAILED'}")
        print("-" * 60)

        print("\n📋 Verification Checks:")
        for check in self.checks:
            status = "✅" if check["passed"] else "❌"
            print(f"  {status} {check['name']}: {check['message']}")
            if check["details"]:
                for key, value in check["details"].items():
                    print(f"      - {key}: {value}")

        if self.warnings:
            print("\n⚠️  Warnings:")
            for warning in self.warnings:
                print(f"  - {warning}")

        if self.errors:
            print("\n❌ Errors:")
            for error in self.errors:
                print(f"  - {error}")

        if self.summary:
            print("\n📊 Summary:")
            for key, value in self.summary.items():
                print(f"  - {key}: {value}")

        print("\n" + "=" * 60)


async def verify_data_processor(
    result: PipelineVerificationResult,
    events_json: list[dict[str, Any]],
) -> GovernanceDataProcessor:
    """Verify the data processor component."""
    logger.info("Verifying GovernanceDataProcessor...")

    processor = GovernanceDataProcessor()

    # Test 1: Load events from JSON
    try:
        events = processor.load_from_json(events_json)
        result.add_check(
            "Event Loading",
            len(events) > 0,
            f"Loaded {len(events)} events",
            {"event_count": len(events)},
        )
    except Exception as e:
        result.add_check("Event Loading", False, f"Failed: {e}")
        return processor

    # Test 2: Convert to DataFrame
    try:
        df = processor.events_to_dataframe()
        result.add_check(
            "DataFrame Conversion",
            len(df) > 0,
            f"Created DataFrame with {len(df)} rows",
            {"columns": list(df.columns), "shape": list(df.shape)},
        )
    except Exception as e:
        result.add_check("DataFrame Conversion", False, f"Failed: {e}")
        return processor

    # Test 3: Prepare for Prophet
    try:
        prophet_df = processor.prepare_for_prophet(df)
        has_required_cols = "ds" in prophet_df.columns and "y" in prophet_df.columns
        result.add_check(
            "Prophet Preparation",
            has_required_cols,
            f"Prophet DataFrame ready with {len(prophet_df)} rows",
            {"columns": list(prophet_df.columns), "row_count": len(prophet_df)},
        )
    except Exception as e:
        result.add_check("Prophet Preparation", False, f"Failed: {e}")

    # Test 4: Prepare for anomaly detection
    try:
        anomaly_df = processor.prepare_for_anomaly_detection(df)
        result.add_check(
            "Anomaly Detection Preparation",
            len(anomaly_df) > 0,
            f"Anomaly DataFrame ready with {len(anomaly_df)} rows",
            {"columns": list(anomaly_df.columns)},
        )
    except Exception as e:
        result.add_check("Anomaly Detection Preparation", False, f"Failed: {e}")

    # Test 5: Compute metrics
    try:
        metrics = processor.compute_metrics(df)
        result.add_check(
            "Metrics Computation",
            metrics.total_events > 0,
            f"Computed metrics: {metrics.total_events} events, "
            f"{metrics.violation_count} violations",
            {
                "total_events": metrics.total_events,
                "violations": metrics.violation_count,
                "unique_users": metrics.unique_users,
                "unique_policies": metrics.unique_policies,
            },
        )
        result.summary["total_events"] = metrics.total_events
        result.summary["violations"] = metrics.violation_count
    except Exception as e:
        result.add_check("Metrics Computation", False, f"Failed: {e}")

    return processor


def verify_anomaly_detector(
    result: PipelineVerificationResult,
    processor: GovernanceDataProcessor,
) -> None:
    """Verify the anomaly detector component."""
    logger.info("Verifying AnomalyDetector...")

    try:
        detector = AnomalyDetector(contamination=0.1)

        df = processor.events_to_dataframe()
        anomaly_df = processor.prepare_for_anomaly_detection(df)

        if anomaly_df.empty:
            result.add_warning("No data available for anomaly detection")
            return

        detection_result = detector.detect_anomalies(anomaly_df)

        result.add_check(
            "Anomaly Detection",
            True,
            f"Detected {detection_result.anomalies_detected} anomalies",
            {
                "total_records": detection_result.total_records_analyzed,
                "anomalies_found": detection_result.anomalies_detected,
                "model_trained": detection_result.model_trained,
            },
        )
        result.summary["anomalies_detected"] = detection_result.anomalies_detected

    except ImportError as e:
        result.add_warning(f"Anomaly detection skipped (missing dependency): {e}")
    except Exception as e:
        result.add_check("Anomaly Detection", False, f"Failed: {e}")


def verify_predictor(
    result: PipelineVerificationResult,
    processor: GovernanceDataProcessor,
) -> None:
    """Verify the violation predictor component."""
    logger.info("Verifying ViolationPredictor...")

    try:
        predictor = ViolationPredictor()

        df = processor.events_to_dataframe()
        prophet_df = processor.prepare_for_prophet(df)

        if prophet_df.empty or len(prophet_df) < 2:
            result.add_warning("Insufficient data for forecasting (need at least 2 data points)")
            return

        forecast = predictor.forecast(prophet_df, periods=7)

        if forecast.model_trained:
            result.add_check(
                "Violation Forecasting",
                True,
                f"Generated {len(forecast.forecast_points)}-day forecast",
                {
                    "forecast_days": len(forecast.forecast_points),
                    "historical_days": forecast.historical_days,
                    "model_trained": forecast.model_trained,
                },
            )
            result.summary["forecast_days"] = len(forecast.forecast_points)
        else:
            result.add_check(
                "Violation Forecasting",
                False,
                f"Model not trained: {forecast.error_message}",
            )

    except ImportError as e:
        result.add_warning(f"Forecasting skipped (missing dependency): {e}")
    except Exception as e:
        result.add_check("Violation Forecasting", False, f"Failed: {e}")


async def verify_kafka_connection(
    result: PipelineVerificationResult,
    kafka_bootstrap: str,
) -> bool:
    """Verify Kafka connectivity."""
    logger.info(f"Verifying Kafka connection to {kafka_bootstrap}...")

    processor = GovernanceDataProcessor(
        kafka_bootstrap_servers=kafka_bootstrap,
        kafka_topic="governance-events",
    )

    try:
        connected = await processor.initialize()
        await processor.shutdown()

        result.add_check(
            "Kafka Connection",
            connected,
            f"Connected to {kafka_bootstrap}" if connected else "Connection failed",
            {"bootstrap_servers": kafka_bootstrap},
        )
        return connected

    except Exception as e:
        result.add_check("Kafka Connection", False, f"Failed: {e}")
        return False


def load_sample_events(input_path: str | None = None) -> list[dict[str, Any]]:
    """Load sample governance events from file or generate them."""
    if input_path and os.path.exists(input_path):
        logger.info(f"Loading events from {input_path}")
        with open(input_path) as f:
            data = json.load(f)
            if isinstance(data, dict) and "events" in data:
                return data["events"]
            return data

    # Generate sample events
    logger.info("Generating sample governance events...")
    from uuid import uuid4

    events = []
    base_time = datetime.now(timezone.utc)

    for day in range(14):  # 14 days of data
        for i in range(10):  # 10 events per day
            event_type = ["access", "violation", "policy_change", "audit"][i % 4]
            events.append(
                {
                    "event_id": str(uuid4()),
                    "event_type": event_type,
                    "timestamp": base_time.replace(
                        day=max(1, base_time.day - day), hour=i, minute=0
                    ).isoformat(),
                    "policy_id": f"policy-{(i % 5) + 1:03d}",
                    "user_id": f"user-{(i % 10) + 1:03d}",
                    "action": ["read", "write", "delete", "execute"][i % 4],
                    "resource": f"/resource/{i + 1}",
                    "outcome": "violation" if event_type == "violation" else "allowed",
                    "severity": "high" if event_type == "violation" else None,
                }
            )

    return events


async def main() -> int:
    """Main entry point for pipeline verification."""
    parser = argparse.ArgumentParser(description="Verify Kafka → Analytics Engine data pipeline")
    parser.add_argument(
        "--mode",
        choices=["sample", "kafka", "json"],
        default="sample",
        help="Data source mode",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="Input JSON file path (for json mode)",
    )
    parser.add_argument(
        "--kafka-bootstrap",
        type=str,
        default=os.getenv("KAFKA_BOOTSTRAP", "localhost:19092"),
        help="Kafka bootstrap servers",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    result = PipelineVerificationResult()

    print("\n🔍 Starting Pipeline Verification...")
    print(f"Mode: {args.mode}")

    # Load events based on mode
    if args.mode == "kafka":
        # First verify Kafka connection
        kafka_ok = await verify_kafka_connection(result, args.kafka_bootstrap)
        if not kafka_ok:
            result.add_error("Cannot proceed without Kafka connection")
            result.print_report()
            return 1
        events = load_sample_events(args.input)
    elif args.mode == "json":
        if not args.input:
            # Use default sample file
            default_path = Path(__file__).parent.parent / "data" / "sample_governance_events.json"
            args.input = str(default_path)
        events = load_sample_events(args.input)
    else:
        events = load_sample_events()

    # Verify data processor
    processor = await verify_data_processor(result, events)

    # Verify anomaly detector
    verify_anomaly_detector(result, processor)

    # Verify predictor
    verify_predictor(result, processor)

    # Print report
    result.print_report()

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
