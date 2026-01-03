#!/usr/bin/env python3
"""
ACGS-2 Quality Dashboard Generator
Creates interactive dashboards for quality metrics visualization
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import pandas as pd


class QualityDashboardGenerator:
    """Generate interactive quality dashboards."""

    def __init__(self, reports_dir: str = "reports"):
        self.reports_dir = Path(reports_dir)
        self.dashboard_dir = self.reports_dir / "dashboard"
        self.dashboard_dir.mkdir(exist_ok=True)

    def generate_dashboard(self):
        """Generate comprehensive quality dashboard."""
        print("📊 Generating ACGS-2 Quality Dashboard...")

        # Load historical metrics
        metrics_data = self._load_historical_metrics()

        if not metrics_data:
            print("⚠️ No historical metrics data found")
            return

        # Create dashboard components
        self._create_overview_dashboard(metrics_data)
        self._create_trends_dashboard(metrics_data)
        self._create_alerts_dashboard(metrics_data)

        # Generate HTML dashboard
        self._create_html_dashboard(metrics_data)

        print("✅ Quality dashboard generated successfully!")
        print(f"📁 Dashboard files saved to: {self.dashboard_dir}")

    def _load_historical_metrics(self) -> pd.DataFrame:
        """Load and process historical metrics data."""
        metrics_files = list((self.reports_dir / "metrics").glob("quality_metrics_*.json"))

        if not metrics_files:
            return pd.DataFrame()

        data = []
        for metrics_file in sorted(metrics_files):
            try:
                with open(metrics_file, "r") as f:
                    metrics = json.load(f)

                # Flatten nested structure
                row = {
                    "timestamp": pd.to_datetime(metrics["timestamp"]),
                    "total_lines": metrics["code_quality"]["total_lines"],
                    "python_files": metrics["code_quality"]["python_files"],
                    "syntax_errors": metrics["code_quality"]["syntax_errors"],
                    "lint_errors": metrics["code_quality"]["lint_errors"],
                    "overall_coverage": metrics["test_coverage"]["overall_coverage"],
                    "latency_p99": metrics["performance"]["latency_p99"],
                    "throughput_rps": metrics["performance"]["throughput_rps"],
                    "cache_hit_rate": metrics["performance"]["cache_hit_rate"],
                    "vulnerabilities": metrics["security"]["vulnerabilities_found"],
                    "security_score": metrics["security"]["security_score"],
                }
                data.append(row)

            except Exception as e:
                print(f"Error loading {metrics_file}: {e}")

        return pd.DataFrame(data)

    def _create_overview_dashboard(self, df: pd.DataFrame):
        """Create overview dashboard with current metrics."""
        if df.empty:
            return

        latest = df.iloc[-1]

        # Create overview figure
        fig = make_subplots(
            rows=2,
            cols=3,
            subplot_titles=(
                "Code Quality Metrics",
                "Test Coverage",
                "Performance Metrics",
                "Security Metrics",
                "Trends Overview",
                "Quality Score",
            ),
            specs=[
                [{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}],
                [{"type": "indicator"}, {"type": "bar"}, {"type": "indicator"}],
            ],
        )

        # Code Quality
        fig.add_trace(
            go.Indicator(
                mode="number",
                value=latest["total_lines"],
                title={"text": "Total Lines"},
                number={"font": {"size": 40}},
            ),
            row=1,
            col=1,
        )

        # Test Coverage
        fig.add_trace(
            go.Indicator(
                mode="number+gauge",
                value=latest["overall_coverage"],
                title={"text": "Test Coverage %"},
                gauge={"axis": {"range": [0, 100]}, "bar": {"color": "green"}},
                number={"font": {"size": 40}},
            ),
            row=1,
            col=2,
        )

        # Performance
        fig.add_trace(
            go.Indicator(
                mode="number+delta",
                value=latest["latency_p99"],
                title={"text": "P99 Latency (ms)"},
                delta={"reference": 0.328},
                number={"font": {"size": 30}},
            ),
            row=1,
            col=3,
        )

        # Security
        fig.add_trace(
            go.Indicator(
                mode="number",
                value=latest["vulnerabilities"],
                title={"text": "Security Vulnerabilities"},
                number={
                    "font": {
                        "size": 40,
                        "color": "red" if latest["vulnerabilities"] > 0 else "green",
                    }
                },
            ),
            row=2,
            col=1,
        )

        # Trends
        recent_trends = df.tail(7)  # Last 7 data points
        trend_data = [
            ("Coverage", recent_trends["overall_coverage"].pct_change().mean() * 100),
            ("Performance", recent_trends["latency_p99"].pct_change().mean() * 100),
            ("Security", recent_trends["vulnerabilities"].pct_change().mean() * 100),
        ]

        fig.add_trace(
            go.Bar(
                x=[t[0] for t in trend_data],
                y=[t[1] for t in trend_data],
                marker_color=["green" if t[1] >= 0 else "red" for t in trend_data],
            ),
            row=2,
            col=2,
        )

        # Overall Quality Score
        quality_score = self._calculate_quality_score(latest)
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=quality_score,
                title={"text": "Quality Score"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {
                        "color": "green"
                        if quality_score > 80
                        else "orange"
                        if quality_score > 60
                        else "red"
                    },
                    "steps": [
                        {"range": [0, 60], "color": "red"},
                        {"range": [60, 80], "color": "orange"},
                        {"range": [80, 100], "color": "green"},
                    ],
                },
                number={"font": {"size": 40}},
            ),
            row=2,
            col=3,
        )

        fig.update_layout(height=800, title_text="ACGS-2 Quality Overview Dashboard")
        fig.write_html(self.dashboard_dir / "overview_dashboard.html")

    def _create_trends_dashboard(self, df: pd.DataFrame):
        """Create trends dashboard showing historical data."""
        if df.empty or len(df) < 2:
            return

        fig = make_subplots(
            rows=3,
            cols=2,
            subplot_titles=(
                "Test Coverage Trend",
                "Performance Trend",
                "Code Size Trend",
                "Security Vulnerabilities",
                "Throughput Trend",
                "Quality Score Trend",
            ),
        )

        # Test Coverage Trend
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=df["overall_coverage"],
                mode="lines+markers",
                name="Coverage %",
                line=dict(color="green"),
            ),
            row=1,
            col=1,
        )

        # Performance Trend
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=df["latency_p99"],
                mode="lines+markers",
                name="P99 Latency (ms)",
                line=dict(color="blue"),
            ),
            row=1,
            col=2,
        )

        # Code Size Trend
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=df["total_lines"],
                mode="lines+markers",
                name="Total Lines",
                line=dict(color="orange"),
            ),
            row=2,
            col=1,
        )

        # Security Vulnerabilities
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=df["vulnerabilities"],
                mode="lines+markers",
                name="Vulnerabilities",
                line=dict(color="red"),
            ),
            row=2,
            col=2,
        )

        # Throughput Trend
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=df["throughput_rps"],
                mode="lines+markers",
                name="Throughput (RPS)",
                line=dict(color="purple"),
            ),
            row=3,
            col=1,
        )

        # Quality Score Trend
        quality_scores = [self._calculate_quality_score(row) for _, row in df.iterrows()]
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=quality_scores,
                mode="lines+markers",
                name="Quality Score",
                line=dict(color="green"),
            ),
            row=3,
            col=2,
        )

        fig.update_layout(height=1200, title_text="ACGS-2 Quality Trends Dashboard")
        fig.write_html(self.dashboard_dir / "trends_dashboard.html")

    def _create_alerts_dashboard(self, df: pd.DataFrame):
        """Create alerts dashboard."""
        alerts = self._analyze_alerts(df)

        if not alerts:
            return

        # Create alerts summary
        alert_summary = {
            "Critical": len([a for a in alerts if "🚨" in a]),
            "Warning": len([a for a in alerts if "⚠️" in a]),
            "Info": len([a for a in alerts if "ℹ️" in a]),
        }

        fig = make_subplots(
            rows=1,
            cols=2,
            subplot_titles=("Alert Summary", "Recent Alerts"),
            specs=[[{"type": "pie"}, {"type": "table"}]],
        )

        # Alert summary pie chart
        fig.add_trace(
            go.Pie(
                labels=list(alert_summary.keys()),
                values=list(alert_summary.values()),
                marker_colors=["red", "orange", "blue"],
            ),
            row=1,
            col=1,
        )

        # Recent alerts table
        recent_alerts = alerts[-10:]  # Last 10 alerts
        fig.add_trace(
            go.Table(
                header=dict(values=["Alert Type", "Message", "Timestamp"]),
                cells=dict(
                    values=[
                        [a.split()[0] for a in recent_alerts],
                        [" ".join(a.split()[1:]) for a in recent_alerts],
                        [datetime.now().strftime("%Y-%m-%d %H:%M") for _ in recent_alerts],
                    ]
                ),
            ),
            row=1,
            col=2,
        )

        fig.update_layout(height=600, title_text="ACGS-2 Quality Alerts Dashboard")
        fig.write_html(self.dashboard_dir / "alerts_dashboard.html")

    def _analyze_alerts(self, df: pd.DataFrame) -> list:
        """Analyze data and generate alerts."""
        if df.empty:
            return []

        alerts = []
        latest = df.iloc[-1]

        # Coverage alerts
        if latest["overall_coverage"] < 80:
            alerts.append("🚨 Test coverage below 80%")
        elif latest["overall_coverage"] < 90:
            alerts.append("⚠️ Test coverage below 90%")

        # Performance alerts
        if latest["latency_p99"] > 0.5:
            alerts.append("🚨 P99 latency above 0.5ms")
        elif latest["latency_p99"] > 0.328:
            alerts.append("⚠️ P99 latency above target")

        # Security alerts
        if latest["vulnerabilities"] > 0:
            alerts.append(f"🚨 {latest['vulnerabilities']} security vulnerabilities found")

        # Code quality alerts
        if latest["syntax_errors"] > 0:
            alerts.append(f"🚨 {latest['syntax_errors']} syntax errors found")

        if latest["lint_errors"] > 10:
            alerts.append("⚠️ High number of lint errors")

        return alerts

    def _calculate_quality_score(self, metrics) -> float:
        """Calculate overall quality score."""
        score = 100

        # Coverage impact
        if metrics["overall_coverage"] < 80:
            score -= 20
        elif metrics["overall_coverage"] < 90:
            score -= 10

        # Performance impact
        if metrics["latency_p99"] > 0.5:
            score -= 15
        elif metrics["latency_p99"] > 0.328:
            score -= 5

        # Security impact
        score -= min(metrics["vulnerabilities"] * 5, 30)

        # Code quality impact
        score -= min(metrics["syntax_errors"] * 2, 10)
        score -= min(metrics["lint_errors"] // 10, 15)

        return max(0, min(100, score))

    def _create_html_dashboard(self, df: pd.DataFrame):
        """Create comprehensive HTML dashboard."""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>ACGS-2 Quality Dashboard</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .dashboard-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }}
        .metric-label {{
            color: #666;
            font-size: 0.9em;
        }}
        .status-good {{ color: #28a745; }}
        .status-warning {{ color: #ffc107; }}
        .status-danger {{ color: #dc3545; }}
        iframe {{
            width: 100%;
            height: 400px;
            border: none;
            border-radius: 10px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 ACGS-2 Quality Dashboard</h1>
        <p>Comprehensive quality metrics and monitoring</p>
        <p>Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>

    <div class="dashboard-grid">
"""

        if not df.empty:
            latest = df.iloc[-1]

            # Add metric cards
            metrics = [
                (
                    "Test Coverage",
                    f"{latest['overall_coverage']:.1f}%",
                    "good" if latest["overall_coverage"] > 90 else "warning",
                ),
                (
                    "P99 Latency",
                    f"{latest['latency_p99']:.2f}ms",
                    "good" if latest["latency_p99"] < 0.328 else "warning",
                ),
                ("Throughput", f"{latest['throughput_rps']:.0f} RPS", "good"),
                (
                    "Vulnerabilities",
                    str(latest["vulnerabilities"]),
                    "danger" if latest["vulnerabilities"] > 0 else "good",
                ),
                ("Total Lines", f"{latest['total_lines']:,}", "neutral"),
                (
                    "Quality Score",
                    f"{self._calculate_quality_score(latest):.0f}/100",
                    "good" if self._calculate_quality_score(latest) > 80 else "warning",
                ),
            ]

            for label, value, status in metrics:
                html_content += f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value status-{status}">{value}</div>
        </div>
