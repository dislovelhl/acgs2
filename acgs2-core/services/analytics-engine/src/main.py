#!/usr/bin/env python3
"""
Analytics Engine - Main Orchestrator

Batch processing engine for governance analytics including:
- Data processing from Kafka governance events
- Anomaly detection using IsolationForest
- Violation forecasting using Prophet
- AI-powered insight generation using OpenAI
- Executive PDF report generation

This is a batch processing service, not an HTTP server.

Usage:
    python src/main.py --help
    python src/main.py --mode full
    python src/main.py --mode anomaly --input data/events.json
    python src/main.py --mode forecast --output reports/
    python src/main.py --mode report --pdf governance_report.pdf
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

from .anomaly_detector import AnomalyDetector, AnomalyDetectionResult
from .data_processor import GovernanceDataProcessor, ProcessedMetrics
from .insight_generator import InsightGenerator, InsightGenerationResult
from .pdf_exporter import PDFExporter, PDFExportResult, PDFReportMetadata
from .predictor import ViolationForecast, ViolationPredictor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("analytics-engine")


class AnalyticsEngineConfig:
    """Configuration for the analytics engine."""

    def __init__(
        self,
        kafka_bootstrap: Optional[str] = None,
        kafka_topic: str = "governance-events",
        redis_url: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        tenant_id: Optional[str] = None,
        output_dir: Optional[str] = None,
        contamination: float = 0.1,
        forecast_days: int = 30,
    ):
        """
        Initialize engine configuration.

        Args:
            kafka_bootstrap: Kafka bootstrap servers
            kafka_topic: Topic for governance events
            redis_url: Redis URL for caching
            openai_api_key: OpenAI API key for insights
            tenant_id: Tenant identifier
            output_dir: Directory for output files
            contamination: Anomaly detection contamination rate
            forecast_days: Number of days to forecast
        """
        self.kafka_bootstrap = kafka_bootstrap or os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
        self.kafka_topic = kafka_topic
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.tenant_id = tenant_id or os.getenv("TENANT_ID", "acgs-dev")
        self.output_dir = output_dir or os.getenv("PDF_OUTPUT_DIR", "./data")
        self.contamination = contamination
        self.forecast_days = forecast_days


class AnalyticsEngineResult:
    """Container for analytics engine processing results."""

    def __init__(self):
        self.timestamp: datetime = datetime.now(timezone.utc)
        self.events_processed: int = 0
        self.metrics: Optional[ProcessedMetrics] = None
        self.anomalies: Optional[AnomalyDetectionResult] = None
        self.forecast: Optional[ViolationForecast] = None
        self.insights: Optional[InsightGenerationResult] = None
        self.pdf_result: Optional[PDFExportResult] = None
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary for serialization."""
        result = {
            "timestamp": self.timestamp.isoformat(),
            "events_processed": self.events_processed,
            "errors": self.errors,
            "warnings": self.warnings,
        }

        if self.metrics:
            result["metrics"] = {
                "period_start": self.metrics.period_start.isoformat(),
                "period_end": self.metrics.period_end.isoformat(),
                "total_events": self.metrics.total_events,
                "violation_count": self.metrics.violation_count,
                "policy_changes": self.metrics.policy_changes,
                "unique_users": self.metrics.unique_users,
                "unique_policies": self.metrics.unique_policies,
                "severity_distribution": self.metrics.severity_distribution,
                "top_violated_policies": self.metrics.top_violated_policies,
            }

        if self.anomalies:
            result["anomalies"] = {
                "analysis_timestamp": self.anomalies.analysis_timestamp.isoformat(),
                "total_records_analyzed": self.anomalies.total_records_analyzed,
                "anomalies_detected": self.anomalies.anomalies_detected,
                "model_trained": self.anomalies.model_trained,
                "anomalies": [
                    {
                        "anomaly_id": a.anomaly_id,
                        "timestamp": a.timestamp.isoformat(),
                        "severity_score": a.severity_score,
                        "severity_label": a.severity_label,
                        "description": a.description,
                        "affected_metrics": a.affected_metrics,
                    }
                    for a in self.anomalies.anomalies
                ],
            }

        if self.forecast:
            result["forecast"] = {
                "forecast_timestamp": self.forecast.forecast_timestamp.isoformat(),
                "historical_days": self.forecast.historical_days,
                "forecast_days": self.forecast.forecast_days,
                "model_trained": self.forecast.model_trained,
                "error_message": self.forecast.error_message,
                "summary": self.forecast.summary,
                "forecast_points": [
                    {
                        "date": p.date.strftime("%Y-%m-%d"),
                        "predicted_value": round(p.predicted_value, 2),
                        "lower_bound": round(p.lower_bound, 2),
                        "upper_bound": round(p.upper_bound, 2),
                    }
                    for p in self.forecast.forecast_points
                ],
            }

        if self.insights:
            result["insights"] = {
                "generation_timestamp": self.insights.generation_timestamp.isoformat(),
                "model_used": self.insights.model_used,
                "tokens_used": self.insights.tokens_used,
                "cached": self.insights.cached,
                "error_message": self.insights.error_message,
            }
            if self.insights.insight:
                result["insights"]["summary"] = self.insights.insight.summary
                result["insights"]["business_impact"] = self.insights.insight.business_impact
                result["insights"]["recommended_action"] = self.insights.insight.recommended_action

        if self.pdf_result:
            result["pdf_export"] = {
                "success": self.pdf_result.success,
                "filename": self.pdf_result.filename,
                "file_path": self.pdf_result.file_path,
                "file_size_bytes": self.pdf_result.file_size_bytes,
                "error_message": self.pdf_result.error_message,
            }

        return result


