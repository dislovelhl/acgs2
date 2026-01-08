#!/usr/bin/env python3
"""
ACGS-2 Mobile-Responsive Executive Dashboard
Web-based dashboard optimized for mobile devices with executive reporting
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from flask import Flask, jsonify, render_template
from plotly.utils import PlotlyJSONEncoder


class MobileDashboard:
    """Mobile-responsive executive dashboard"""

    def __init__(self, storage_dir: str = "src/claude-flow/claude-flow/storage"):
        self.storage_dir = storage_dir
        self.app = Flask(__name__, template_folder="templates", static_folder="static")
        self.setup_routes()

    def setup_routes(self):
        """Setup Flask routes"""

        @self.app.route("/")
        def dashboard():
            return render_template("dashboard.html")

        @self.app.route("/api/dashboard-data")
        def dashboard_data():
            return jsonify(self.get_dashboard_data())

        @self.app.route("/api/metrics")
        def metrics():
            return jsonify(self.get_key_metrics())

        @self.app.route("/api/charts/<chart_type>")
        def chart_data(chart_type):
            return jsonify(self.generate_chart(chart_type))

        @self.app.route("/api/alerts")
        def alerts():
            return jsonify(self.get_recent_alerts())

        @self.app.route("/api/tasks")
        def tasks():
            return jsonify(self.get_task_status())

        @self.app.route("/api/compliance")
        def compliance():
            return jsonify(self.get_compliance_status())

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""

        # Get current metrics
        metrics = self.get_key_metrics()

        # Get recent activity
        recent_alerts = self.get_recent_alerts()
        active_tasks = self.get_task_status()
        compliance_status = self.get_compliance_status()

        # Generate charts
        charts = {
            "utilization_trend": self.generate_chart("utilization_trend"),
            "task_completion": self.generate_chart("task_completion"),
            "compliance_trend": self.generate_chart("compliance_trend"),
            "agent_performance": self.generate_chart("agent_performance"),
        }

        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics,
            "alerts": recent_alerts,
            "tasks": active_tasks,
            "compliance": compliance_status,
            "charts": charts,
            "system_status": self.get_system_status(),
        }

    def get_key_metrics(self) -> Dict[str, Any]:
        """Get key performance metrics for dashboard"""

        # Load current system state
        agents = self._load_agents()
        tasks = self._load_tasks()

        # Calculate metrics
        total_agents = len(agents)
        active_agents = len([a for a in agents if a.get("status") == "active"])
        busy_agents = len([a for a in agents if a.get("status") == "busy"])

        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.get("status") == "completed"])
        in_progress_tasks = len([t for t in tasks if t.get("status") == "in-progress"])
        failed_tasks = len([t for t in tasks if t.get("status") == "failed"])

        # Success rate
        success_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        # Utilization
        utilization = (busy_agents / total_agents * 100) if total_agents > 0 else 0

        return {
            "agents": {
                "total": total_agents,
                "active": active_agents,
                "busy": busy_agents,
                "utilization": round(utilization, 1),
            },
            "tasks": {
                "total": total_tasks,
                "completed": completed_tasks,
                "in_progress": in_progress_tasks,
                "failed": failed_tasks,
                "success_rate": round(success_rate, 1),
            },
            "system_health": {
                "overall_score": 85,  # Would be calculated
                "status": "healthy" if utilization < 80 else "warning",
            },
        }

    def generate_chart(self, chart_type: str) -> Dict[str, Any]:
        """Generate interactive charts for mobile dashboard"""

        if chart_type == "utilization_trend":
            # Create utilization trend chart
            dates = pd.date_range(end=datetime.now(), periods=24, freq="H")
            utilization = [60 + np.random.normal(0, 10) for _ in range(24)]  # Sample data

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=utilization,
                    mode="lines+markers",
                    name="Agent Utilization",
                    line=dict(color="#17a2b8", width=2),
                )
            )

            fig.update_layout(
                title="Agent Utilization Trend (24h)",
                xaxis_title="Time",
                yaxis_title="Utilization %",
                margin=dict(l=20, r=20, t=40, b=20),
                height=300,
            )

        elif chart_type == "task_completion":
            # Task completion status
            labels = ["Completed", "In Progress", "Pending", "Failed"]
            values = [45, 12, 8, 2]  # Sample data
            colors = ["#28a745", "#ffc107", "#17a2b8", "#dc3545"]

            fig = go.Figure(
                data=[
                    go.Pie(
                        labels=labels,
                        values=values,
                        marker_colors=colors,
                        title="Task Status Distribution",
                    )
                ]
            )

            fig.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=300)

        elif chart_type == "compliance_trend":
            # Compliance trend
            dates = pd.date_range(end=datetime.now(), periods=30, freq="D")
            compliance = [85 + np.random.normal(0, 5) for _ in range(30)]

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=compliance,
                    fill="tozeroy",
                    name="Compliance Score",
                    line=dict(color="#28a745"),
                )
            )

            fig.update_layout(
                title="Compliance Trend (30 days)",
                xaxis_title="Date",
                yaxis_title="Compliance %",
                margin=dict(l=20, r=20, t=40, b=20),
                height=300,
            )

        elif chart_type == "agent_performance":
            # Agent performance bar chart
            agents = ["Coder-1", "Coder-2", "Tester-1", "Tester-2", "Coordinator"]
            tasks_completed = [25, 22, 18, 20, 15]

            fig = go.Figure()
            fig.add_trace(
                go.Bar(x=agents, y=tasks_completed, marker_color="#17a2b8", name="Tasks Completed")
            )

            fig.update_layout(
                title="Agent Performance",
                xaxis_title="Agent",
                yaxis_title="Tasks Completed",
                margin=dict(l=20, r=20, t=40, b=20),
                height=300,
            )

        else:
            return {"error": f"Unknown chart type: {chart_type}"}

        # Convert to JSON for mobile rendering
        return json.loads(json.dumps(fig, cls=PlotlyJSONEncoder))

    def get_recent_alerts(self) -> List[Dict[str, Any]]:
        """Get recent alerts for dashboard"""

        # In production, this would load from alert storage
        alerts = [
            {
                "id": "alert-001",
                "timestamp": (datetime.now() - timedelta(minutes=15)).isoformat(),
                "severity": "medium",
                "type": "utilization_warning",
                "message": "Agent utilization above 80%",
                "acknowledged": False,
            },
            {
                "id": "alert-002",
                "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
                "severity": "low",
                "type": "task_completed",
                "message": "Authentication system implementation completed",
                "acknowledged": True,
            },
        ]

        return alerts

    def get_task_status(self) -> Dict[str, Any]:
        """Get current task status"""

        tasks = self._load_tasks()

        active_tasks = []
        for task in tasks:
            if task.get("status") in ["in_progress", "pending"]:
                active_tasks.append(
                    {
                        "id": task.get("id"),
                        "task": task.get("task"),
                        "status": task.get("status"),
                        "priority": task.get("priority", "medium"),
                        "assigned_agent": task.get("assigned_agent"),
                        "progress": task.get("progress", 0),
                    }
                )

        return {
            "active_count": len(active_tasks),
            "tasks": active_tasks[:5],  # Show top 5
        }

    def get_compliance_status(self) -> Dict[str, Any]:
        """Get compliance status"""

        return {
            "overall_score": 88,
            "trend": "improving",
            "checks": {
                "security_clearance": {"status": "passed", "score": 90},
                "data_privacy": {"status": "warning", "score": 75},
                "regulatory_compliance": {"status": "passed", "score": 95},
                "resource_limits": {"status": "passed", "score": 85},
                "audit_trail": {"status": "warning", "score": 78},
            },
            "last_audit": (datetime.now() - timedelta(days=7)).isoformat(),
        }

    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""

        return {
            "status": "operational",
            "uptime": "99.9%",
            "last_incident": (datetime.now() - timedelta(days=30)).isoformat(),
            "active_integrations": 5,
            "data_freshness": "real-time",
        }

    def _load_agents(self) -> List[Dict[str, Any]]:
        """Load agents from storage"""
        agents = []
        for filename in os.listdir(self.storage_dir):
            if filename.startswith("agent_") and filename.endswith(".json"):
                try:
                    with open(os.path.join(self.storage_dir, filename), "r") as f:
                        agents.append(json.load(f))
                except Exception:
                    pass
        return agents

    def _load_tasks(self) -> List[Dict[str, Any]]:
        """Load tasks from storage"""
        tasks = []
        for filename in os.listdir(self.storage_dir):
            if filename.startswith("task_") and filename.endswith(".json"):
                try:
                    with open(os.path.join(self.storage_dir, filename), "r") as f:
                        tasks.append(json.load(f))
                except Exception:
                    pass
        return tasks

    def _load_swarms(self) -> List[Dict[str, Any]]:
        """Load swarms from storage"""
        swarms = []
        for filename in os.listdir(self.storage_dir):
            if filename.startswith("swarm_") and filename.endswith(".json"):
                try:
                    with open(os.path.join(self.storage_dir, filename), "r") as f:
                        swarms.append(json.load(f))
                except Exception:
                    pass
        return swarms

    def run(self, host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
        """Run the dashboard server"""

        self.app.run(host=host, port=port, debug=debug)


# HTML template for mobile dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ACGS-2 Executive Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .mobile-card {
            @apply bg-white rounded-lg shadow-md p-4 m-2;
        }
        .metric-large {
            @apply text-3xl font-bold text-gray-800;
        }
        .metric-label {
            @apply text-sm text-gray-600 uppercase tracking-wide;
        }
        .status-healthy {
            @apply bg-green-100 text-green-800;
        }
        .status-warning {
            @apply bg-yellow-100 text-yellow-800;
        }
        .status-critical {
            @apply bg-red-100 text-red-800;
        }
    </style>
</head>
<body class="bg-gray-100 min-h-screen">
    <div class="container mx-auto px-4 py-6 max-w-md">
        <!-- Header -->
        <div class="mobile-card">
            <h1 class="text-xl font-bold text-gray-800 mb-2">ACGS-2 Executive Dashboard</h1>
            <p class="text-sm text-gray-600" id="last-updated">Loading...</p>
        </div>

        <!-- Key Metrics -->
        <div class="mobile-card">
            <h2 class="text-lg font-semibold mb-3">Key Metrics</h2>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <div class="metric-large" id="agent-utilization">0%</div>
                    <div class="metric-label">Agent Utilization</div>
                </div>
                <div>
                    <div class="metric-large" id="task-success">0%</div>
                    <div class="metric-label">Task Success Rate</div>
                </div>
                <div>
                    <div class="metric-large" id="total-agents">0</div>
                    <div class="metric-label">Total Agents</div>
                </div>
                <div>
                    <div class="metric-large" id="active-tasks">0</div>
                    <div class="metric-label">Active Tasks</div>
                </div>
            </div>
        </div>

        <!-- System Status -->
        <div class="mobile-card">
            <h2 class="text-lg font-semibold mb-3">System Status</h2>
            <div class="flex items-center justify-between">
                <span class="text-gray-700">Overall Health</span>
                <span class="px-2 py-1 rounded-full text-xs font-medium" id="system-status">Unknown</span>
            </div>
            <div class="mt-2">
                <div class="w-full bg-gray-200 rounded-full h-2">
                    <div class="bg-green-600 h-2 rounded-full" id="health-bar" style="width: 0%"></div>
                </div>
            </div>
        </div>

        <!-- Charts -->
        <div class="mobile-card">
            <h2 class="text-lg font-semibold mb-3">Utilization Trend</h2>
            <div id="utilization-chart" class="w-full h-64"></div>
        </div>

        <div class="mobile-card">
            <h2 class="text-lg font-semibold mb-3">Task Status</h2>
            <div id="task-chart" class="w-full h-64"></div>
        </div>

        <!-- Active Alerts -->
        <div class="mobile-card">
            <h2 class="text-lg font-semibold mb-3">Active Alerts</h2>
            <div id="alerts-list" class="space-y-2">
                <p class="text-gray-500 text-sm">Loading alerts...</p>
            </div>
        </div>

        <!-- Active Tasks -->
        <div class="mobile-card">
            <h2 class="text-lg font-semibold mb-3">Active Tasks</h2>
            <div id="tasks-list" class="space-y-2">
                <p class="text-gray-500 text-sm">Loading tasks...</p>
            </div>
        </div>
    </div>

    <script>
        // Auto-refresh data every 30 seconds
        let dashboardData = {};

        async function loadDashboardData() {
            try {
                const response = await fetch('/api/dashboard-data');
                dashboardData = await response.json();
                updateDashboard();
            } catch (error) {
                console.error('Failed to load dashboard data:', error);
            }
        }

        function updateDashboard() {
            // Update timestamp
            document.getElementById('last-updated').textContent =
                `Last updated: ${new Date(dashboardData.timestamp).toLocaleTimeString()}`;

            // Update key metrics
            const metrics = dashboardData.metrics;
            document.getElementById('agent-utilization').textContent =
                `${metrics.agents.utilization}%`;
            document.getElementById('task-success').textContent =
                `${metrics.tasks.success_rate}%`;
            document.getElementById('total-agents').textContent =
                metrics.agents.total;
            document.getElementById('active-tasks').textContent =
                metrics.tasks.in_progress;

            // Update system status
            const health = metrics.system_health;
            const statusEl = document.getElementById('system-status');
            const healthBar = document.getElementById('health-bar');

            statusEl.className = 'px-2 py-1 rounded-full text-xs font-medium';
            if (health.status === 'healthy') {
                statusEl.classList.add('status-healthy');
                statusEl.textContent = 'Healthy';
            } else if (health.status === 'warning') {
                statusEl.classList.add('status-warning');
                statusEl.textContent = 'Warning';
            } else {
                statusEl.classList.add('status-critical');
                statusEl.textContent = 'Critical';
            }

            healthBar.style.width = `${health.overall_score}%`;

            // Update charts
            updateCharts();

            // Update alerts
            updateAlerts();

            // Update tasks
            updateTasks();
        }

        function updateCharts() {
            // Utilization trend chart
            if (dashboardData.charts && dashboardData.charts.utilization_trend) {
                Plotly.newPlot('utilization-chart',
                    dashboardData.charts.utilization_trend.data,
                    dashboardData.charts.utilization_trend.layout,
                    {responsive: true});
            }

            // Task status chart
            if (dashboardData.charts && dashboardData.charts.task_completion) {
                Plotly.newPlot('task-chart',
                    dashboardData.charts.task_completion.data,
                    dashboardData.charts.task_completion.layout,
                    {responsive: true});
            }
        }

        function updateAlerts() {
            const alertsList = document.getElementById('alerts-list');
            const alerts = dashboardData.alerts || [];

            if (alerts.length === 0) {
                alertsList.innerHTML = '<p class="text-gray-500 text-sm">No active alerts</p>';
                return;
            }

            alertsList.innerHTML = alerts.map(alert => `
                <div class="flex items-center justify-between p-2 rounded ${
                    alert.severity === 'critical' ? 'bg-red-50' :
                    alert.severity === 'high' ? 'bg-orange-50' :
                    alert.severity === 'medium' ? 'bg-yellow-50' : 'bg-blue-50'
                }">
                    <div>
                        <p class="text-sm font-medium">${alert.message}</p>
                        <p class="text-xs text-gray-600">${new Date(alert.timestamp).toLocaleTimeString()}</p>
                    </div>
                    <span class="text-xs px-2 py-1 rounded ${
                        alert.severity === 'critical' ? 'bg-red-200 text-red-800' :
                        alert.severity === 'high' ? 'bg-orange-200 text-orange-800' :
                        alert.severity === 'medium' ? 'bg-yellow-200 text-yellow-800' :
                        'bg-blue-200 text-blue-800'
                    }">${alert.severity}</span>
                </div>
            `).join('');
        }

        function updateTasks() {
            const tasksList = document.getElementById('tasks-list');
            const tasks = (dashboardData.tasks && dashboardData.tasks.tasks) || [];

            if (tasks.length === 0) {
                tasksList.innerHTML = '<p class="text-gray-500 text-sm">No active tasks</p>';
                return;
            }

            tasksList.innerHTML = tasks.map(task => `
                <div class="p-2 border rounded">
                    <div class="flex items-center justify-between">
                        <p class="text-sm font-medium">${task.task}</p>
                        <span class="text-xs px-2 py-1 rounded ${
                            task.priority === 'critical' ? 'bg-red-200 text-red-800' :
                            task.priority === 'high' ? 'bg-orange-200 text-orange-800' :
                            task.priority === 'medium' ? 'bg-yellow-200 text-yellow-800' :
                            'bg-blue-200 text-blue-800'
                        }">${task.priority}</span>
                    </div>
                    <div class="mt-1">
                        <div class="w-full bg-gray-200 rounded-full h-1">
                            <div class="bg-blue-600 h-1 rounded-full" style="width: ${task.progress}%"></div>
                        </div>
                        <p class="text-xs text-gray-600 mt-1">${task.progress}% complete</p>
                    </div>
                </div>
            `).join('');
        }

        // Load data on page load and refresh every 30 seconds
        loadDashboardData();
        setInterval(loadDashboardData, 30000);
    </script>
</body>
</html>
"""


def create_dashboard_template():
    """Create the dashboard HTML template"""

    # Create templates directory
    os.makedirs("templates", exist_ok=True)

    with open("templates/dashboard.html", "w") as f:
        f.write(DASHBOARD_HTML)


def main():
    """Main entry point for mobile dashboard"""

    import sys

    # Create template
    create_dashboard_template()

    # Initialize dashboard
    dashboard = MobileDashboard()

    if len(sys.argv) > 1 and sys.argv[1] == "--server":
        # Run as web server
        host = sys.argv[2] if len(sys.argv) > 2 else "0.0.0.0"
        port = int(sys.argv[3]) if len(sys.argv) > 3 else 5000
        dashboard.run(host=host, port=port, debug=True)
    else:
        # Run data API demo
        dashboard.get_dashboard_data()


if __name__ == "__main__":
    main()
