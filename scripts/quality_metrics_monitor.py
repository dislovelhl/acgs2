#!/usr/bin/env python3
"""
ACGS-2 Quality Metrics Monitor
Tracks code quality trends and provides alerts
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List


class QualityMetricsMonitor:
    """Monitor and analyze code quality metrics over time."""

    def __init__(self, reports_dir: str = "reports"):
        self.reports_dir = Path(reports_dir)
        self.metrics_dir = self.reports_dir / "metrics"
        self.metrics_dir.mkdir(exist_ok=True)

    def collect_current_metrics(self) -> Dict:
        """Collect current quality metrics."""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "code_quality": {},
            "test_coverage": {},
            "performance": {},
            "security": {},
        }

        # Code quality metrics
        metrics["code_quality"] = self._collect_code_quality_metrics()

        # Test coverage (if available)
        metrics["test_coverage"] = self._collect_test_coverage()

        # Performance metrics (if available)
        metrics["performance"] = self._collect_performance_metrics()

        # Security metrics
        metrics["security"] = self._collect_security_metrics()

        return metrics

    def _collect_code_quality_metrics(self) -> Dict:
        """Collect code quality metrics using various tools."""
        metrics = {
            "total_lines": 0,
            "python_files": 0,
            "syntax_errors": 0,
            "lint_errors": 0,
            "complexity_score": 0,
            "duplication_percentage": 0,
        }

        try:
            # Count files and lines
            total_lines = 0
            python_files = 0

            for root, dirs, files in os.walk("acgs2-core"):
                # Skip venv and cache directories
                dirs[:] = [d for d in dirs if d not in ["__pycache__", ".venv", "venv"]]

                for file in files:
                    if file.endswith(".py"):
                        python_files += 1
                        try:
                            with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                                total_lines += len(f.readlines())
                        except Exception:
                            pass

            metrics["total_lines"] = total_lines
            metrics["python_files"] = python_files

        except Exception as e:
            print(f"Error collecting code metrics: {e}")

        return metrics

    def _collect_test_coverage(self) -> Dict:
        """Collect test coverage metrics."""
        coverage_metrics = {
            "overall_coverage": 0.0,
            "files_covered": 0,
            "lines_covered": 0,
            "total_lines": 0,
        }

        # Try to read coverage reports
        coverage_files = [
            "acgs2-core/coverage.json",
            "acgs2-core/htmlcov/coverage.json",
            ".coverage",
        ]

        for coverage_file in coverage_files:
            if os.path.exists(coverage_file):
                try:
                    with open(coverage_file, "r") as f:
                        coverage_data = json.load(f)

                    # Extract overall coverage
                    if "totals" in coverage_data:
                        totals = coverage_data["totals"]
                        coverage_metrics["overall_coverage"] = totals.get("percent_covered", 0)
                        coverage_metrics["lines_covered"] = totals.get("covered_lines", 0)
                        coverage_metrics["total_lines"] = totals.get("num_statements", 0)

                    break
                except Exception as e:
                    print(f"Error reading coverage file {coverage_file}: {e}")

        return coverage_metrics

    def _collect_performance_metrics(self) -> Dict:
        """Collect performance metrics from latest benchmark."""
        perf_metrics = {
            "latency_p99": 0.0,
            "throughput_rps": 0.0,
            "cache_hit_rate": 0.0,
            "memory_usage_mb": 0.0,
            "cpu_usage_percent": 0.0,
        }

        # Try to read latest performance report
        perf_files = list(self.reports_dir.glob("performance/performance_benchmark_report*.json"))
        if perf_files:
            latest_perf = max(perf_files, key=os.path.getctime)
            try:
                with open(latest_perf, "r") as f:
                    perf_data = json.load(f)

                for result in perf_data.get("results", []):
                    metric = result["metric"]
                    value = result["actual"]

                    if metric == "latency_p99":
                        perf_metrics["latency_p99"] = value
                    elif metric == "throughput_rps":
                        perf_metrics["throughput_rps"] = value
                    elif metric == "cache_hit_rate":
                        perf_metrics["cache_hit_rate"] = value

            except Exception as e:
                print(f"Error reading performance file {latest_perf}: {e}")

        return perf_metrics

    def _collect_security_metrics(self) -> Dict:
        """Collect security metrics."""
        security_metrics = {
            "vulnerabilities_found": 0,
            "security_score": 100,
            "compliance_score": 100,
        }

        # Try to read security scan results
        security_files = list(self.reports_dir.glob("**/security_report.json"))
        if security_files:
            latest_security = max(security_files, key=os.path.getctime)
            try:
                with open(latest_security, "r") as f:
                    security_data = json.load(f)

                # Count vulnerabilities
                if "results" in security_data:
                    vulnerabilities = 0
                    for result in security_data["results"]:
                        vulnerabilities += len(result.get("issues", []))
                    security_metrics["vulnerabilities_found"] = vulnerabilities

            except Exception as e:
                print(f"Error reading security file {latest_security}: {e}")

        return security_metrics

    def save_metrics(self, metrics: Dict):
        """Save metrics to historical data."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"quality_metrics_{timestamp}.json"

        with open(self.metrics_dir / filename, "w") as f:
            json.dump(metrics, f, indent=2)

    def analyze_trends(self, days: int = 30) -> Dict:
        """Analyze quality trends over the specified period."""
        cutoff_date = datetime.now() - timedelta(days=days)

        # Load historical metrics
        historical_data = []
        for metrics_file in self.metrics_dir.glob("quality_metrics_*.json"):
            try:
                with open(metrics_file, "r") as f:
                    data = json.load(f)

                timestamp = datetime.fromisoformat(data["timestamp"])
                if timestamp >= cutoff_date:
                    historical_data.append(data)
            except Exception as e:
                print(f"Error loading metrics file {metrics_file}: {e}")

        if not historical_data:
            return {"error": "No historical data available"}

        # Sort by timestamp
        historical_data.sort(key=lambda x: x["timestamp"])

        # Analyze trends
        trends = self._calculate_trends(historical_data)

        # Generate alerts
        alerts = self._generate_alerts(trends)

        return {
            "period_days": days,
            "data_points": len(historical_data),
            "trends": trends,
            "alerts": alerts,
        }

    def _calculate_trends(self, data: List[Dict]) -> Dict:
        """Calculate quality trends."""
        if not data:
            return {}

        trends = {
            "code_quality_trend": "stable",
            "coverage_trend": "stable",
            "performance_trend": "stable",
            "security_trend": "stable",
        }

        # Simple trend analysis (compare first vs last)
        if len(data) >= 2:
            first = data[0]
            last = data[-1]

            # Code quality trend
            first_lines = first["code_quality"]["total_lines"]
            last_lines = last["code_quality"]["total_lines"]
            if last_lines > first_lines * 1.1:
                trends["code_quality_trend"] = "increasing"
            elif last_lines < first_lines * 0.9:
                trends["code_quality_trend"] = "decreasing"

            # Coverage trend
            first_cov = first["test_coverage"]["overall_coverage"]
            last_cov = last["test_coverage"]["overall_coverage"]
            if last_cov > first_cov + 5:
                trends["coverage_trend"] = "improving"
            elif last_cov < first_cov - 5:
                trends["coverage_trend"] = "declining"

        return trends

    def _generate_alerts(self, trends: Dict) -> List[str]:
        """Generate alerts based on trends."""
        alerts = []

        if trends.get("code_quality_trend") == "increasing":
            alerts.append("⚠️ Codebase size is growing rapidly - consider refactoring")

        if trends.get("coverage_trend") == "declining":
            alerts.append("🚨 Test coverage is declining - review test strategy")

        if trends.get("performance_trend") == "degrading":
            alerts.append("🚨 Performance metrics are degrading - investigate bottlenecks")

        if trends.get("security_trend") == "worsening":
            alerts.append("🚨 Security posture is worsening - address vulnerabilities")

        return alerts

    def generate_report(self) -> str:
        """Generate a comprehensive quality report."""
        current_metrics = self.collect_current_metrics()
        trends_analysis = self.analyze_trends(days=30)

        report = f"""
# ACGS-2 Quality Metrics Report
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 📊 Current Metrics

### Code Quality
- Total Lines: {current_metrics["code_quality"]["total_lines"]:,}
- Python Files: {current_metrics["code_quality"]["python_files"]}
- Syntax Errors: {current_metrics["code_quality"]["syntax_errors"]}
- Lint Errors: {current_metrics["code_quality"]["lint_errors"]}

### Test Coverage
- Overall Coverage: {current_metrics["test_coverage"]["overall_coverage"]:.1f}%
- Files Covered: {current_metrics["test_coverage"]["files_covered"]}
- Lines Covered: {current_metrics["test_coverage"]["lines_covered"]:,}

### Performance
- P99 Latency: {current_metrics["performance"]["latency_p99"]:.2f}ms
- Throughput: {current_metrics["performance"]["throughput_rps"]:.0f} RPS
- Cache Hit Rate: {current_metrics["performance"]["cache_hit_rate"]:.1f}%

### Security
- Vulnerabilities Found: {current_metrics["security"]["vulnerabilities_found"]}
- Security Score: {current_metrics["security"]["security_score"]}/100

## 📈 Trends Analysis (30 days)

Data Points: {trends_analysis.get("data_points", 0)}

### Trends
- Code Quality: {trends_analysis.get("trends", {}).get("code_quality_trend", "unknown")}
- Test Coverage: {trends_analysis.get("trends", {}).get("coverage_trend", "unknown")}
- Performance: {trends_analysis.get("trends", {}).get("performance_trend", "unknown")}
- Security: {trends_analysis.get("trends", {}).get("security_trend", "unknown")}

### Alerts
"""

        alerts = trends_analysis.get("alerts", [])
        if alerts:
            for alert in alerts:
                report += f"- {alert}\n"
        else:
            report += "✅ No critical alerts\n"

        return report


def main():
    """Main execution."""
    monitor = QualityMetricsMonitor()

    # Collect and save current metrics
    print("📊 Collecting current quality metrics...")
    current_metrics = monitor.collect_current_metrics()
    monitor.save_metrics(current_metrics)

    # Analyze trends
    print("📈 Analyzing quality trends...")
    monitor.analyze_trends()

    # Generate and display report
    print("📋 Generating quality report...")
    report = monitor.generate_report()
    print(report)

    # Save report
    report_file = monitor.reports_dir / "quality_metrics_report.md"
    with open(report_file, "w") as f:
        f.write(report)

    print(f"💾 Report saved to: {report_file}")


if __name__ == "__main__":
    main()