"""

        html_content += """
    </div>

    <h2>📊 Detailed Dashboards</h2>
    <div class="dashboard-grid">
        <div class="metric-card">
            <h3>Overview Dashboard</h3>
            <iframe src="overview_dashboard.html"></iframe>
        </div>
        <div class="metric-card">
            <h3>Trends Dashboard</h3>
            <iframe src="trends_dashboard.html"></iframe>
        </div>
        <div class="metric-card">
            <h3>Alerts Dashboard</h3>
            <iframe src="alerts_dashboard.html"></iframe>
        </div>
    </div>

    <div class="metric-card">
        <h2>🚨 Active Alerts</h2>
"""

        alerts = self._analyze_alerts(df)
        if alerts:
            for alert in alerts:
                html_content += f"<p>{alert}</p>"
        else:
            html_content += "<p>✅ No active alerts</p>"

        html_content += """
    </div>
</body>
</html>
"""

        with open(self.dashboard_dir / "index.html", "w") as f:
            f.write(html_content)


def main():
    """Main execution."""
    generator = QualityDashboardGenerator()

    try:
        generator.generate_dashboard()
        print("🎉 Quality dashboard generated successfully!")
        print(f"📂 Open {generator.dashboard_dir}/index.html in your browser")

    except ImportError as e:
        print(f"⚠️ Plotly not available: {e}")
        print("Install with: pip install plotly pandas")
    except Exception as e:
        print(f"❌ Error generating dashboard: {e}")


if __name__ == "__main__":
    main()