class AnalyticsEngine:
    """
    Main orchestrator for the analytics engine.

    Coordinates data processing, anomaly detection, forecasting,
    insight generation, and PDF report creation.
    """

    def __init__(self, config: Optional[AnalyticsEngineConfig] = None):
        """
        Initialize the analytics engine.

        Args:
            config: Engine configuration (uses defaults if None)
        """
        self.config = config or AnalyticsEngineConfig()

        # Initialize components
        self.data_processor = GovernanceDataProcessor(
            kafka_bootstrap_servers=self.config.kafka_bootstrap,
            kafka_topic=self.config.kafka_topic,
        )
        self.anomaly_detector = AnomalyDetector(
            contamination=self.config.contamination,
        )
        self.predictor = ViolationPredictor()
        self.insight_generator = InsightGenerator(
            api_key=self.config.openai_api_key,
        )
        self.pdf_exporter = PDFExporter(
            output_dir=self.config.output_dir,
        )

        self._events_df: Optional[pd.DataFrame] = None

    def get_status(self) -> Dict[str, Any]:
        """Get the status of all engine components."""
        return {
            "kafka_configured": bool(self.config.kafka_bootstrap),
            "openai_available": self.insight_generator.is_available,
            "anomaly_detector": self.anomaly_detector.get_model_info(),
            "predictor": self.predictor.get_model_info(),
            "insight_generator": self.insight_generator.get_generator_info(),
            "pdf_exporter": self.pdf_exporter.get_exporter_info(),
            "tenant_id": self.config.tenant_id,
        }

    async def load_from_kafka(
        self,
        max_batches: int = 10,
        batch_timeout_ms: int = 10000,
    ) -> pd.DataFrame:
        """
        Load governance events from Kafka.

        Args:
            max_batches: Maximum number of batches to consume
            batch_timeout_ms: Timeout per batch in milliseconds

        Returns:
            DataFrame with consumed events
        """
        logger.info(f"Loading events from Kafka ({self.config.kafka_topic})...")
        self._events_df = await self.data_processor.run_batch_processing(
            max_batches=max_batches,
            batch_timeout_ms=batch_timeout_ms,
        )
        logger.info(f"Loaded {len(self._events_df)} events from Kafka")
        return self._events_df

    def load_from_json(self, json_path: str) -> pd.DataFrame:
        """
        Load governance events from a JSON file.

        Args:
            json_path: Path to JSON file with events

        Returns:
            DataFrame with loaded events
        """
        logger.info(f"Loading events from JSON: {json_path}")
        with open(json_path, "r") as f:
            data = json.load(f)

        if isinstance(data, dict) and "events" in data:
            events_data = data["events"]
        elif isinstance(data, list):
            events_data = data
        else:
            raise ValueError("JSON must be a list of events or contain 'events' key")

        self.data_processor.load_from_json(events_data)
        self._events_df = self.data_processor.events_to_dataframe()
        logger.info(f"Loaded {len(self._events_df)} events from JSON")
        return self._events_df

    def generate_sample_data(self, num_days: int = 30) -> pd.DataFrame:
        """
        Generate sample governance data for testing.

        Args:
            num_days: Number of days of sample data to generate

        Returns:
            DataFrame with sample events
        """
        import uuid
        from datetime import timedelta

        import numpy as np

        logger.info(f"Generating {num_days} days of sample data...")

        events = []
        base_date = datetime.now(timezone.utc) - timedelta(days=num_days)

        event_types = ["access", "violation", "policy_change", "audit"]
        outcomes = ["allowed", "denied", "violation"]
        severities = ["low", "medium", "high", "critical"]
        policies = [f"policy-{i:03d}" for i in range(1, 11)]
        users = [f"user-{i:03d}" for i in range(1, 21)]

        for day in range(num_days):
            date = base_date + timedelta(days=day)
            # Random number of events per day (10-50)
            num_events = np.random.randint(10, 51)

            for _ in range(num_events):
                event_type = np.random.choice(event_types, p=[0.6, 0.2, 0.1, 0.1])
                outcome = (
                    "violation" if event_type == "violation" else np.random.choice(outcomes[:2])
                )

                events.append(
                    {
                        "event_id": str(uuid.uuid4()),
                        "event_type": event_type,
                        "timestamp": date
                        + timedelta(
                            hours=np.random.randint(0, 24),
                            minutes=np.random.randint(0, 60),
                        ),
                        "policy_id": np.random.choice(policies),
                        "user_id": np.random.choice(users),
                        "action": np.random.choice(["read", "write", "delete", "execute"]),
                        "resource": f"/resource/{np.random.randint(1, 100)}",
                        "outcome": outcome,
                        "severity": (
                            np.random.choice(severities) if outcome == "violation" else None
                        ),
                    }
                )

        self.data_processor.load_from_json(events)
        self._events_df = self.data_processor.events_to_dataframe()
        logger.info(f"Generated {len(self._events_df)} sample events")
        return self._events_df

    def run_anomaly_detection(
        self,
        df: Optional[pd.DataFrame] = None,
    ) -> AnomalyDetectionResult:
        """
        Run anomaly detection on governance data.

        Args:
            df: DataFrame with events (uses loaded data if None)

        Returns:
            AnomalyDetectionResult with detected anomalies
        """
        if df is None:
            df = self._events_df

        if df is None or df.empty:
            logger.warning("No data available for anomaly detection")
            return AnomalyDetectionResult(
                analysis_timestamp=datetime.now(timezone.utc),
                total_records_analyzed=0,
                anomalies_detected=0,
                contamination_rate=self.config.contamination,
                anomalies=[],
                model_trained=False,
            )

        logger.info("Running anomaly detection...")
        anomaly_df = self.data_processor.prepare_for_anomaly_detection(df)
        result = self.anomaly_detector.detect_anomalies(anomaly_df)
        logger.info(f"Detected {result.anomalies_detected} anomalies")
        return result

    def run_forecasting(
        self,
        df: Optional[pd.DataFrame] = None,
        periods: Optional[int] = None,
    ) -> ViolationForecast:
        """
        Run violation forecasting on governance data.

        Args:
            df: DataFrame with events (uses loaded data if None)
            periods: Number of days to forecast (uses config default if None)

        Returns:
            ViolationForecast with predictions
        """
        if df is None:
            df = self._events_df

        if periods is None:
            periods = self.config.forecast_days

        if df is None or df.empty:
            logger.warning("No data available for forecasting")
            return ViolationForecast(
                forecast_timestamp=datetime.now(timezone.utc),
                historical_days=0,
                forecast_days=periods,
                forecast_points=[],
                model_trained=False,
                error_message="No historical data provided for forecasting",
            )

        logger.info(f"Running {periods}-day violation forecast...")
        prophet_df = self.data_processor.prepare_for_prophet(df)
        result = self.predictor.forecast(prophet_df, periods=periods)
        logger.info(
            f"Forecast generated: {len(result.forecast_points)} points, "
            f"model_trained={result.model_trained}"
        )
        return result

    def run_insight_generation(
        self,
        df: Optional[pd.DataFrame] = None,
    ) -> InsightGenerationResult:
        """
        Generate AI-powered insights from governance data.

        Args:
            df: DataFrame with events (uses loaded data if None)

        Returns:
            InsightGenerationResult with AI insights
        """
        if df is None:
            df = self._events_df

        if df is None or df.empty:
            logger.warning("No data available for insight generation")
            return InsightGenerationResult(
                generation_timestamp=datetime.now(timezone.utc),
                insight=None,
                model_used=self.insight_generator.insight_model,
                tokens_used=0,
                cached=False,
                error_message="No data available for insight generation",
            )

        logger.info("Generating AI insights...")
        metrics = self.data_processor.compute_metrics(df)

        # Prepare data for insight generation
        top_policy = (
            metrics.top_violated_policies[0]["policy_id"]
            if metrics.top_violated_policies
            else "None"
        )

        governance_data = {
            "violation_count": metrics.violation_count,
            "top_violated_policy": top_policy,
            "trend": "stable",  # Could be computed from historical data
            "total_events": metrics.total_events,
            "unique_users": metrics.unique_users,
            "severity_distribution": metrics.severity_distribution,
        }

        result = self.insight_generator.generate_insight(governance_data)
        logger.info(
            f"Insights generated: model={result.model_used}, " f"tokens={result.tokens_used}"
        )
        return result

    def generate_pdf_report(
        self,
        df: Optional[pd.DataFrame] = None,
        anomalies: Optional[AnomalyDetectionResult] = None,
        forecast: Optional[ViolationForecast] = None,
        insights: Optional[InsightGenerationResult] = None,
        output_path: Optional[str] = None,
    ) -> PDFExportResult:
        """
        Generate a PDF executive report.

        Args:
            df: DataFrame with events (uses loaded data if None)
            anomalies: Anomaly detection results (runs detection if None)
            forecast: Forecast results (runs forecasting if None)
            insights: AI insights (runs generation if None)
            output_path: Path for output PDF file

        Returns:
            PDFExportResult with export status
        """
        if df is None:
            df = self._events_df

        if df is None or df.empty:
            logger.warning("No data available for PDF report")
            return PDFExportResult(
                success=False,
                export_timestamp=datetime.now(timezone.utc),
                error_message="No data available for report generation",
            )

        logger.info("Generating PDF executive report...")

        # Compute metrics
        metrics = self.data_processor.compute_metrics(df)
        governance_data = {
            "total_events": metrics.total_events,
            "violation_count": metrics.violation_count,
            "unique_users": metrics.unique_users,
            "policy_changes": metrics.policy_changes,
            "trend": "stable",
        }

        # Prepare anomalies dict
        anomalies_dict = None
        if anomalies:
            anomalies_dict = {
                "total_records_analyzed": anomalies.total_records_analyzed,
                "anomalies_detected": anomalies.anomalies_detected,
                "anomalies": [
                    {
                        "timestamp": a.timestamp.isoformat(),
                        "severity_label": a.severity_label,
                        "description": a.description,
                    }
                    for a in anomalies.anomalies
                ],
            }

        # Prepare forecast dict
        predictions_dict = None
        if forecast:
            predictions_dict = self.predictor.get_forecast_as_dict(forecast)

        # Prepare insights dict
        insights_dict = None
        if insights and insights.insight:
            insights_dict = {
                "summary": insights.insight.summary,
                "business_impact": insights.insight.business_impact,
                "recommended_action": insights.insight.recommended_action,
            }

        # Generate report
        metadata = PDFReportMetadata(
            title="Governance Analytics Report",
            subtitle="Executive Summary",
            tenant_id=self.config.tenant_id,
            period_start=metrics.period_start,
            period_end=metrics.period_end,
        )

        result = self.pdf_exporter.generate_executive_report(
            governance_data=governance_data,
            insights=insights_dict,
            anomalies=anomalies_dict,
            predictions=predictions_dict,
            output_path=output_path,
            metadata=metadata,
        )

        if result.success:
            logger.info(f"PDF report generated: {result.file_path}")
        else:
            logger.error(f"PDF generation failed: {result.error_message}")

        return result

    async def run_full_pipeline(
        self,
        source: str = "kafka",
        input_path: Optional[str] = None,
        output_pdf: Optional[str] = None,
    ) -> AnalyticsEngineResult:
        """
        Run the complete analytics pipeline.

        Args:
            source: Data source ('kafka', 'json', or 'sample')
            input_path: Path for JSON input (if source='json')
            output_pdf: Path for PDF output

        Returns:
            AnalyticsEngineResult with all processing results
        """
        result = AnalyticsEngineResult()

        try:
            # Load data
            if source == "kafka":
                df = await self.load_from_kafka()
            elif source == "json" and input_path:
                df = self.load_from_json(input_path)
            elif source == "sample":
                df = self.generate_sample_data()
            else:
                result.errors.append(f"Invalid source: {source}")
                return result

            result.events_processed = len(df)

            if df.empty:
                result.warnings.append("No events to process")
                return result

            # Compute metrics
            result.metrics = self.data_processor.compute_metrics(df)

            # Run anomaly detection
            result.anomalies = self.run_anomaly_detection(df)

            # Run forecasting
            result.forecast = self.run_forecasting(df)

            # Generate insights (if OpenAI available)
            if self.insight_generator.is_available:
                result.insights = self.run_insight_generation(df)
            else:
                result.warnings.append("OpenAI not configured, skipping insights")

            # Generate PDF report
            if output_pdf:
                result.pdf_result = self.generate_pdf_report(
                    df=df,
                    anomalies=result.anomalies,
                    forecast=result.forecast,
                    insights=result.insights,
                    output_path=output_pdf,
                )

        except Exception as e:
            logger.exception("Pipeline error")
            result.errors.append(str(e))

        return result


