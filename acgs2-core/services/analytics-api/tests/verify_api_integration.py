#!/usr/bin/env python3
"""
Verification script for analytics-api ↔ analytics-engine integration.

Constitutional Hash: cdd01ef066bc6cf2

This script performs end-to-end verification of the analytics-api endpoints
by calling each endpoint and validating the response structure and content.

Usage:
    # Verify against running API server
    python verify_api_integration.py --url http://localhost:8080

    # Verify against FastAPI TestClient (no server needed)
    python verify_api_integration.py --testclient

Verification Steps:
    1. GET /insights - Verify AI-generated summary returned
    2. GET /anomalies - Verify detected outliers returned
    3. GET /predictions - Verify 30-day forecast returned
    4. POST /query - Verify natural language response
    5. POST /export/pdf - Verify PDF download
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add analytics-api to path
API_SRC_PATH = Path(__file__).parent.parent / "src"
if str(API_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(API_SRC_PATH))


class VerificationResult:
    """Result of a single verification check."""

    def __init__(self, name: str, passed: bool, message: str, details: Optional[Dict] = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class APIVerifier:
    """Verifier for analytics-api integration with analytics-engine."""

    def __init__(self, base_url: str = "http://localhost:8080", use_testclient: bool = False):
        self.base_url = base_url.rstrip("/")
        self.use_testclient = use_testclient
        self.client = None
        self.results: List[VerificationResult] = []

        if use_testclient:
            self._setup_testclient()
        else:
            self._setup_http_client()

    def _setup_testclient(self):
        """Set up FastAPI TestClient."""
        try:
            from fastapi.testclient import TestClient
            from main import app

            self.client = TestClient(app)
            print("✓ FastAPI TestClient initialized")
        except ImportError as e:
            print(f"✗ Failed to initialize TestClient: {e}")
            sys.exit(1)

    def _setup_http_client(self):
        """Set up HTTP client for external requests."""
        try:
            import requests

            self.client = requests
            print(f"✓ HTTP client initialized for {self.base_url}")
        except ImportError:
            print("✗ requests library not available")
            print("  Install with: pip install requests")
            sys.exit(1)

    def _make_request(
        self, method: str, endpoint: str, json_data: Optional[Dict] = None
    ) -> Tuple[int, Any, Dict]:
        """Make HTTP request and return status, data, headers."""
        url = endpoint if self.use_testclient else f"{self.base_url}{endpoint}"

        if self.use_testclient:
            if method == "GET":
                response = self.client.get(url)
            elif method == "POST":
                response = self.client.post(url, json=json_data)
            else:
                raise ValueError(f"Unsupported method: {method}")

            try:
                data = response.json()
            except (json.JSONDecodeError, ValueError):
                data = response.content

            return response.status_code, data, dict(response.headers)
        else:
            import requests

            if method == "GET":
                response = requests.get(url, timeout=30)
            elif method == "POST":
                response = requests.post(url, json=json_data, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")

            try:
                data = response.json()
            except (json.JSONDecodeError, ValueError):
                data = response.content

            return response.status_code, data, dict(response.headers)

    def _add_result(
        self,
        name: str,
        passed: bool,
        message: str,
        details: Optional[Dict] = None,
    ):
        """Add a verification result."""
        result = VerificationResult(name, passed, message, details)
        self.results.append(result)

        status = "✓" if passed else "✗"
        print(f"  {status} {name}: {message}")

    def verify_insights(self) -> bool:
        """Verify GET /insights endpoint returns AI-generated summary."""
        print("\n[1/5] Verifying GET /insights...")

        try:
            status, data, headers = self._make_request("GET", "/insights")

            # Check status code
            if status != 200:
                self._add_result(
                    "insights_status",
                    False,
                    f"Expected 200, got {status}",
                    {"status_code": status},
                )
                return False

            self._add_result("insights_status", True, "Returns 200 OK")

            # Check required fields
            required_fields = [
                "summary",
                "business_impact",
                "recommended_action",
                "confidence",
                "generated_at",
            ]
            missing = [f for f in required_fields if f not in data]

            if missing:
                self._add_result(
                    "insights_fields",
                    False,
                    f"Missing fields: {missing}",
                )
                return False

            self._add_result("insights_fields", True, "All required fields present")

            # Check summary content
            if not data.get("summary") or len(data["summary"]) < 10:
                self._add_result(
                    "insights_summary",
                    False,
                    "Summary is empty or too short",
                )
                return False

            self._add_result(
                "insights_summary",
                True,
                f"Summary returned ({len(data['summary'])} chars)",
            )

            # Check confidence range
            confidence = data.get("confidence", 0)
            if not (0.0 <= confidence <= 1.0):
                self._add_result(
                    "insights_confidence",
                    False,
                    f"Confidence out of range: {confidence}",
                )
                return False

            self._add_result(
                "insights_confidence",
                True,
                f"Confidence valid: {confidence}",
            )

            return True

        except Exception as e:
            self._add_result("insights", False, f"Exception: {e}")
            return False

    def verify_anomalies(self) -> bool:
        """Verify GET /anomalies endpoint returns detected outliers."""
        print("\n[2/5] Verifying GET /anomalies...")

        try:
            status, data, headers = self._make_request("GET", "/anomalies")

            # Check status code
            if status != 200:
                self._add_result(
                    "anomalies_status",
                    False,
                    f"Expected 200, got {status}",
                )
                return False

            self._add_result("anomalies_status", True, "Returns 200 OK")

            # Check required fields
            required_fields = [
                "analysis_timestamp",
                "total_records_analyzed",
                "anomalies_detected",
                "contamination_rate",
                "anomalies",
                "model_trained",
            ]
            missing = [f for f in required_fields if f not in data]

            if missing:
                self._add_result(
                    "anomalies_fields",
                    False,
                    f"Missing fields: {missing}",
                )
                return False

            self._add_result("anomalies_fields", True, "All required fields present")

            # Check anomalies is a list
            if not isinstance(data.get("anomalies"), list):
                self._add_result(
                    "anomalies_list",
                    False,
                    "Anomalies should be a list",
                )
                return False

            detected_count = data.get("anomalies_detected", 0)
            self._add_result(
                "anomalies_list",
                True,
                f"{detected_count} anomalies detected",
            )

            # If anomalies detected, verify structure
            if detected_count > 0 and data["anomalies"]:
                anomaly = data["anomalies"][0]
                anomaly_fields = ["anomaly_id", "timestamp", "severity_score", "severity_label"]
                missing_anomaly = [f for f in anomaly_fields if f not in anomaly]

                if missing_anomaly:
                    self._add_result(
                        "anomalies_structure",
                        False,
                        f"Anomaly missing fields: {missing_anomaly}",
                    )
                    return False

                self._add_result(
                    "anomalies_structure",
                    True,
                    f"Anomaly structure valid (severity: {anomaly['severity_label']})",
                )

            return True

        except Exception as e:
            self._add_result("anomalies", False, f"Exception: {e}")
            return False

    def verify_predictions(self) -> bool:
        """Verify GET /predictions endpoint returns 30-day forecast."""
        print("\n[3/5] Verifying GET /predictions...")

        try:
            status, data, headers = self._make_request("GET", "/predictions")

            # Check status code
            if status != 200:
                self._add_result(
                    "predictions_status",
                    False,
                    f"Expected 200, got {status}",
                )
                return False

            self._add_result("predictions_status", True, "Returns 200 OK")

            # Check required fields
            required_fields = [
                "forecast_timestamp",
                "historical_days",
                "forecast_days",
                "model_trained",
                "predictions",
                "summary",
            ]
            missing = [f for f in required_fields if f not in data]

            if missing:
                self._add_result(
                    "predictions_fields",
                    False,
                    f"Missing fields: {missing}",
                )
                return False

            self._add_result("predictions_fields", True, "All required fields present")

            # Check predictions is a list
            if not isinstance(data.get("predictions"), list):
                self._add_result(
                    "predictions_list",
                    False,
                    "Predictions should be a list",
                )
                return False

            prediction_count = len(data.get("predictions", []))
            model_trained = data.get("model_trained", False)

            self._add_result(
                "predictions_list",
                True,
                f"{prediction_count} prediction points (model_trained: {model_trained})",
            )

            # Check summary status
            summary = data.get("summary", {})
            summary_status = summary.get("status", "unknown")

            self._add_result(
                "predictions_summary",
                True,
                f"Summary status: {summary_status}",
            )

            # If predictions present, verify structure
            if prediction_count > 0:
                pred = data["predictions"][0]
                pred_fields = ["date", "predicted_value", "lower_bound", "upper_bound"]
                missing_pred = [f for f in pred_fields if f not in pred]

                if missing_pred:
                    self._add_result(
                        "predictions_structure",
                        False,
                        f"Prediction point missing fields: {missing_pred}",
                    )
                    return False

                # Check values are non-negative
                if pred.get("predicted_value", -1) < 0:
                    self._add_result(
                        "predictions_values",
                        False,
                        "Predicted values should be non-negative",
                    )
                    return False

                self._add_result(
                    "predictions_structure",
                    True,
                    f"Prediction structure valid (first: {pred['date']})",
                )

            return True

        except Exception as e:
            self._add_result("predictions", False, f"Exception: {e}")
            return False

    def verify_query(self) -> bool:
        """Verify POST /query endpoint returns natural language response."""
        print("\n[4/5] Verifying POST /query...")

        try:
            question = "Show violations this week"
            status, data, headers = self._make_request(
                "POST",
                "/query",
                json_data={"question": question},
            )

            # Check status code
            if status != 200:
                self._add_result(
                    "query_status",
                    False,
                    f"Expected 200, got {status}",
                )
                return False

            self._add_result("query_status", True, "Returns 200 OK")

            # Check required fields
            required_fields = ["query", "answer", "data", "query_understood", "generated_at"]
            missing = [f for f in required_fields if f not in data]

            if missing:
                self._add_result(
                    "query_fields",
                    False,
                    f"Missing fields: {missing}",
                )
                return False

            self._add_result("query_fields", True, "All required fields present")

            # Check query echoed
            if data.get("query") != question:
                self._add_result(
                    "query_echo",
                    False,
                    "Original query not echoed correctly",
                )
                return False

            self._add_result("query_echo", True, "Query echoed correctly")

            # Check answer content
            answer = data.get("answer", "")
            if not answer or len(answer) < 10:
                self._add_result(
                    "query_answer",
                    False,
                    "Answer is empty or too short",
                )
                return False

            self._add_result(
                "query_answer",
                True,
                f"Answer returned ({len(answer)} chars)",
            )

            return True

        except Exception as e:
            self._add_result("query", False, f"Exception: {e}")
            return False

    def verify_export_pdf(self) -> bool:
        """Verify POST /export/pdf endpoint returns PDF download."""
        print("\n[5/5] Verifying POST /export/pdf...")

        try:
            status, data, headers = self._make_request("POST", "/export/pdf")

            # 200 = success, 503 = ReportLab not installed
            if status not in [200, 503]:
                self._add_result(
                    "export_pdf_status",
                    False,
                    f"Expected 200 or 503, got {status}",
                )
                return False

            if status == 503:
                self._add_result(
                    "export_pdf_status",
                    True,
                    "Returns 503 (ReportLab not installed) - acceptable",
                )
                return True

            self._add_result("export_pdf_status", True, "Returns 200 OK")

            # Check content type
            content_type = headers.get("content-type", "")
            if "application/pdf" not in content_type:
                self._add_result(
                    "export_pdf_content_type",
                    False,
                    f"Expected application/pdf, got {content_type}",
                )
                return False

            self._add_result("export_pdf_content_type", True, "Content-Type is application/pdf")

            # Check Content-Disposition
            content_disposition = headers.get("content-disposition", "")
            if "attachment" not in content_disposition:
                self._add_result(
                    "export_pdf_disposition",
                    False,
                    "Missing attachment in Content-Disposition",
                )
                return False

            self._add_result(
                "export_pdf_disposition",
                True,
                "Content-Disposition is attachment",
            )

            # Check PDF content
            pdf_content = data if isinstance(data, bytes) else b""
            if len(pdf_content) < 100:
                self._add_result(
                    "export_pdf_content",
                    False,
                    f"PDF content too small: {len(pdf_content)} bytes",
                )
                return False

            # PDF files start with %PDF
            if not pdf_content.startswith(b"%PDF"):
                self._add_result(
                    "export_pdf_content",
                    False,
                    "Content is not valid PDF (missing %PDF header)",
                )
                return False

            self._add_result(
                "export_pdf_content",
                True,
                f"Valid PDF returned ({len(pdf_content)} bytes)",
            )

            return True

        except Exception as e:
            self._add_result("export_pdf", False, f"Exception: {e}")
            return False

    def run_all_verifications(self) -> bool:
        """Run all verification checks."""
        print("\n" + "=" * 60)
        print("Analytics API ↔ Analytics Engine Integration Verification")
        print("=" * 60)

        all_passed = True

        # Run each verification
        if not self.verify_insights():
            all_passed = False

        if not self.verify_anomalies():
            all_passed = False

        if not self.verify_predictions():
            all_passed = False

        if not self.verify_query():
            all_passed = False

        if not self.verify_export_pdf():
            all_passed = False

        # Print summary
        print("\n" + "=" * 60)
        print("VERIFICATION SUMMARY")
        print("=" * 60)

        passed_count = sum(1 for r in self.results if r.passed)
        total_count = len(self.results)

        print(f"\nTotal checks: {total_count}")
        print(f"Passed: {passed_count}")
        print(f"Failed: {total_count - passed_count}")

        if all_passed:
            print("\n✓ ALL VERIFICATIONS PASSED")
        else:
            print("\n✗ SOME VERIFICATIONS FAILED")
            print("\nFailed checks:")
            for r in self.results:
                if not r.passed:
                    print(f"  - {r.name}: {r.message}")

        return all_passed


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify analytics-api ↔ analytics-engine integration"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8080",
        help="Base URL of analytics-api (default: http://localhost:8080)",
    )
    parser.add_argument(
        "--testclient",
        action="store_true",
        help="Use FastAPI TestClient instead of HTTP requests",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    verifier = APIVerifier(base_url=args.url, use_testclient=args.testclient)
    success = verifier.run_all_verifications()

    if args.json:
        output = {
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "results": [r.to_dict() for r in verifier.results],
        }
        print(json.dumps(output, indent=2))

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