def create_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="analytics-engine",
        description=(
            "ACGS-2 Analytics Engine - Batch processing for governance analytics.\n\n"
            "Processes governance events from Kafka or JSON files, performs anomaly\n"
            "detection, generates violation forecasts, creates AI-powered insights,\n"
            "and produces executive PDF reports."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline with Kafka input
  python -m src.main --mode full

  # Run with sample data for testing
  python -m src.main --mode full --source sample --output report.pdf

  # Run anomaly detection only from JSON file
  python -m src.main --mode anomaly --input events.json

  # Generate forecast from sample data
  python -m src.main --mode forecast --source sample --days 30

  # Show engine status
  python -m src.main --status

Environment Variables:
  KAFKA_BOOTSTRAP     Kafka bootstrap servers (default: localhost:9092)
  KAFKA_TOPIC         Kafka topic for governance events
  REDIS_URL           Redis URL for caching
  OPENAI_API_KEY      OpenAI API key for AI insights
  TENANT_ID           Tenant identifier (default: acgs-dev)
  PDF_OUTPUT_DIR      Directory for PDF output files
""",
    )

    parser.add_argument(
        "--mode",
        choices=["full", "anomaly", "forecast", "insight", "report"],
        default="full",
        help="Processing mode: full (all), anomaly, forecast, insight, or report",
    )

    parser.add_argument(
        "--source",
        choices=["kafka", "json", "sample"],
        default="kafka",
        help="Data source: kafka, json file, or sample data",
    )

    parser.add_argument(
        "--input",
        "-i",
        type=str,
        metavar="FILE",
        help="Input JSON file path (required for --source json)",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        metavar="FILE",
        help="Output PDF file path for reports",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        metavar="DIR",
        help="Output directory for generated files",
    )

    parser.add_argument(
        "--days",
        type=int,
        default=30,
        metavar="N",
        help="Number of days to forecast (default: 30)",
    )

    parser.add_argument(
        "--contamination",
        type=float,
        default=0.1,
        metavar="RATE",
        help="Anomaly detection contamination rate 0.01-0.5 (default: 0.1)",
    )

    parser.add_argument(
        "--sample-days",
        type=int,
        default=30,
        metavar="N",
        help="Number of days for sample data generation (default: 30)",
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="Show engine component status and exit",
    )

    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output results as JSON",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress non-error output",
    )

    return parser


async def main_async(args: argparse.Namespace) -> int:
    """Async main entry point."""
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.quiet:
        logging.getLogger().setLevel(logging.ERROR)

    # Create engine configuration
    config = AnalyticsEngineConfig(
        output_dir=args.output_dir,
        contamination=args.contamination,
        forecast_days=args.days,
    )

    # Initialize engine
    engine = AnalyticsEngine(config)

    # Handle status check
    if args.status:
        status = engine.get_status()
        if args.json_output:
            print(json.dumps(status, indent=2, default=str))
        else:
            print("\n=== Analytics Engine Status ===")
            print(f"Kafka configured: {status['kafka_configured']}")
            print(f"OpenAI available: {status['openai_available']}")
            print(f"Tenant ID: {status['tenant_id']}")
            print("\nComponent Status:")
            print(
                f"  - Anomaly Detector: sklearn={status['anomaly_detector']['sklearn_available']}"
            )
            print(f"  - Predictor: prophet={status['predictor']['prophet_available']}")
            api_key_configured = status["insight_generator"]["api_key_configured"]
            print(f"  - Insight Generator: api_key={api_key_configured}")
            print(f"  - PDF Exporter: reportlab={status['pdf_exporter']['reportlab_available']}")
        return 0

    # Validate arguments
    if args.source == "json" and not args.input:
        print("Error: --input required when --source is 'json'", file=sys.stderr)
        return 1

    # Run based on mode
    try:
        if args.mode == "full":
            result = await engine.run_full_pipeline(
                source=args.source,
                input_path=args.input,
                output_pdf=args.output,
            )
        else:
            # Load data first for other modes
            if args.source == "kafka":
                await engine.load_from_kafka()
            elif args.source == "json":
                engine.load_from_json(args.input)
            else:
                engine.generate_sample_data(num_days=args.sample_days)

            result = AnalyticsEngineResult()
            result.events_processed = len(engine._events_df) if engine._events_df is not None else 0

            if result.events_processed == 0:
                result.warnings.append("No events to process")
            else:
                result.metrics = engine.data_processor.compute_metrics(engine._events_df)

                if args.mode == "anomaly":
                    result.anomalies = engine.run_anomaly_detection()
                elif args.mode == "forecast":
                    result.forecast = engine.run_forecasting()
                elif args.mode == "insight":
                    result.insights = engine.run_insight_generation()
                elif args.mode == "report":
                    result.anomalies = engine.run_anomaly_detection()
                    result.forecast = engine.run_forecasting()
                    if engine.insight_generator.is_available:
                        result.insights = engine.run_insight_generation()
                    result.pdf_result = engine.generate_pdf_report(
                        anomalies=result.anomalies,
                        forecast=result.forecast,
                        insights=result.insights,
                        output_path=args.output,
                    )

        # Output results
        if args.json_output:
            print(json.dumps(result.to_dict(), indent=2, default=str))
        else:
            print("\n=== Analytics Engine Results ===")
            print(f"Timestamp: {result.timestamp.isoformat()}")
            print(f"Events Processed: {result.events_processed}")

            if result.metrics:
                print("\nMetrics:")
                print(f"  - Violations: {result.metrics.violation_count}")
                print(f"  - Total Events: {result.metrics.total_events}")
                print(f"  - Unique Users: {result.metrics.unique_users}")

            if result.anomalies:
                print(f"\nAnomalies: {result.anomalies.anomalies_detected} detected")

            if result.forecast:
                if result.forecast.model_trained:
                    summary = result.forecast.summary
                    print(f"\nForecast ({result.forecast.forecast_days} days):")
                    if "trend_direction" in summary:
                        print(f"  - Trend: {summary['trend_direction']}")
                    if "total_predicted_violations" in summary:
                        print(f"  - Total Predicted: {summary['total_predicted_violations']:.0f}")
                else:
                    print(f"\nForecast: {result.forecast.error_message}")

            if result.insights:
                if result.insights.insight:
                    print(f"\nInsight: {result.insights.insight.summary}")
                else:
                    print(f"\nInsight: {result.insights.error_message}")

            if result.pdf_result:
                if result.pdf_result.success:
                    print(f"\nPDF Report: {result.pdf_result.file_path}")
                else:
                    print(f"\nPDF Report: {result.pdf_result.error_message}")

            if result.warnings:
                print(f"\nWarnings: {', '.join(result.warnings)}")

            if result.errors:
                print(f"\nErrors: {', '.join(result.errors)}")
                return 1

        return 0

    except Exception as e:
        logger.exception("Engine error")
        if args.json_output:
            print(json.dumps({"error": str(e)}, indent=2))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
