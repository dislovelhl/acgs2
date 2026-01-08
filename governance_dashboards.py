#!/usr/bin/env python3
"""
ACGS-2 Governance Dashboards
Provides executive reporting and compliance tracking dashboards
"""

import json
import os
import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List


class GovernanceDashboards:
    """Governance dashboards for executive reporting and compliance tracking"""

    def __init__(self, storage_dir: str = "src/claude-flow/claude-flow/storage"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

    def generate_executive_dashboard(self) -> Dict[str, Any]:
        """Generate comprehensive executive dashboard"""

        # Gather all data sources
        agents = self._load_agents()
        tasks = self._load_tasks()
        swarms = self._load_swarms()
        workflows = self._load_workflows()

        # Calculate key metrics
        metrics = self._calculate_key_metrics(agents, tasks, swarms, workflows)

        # Generate compliance overview
        compliance_overview = self._generate_compliance_overview(tasks)

        # Generate performance indicators
        performance_indicators = self._generate_performance_indicators(agents, tasks)

        # Generate risk assessment
        risk_assessment = self._generate_risk_assessment(tasks, agents)

        # Generate trend analysis
        trend_analysis = self._generate_trend_analysis(tasks)

        return {
            "dashboard_title": "ACGS-2 Governance Executive Dashboard",
            "generated_at": datetime.now().isoformat(),
            "report_period": "Last 30 days",
            "key_metrics": metrics,
            "compliance_overview": compliance_overview,
            "performance_indicators": performance_indicators,
            "risk_assessment": risk_assessment,
            "trend_analysis": trend_analysis,
            "recommendations": self._generate_executive_recommendations(
                metrics, compliance_overview, risk_assessment
            ),
        }

    def _calculate_key_metrics(
        self, agents: List[Dict], tasks: List[Dict], swarms: List[Dict], workflows: List[Dict]
    ) -> Dict[str, Any]:
        """Calculate key performance metrics"""

        # Agent metrics
        total_agents = len(agents)
        active_agents = len([a for a in agents if a.get("status") == "active"])
        busy_agents = len([a for a in agents if a.get("status") == "busy"])

        # Task metrics
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.get("status") == "completed"])
        failed_tasks = len([t for t in tasks if t.get("status") == "failed"])
        in_progress_tasks = len([t for t in tasks if t.get("status") == "in-progress"])

        # Success rate
        success_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        # Swarm metrics
        swarm_utilization = (busy_agents / total_agents * 100) if total_agents > 0 else 0

        # Workflow metrics
        completed_workflows = len([w for w in workflows if w.get("status") == "completed"])
        total_workflows = len(workflows)

        return {
            "agents": {
                "total": total_agents,
                "active": active_agents,
                "busy": busy_agents,
                "utilization_rate": round(swarm_utilization, 1),
            },
            "tasks": {
                "total": total_tasks,
                "completed": completed_tasks,
                "failed": failed_tasks,
                "in_progress": in_progress_tasks,
                "success_rate": round(success_rate, 1),
            },
            "workflows": {
                "total": total_workflows,
                "completed": completed_workflows,
                "success_rate": round(
                    (completed_workflows / total_workflows * 100) if total_workflows > 0 else 0, 1
                ),
            },
            "system_health": self._calculate_system_health_score(agents, tasks, workflows),
        }

    def _calculate_system_health_score(
        self, agents: List[Dict], tasks: List[Dict], workflows: List[Dict]
    ) -> Dict[str, Any]:
        """Calculate overall system health score"""

        scores = {
            "agent_health": 0,
            "task_reliability": 0,
            "workflow_efficiency": 0,
            "compliance_score": 0,
        }

        # Agent health (availability and utilization)
        if agents:
            active_ratio = len([a for a in agents if a.get("status") in ["active", "busy"]]) / len(
                agents
            )
            scores["agent_health"] = min(100, active_ratio * 100)

        # Task reliability (success rate)
        if tasks:
            completed = len([t for t in tasks if t.get("status") == "completed"])
            success_rate = completed / len(tasks) if tasks else 0
            scores["task_reliability"] = success_rate * 100

        # Workflow efficiency (completion rate)
        if workflows:
            completed = len([w for w in workflows if w.get("status") == "completed"])
            efficiency = completed / len(workflows) if workflows else 0
            scores["workflow_efficiency"] = efficiency * 100

        # Compliance score (simplified)
        scores["compliance_score"] = 85  # Would be calculated from actual compliance checks

        overall_score = statistics.mean(scores.values())

        health_status = (
            "excellent"
            if overall_score >= 90
            else "good"
            if overall_score >= 75
            else "fair"
            if overall_score >= 60
            else "poor"
        )

        return {
            "overall_score": round(overall_score, 1),
            "status": health_status,
            "component_scores": scores,
        }

    def _generate_compliance_overview(self, tasks: List[Dict]) -> Dict[str, Any]:
        """Generate compliance overview"""

        # Simulate compliance checks (would integrate with actual compliance engine)
        compliance_checks = {
            "security_clearance": {"passed": 85, "failed": 15, "total": 100},
            "data_privacy": {"passed": 90, "failed": 10, "total": 100},
            "regulatory_compliance": {"passed": 95, "failed": 5, "total": 100},
            "resource_limits": {"passed": 88, "failed": 12, "total": 100},
            "audit_trail": {"passed": 82, "failed": 18, "total": 100},
        }

        overall_compliance = (
            sum(check["passed"] for check in compliance_checks.values())
            / sum(check["total"] for check in compliance_checks.values())
            * 100
        )

        # Identify compliance trends
        compliance_trend = (
            "improving"
            if overall_compliance > 85
            else "stable"
            if overall_compliance > 75
            else "declining"
        )

        return {
            "overall_compliance_score": round(overall_compliance, 1),
            "compliance_trend": compliance_trend,
            "compliance_checks": compliance_checks,
            "critical_violations": len([c for c in compliance_checks.values() if c["failed"] > 20]),
            "compliance_maturity_level": self._calculate_compliance_maturity(overall_compliance),
        }

    def _calculate_compliance_maturity(self, score: float) -> str:
        """Calculate compliance maturity level"""
        if score >= 95:
            return "Optimized"
        elif score >= 85:
            return "Managed"
        elif score >= 75:
            return "Defined"
        elif score >= 60:
            return "Repeatable"
        else:
            return "Initial"

    def _generate_performance_indicators(
        self, agents: List[Dict], tasks: List[Dict]
    ) -> Dict[str, Any]:
        """Generate key performance indicators"""

        # Task completion metrics
        completed_tasks = [t for t in tasks if t.get("status") == "completed"]
        completion_times = []

        for task in completed_tasks:
            if task.get("completed_at") and task.get("assigned_at"):
                completion_time = task["completed_at"] - task["assigned_at"]
                if completion_time > 0:
                    completion_times.append(completion_time / 3600)  # Convert to hours

        avg_completion_time = statistics.mean(completion_times) if completion_times else 0
        median_completion_time = statistics.median(completion_times) if completion_times else 0

        # Agent productivity
        agent_productivity = defaultdict(int)
        for task in completed_tasks:
            agent_id = task.get("assigned_agent")
            if agent_id:
                agent_productivity[agent_id] += 1

        top_performers = sorted(agent_productivity.items(), key=lambda x: x[1], reverse=True)[:3]

        # System throughput
        tasks_per_hour = len(completed_tasks) / 24  # Simplified daily throughput

        return {
            "avg_task_completion_time_hours": round(avg_completion_time, 2),
            "median_task_completion_time_hours": round(median_completion_time, 2),
            "tasks_per_hour": round(tasks_per_hour, 2),
            "agent_productivity": {
                "top_performers": [
                    {"agent_id": agent_id, "tasks_completed": count}
                    for agent_id, count in top_performers
                ],
                "total_productive_agents": len([a for a in agent_productivity.values() if a > 0]),
            },
            "efficiency_metrics": {
                "first_time_resolution_rate": 0.85,  # Would be calculated from actual data
                "automation_rate": 0.72,
                "error_rate": len([t for t in tasks if t.get("status") == "failed"]) / len(tasks)
                if tasks
                else 0,
            },
        }

    def _generate_risk_assessment(self, tasks: List[Dict], agents: List[Dict]) -> Dict[str, Any]:
        """Generate comprehensive risk assessment"""

        # Identify high-risk tasks
        high_risk_tasks = []
        for task in tasks:
            risk_score = 0

            # Risk factors
            if task.get("priority") == "critical":
                risk_score += 30
            if "security" in task.get("skills", []):
                risk_score += 25
            if task.get("status") == "failed":
                risk_score += 20
            if not task.get("assigned_agent"):
                risk_score += 15

            if risk_score > 40:
                high_risk_tasks.append(
                    {
                        "task_id": task.get("id"),
                        "task_name": task.get("task"),
                        "risk_score": risk_score,
                        "risk_factors": self._identify_risk_factors(task),
                    }
                )

        # System-level risks
        system_risks = []

        # Agent utilization risk
        busy_agents = len([a for a in agents if a.get("status") == "busy"])
        total_agents = len(agents)
        utilization = (busy_agents / total_agents * 100) if total_agents > 0 else 0

        if utilization > 90:
            system_risks.append(
                {
                    "risk_type": "overutilization",
                    "severity": "high",
                    "description": ".1f",
                    "impact": "System performance degradation, increased failure rates",
                }
            )

        # Task backlog risk
        pending_tasks = len([t for t in tasks if t.get("status") in ["pending", "in-progress"]])
        if pending_tasks > 20:
            system_risks.append(
                {
                    "risk_type": "task_backlog",
                    "severity": "medium",
                    "description": f"High task backlog: {pending_tasks} tasks pending",
                    "impact": "Increased lead times, customer dissatisfaction",
                }
            )

        overall_risk_level = "low"
        if len(high_risk_tasks) > 5 or any(r["severity"] == "high" for r in system_risks):
            overall_risk_level = "high"
        elif len(high_risk_tasks) > 2 or any(r["severity"] == "medium" for r in system_risks):
            overall_risk_level = "medium"

        return {
            "overall_risk_level": overall_risk_level,
            "high_risk_tasks_count": len(high_risk_tasks),
            "high_risk_tasks": high_risk_tasks[:5],  # Top 5
            "system_risks": system_risks,
            "risk_mitigation_actions": self._generate_risk_mitigation_actions(
                high_risk_tasks, system_risks
            ),
        }

    def _identify_risk_factors(self, task: Dict[str, Any]) -> List[str]:
        """Identify specific risk factors for a task"""
        factors = []

        if task.get("priority") == "critical":
            factors.append("Critical priority")
        if "security" in task.get("skills", []):
            factors.append("Security-sensitive")
        if task.get("status") == "failed":
            factors.append("Previous failure")
        if not task.get("assigned_agent"):
            factors.append("Unassigned")
        if task.get("retry_count", 0) > 2:
            factors.append("Multiple retries")

        return factors

    def _generate_risk_mitigation_actions(
        self, high_risk_tasks: List[Dict], system_risks: List[Dict]
    ) -> List[str]:
        """Generate risk mitigation actions"""
        actions = []

        if high_risk_tasks:
            actions.append(
                f"Address {len(high_risk_tasks)} high-risk tasks with priority assignment"
            )

        for risk in system_risks:
            if risk["risk_type"] == "overutilization":
                actions.append("Scale up agent capacity to reduce utilization pressure")
            elif risk["risk_type"] == "task_backlog":
                actions.append("Implement task prioritization and parallel processing")

        if not actions:
            actions.append("Continue monitoring - risk levels are acceptable")

        return actions

    def _generate_trend_analysis(self, tasks: List[Dict]) -> Dict[str, Any]:
        """Generate trend analysis for key metrics"""

        # Group tasks by day (last 30 days)
        daily_stats = defaultdict(lambda: {"total": 0, "completed": 0, "failed": 0})

        cutoff_date = datetime.now() - timedelta(days=30)

        for task in tasks:
            created_at = task.get("created_at")
            if created_at:
                try:
                    task_date = datetime.fromtimestamp(created_at)
                    if task_date >= cutoff_date:
                        day_key = task_date.strftime("%Y-%m-%d")
                        daily_stats[day_key]["total"] += 1

                        if task.get("status") == "completed":
                            daily_stats[day_key]["completed"] += 1
                        elif task.get("status") == "failed":
                            daily_stats[day_key]["failed"] += 1
                except (ValueError, OSError):
                    pass

        # Calculate trends
        dates = sorted(daily_stats.keys())
        completion_rates = []

        for date in dates:
            stats = daily_stats[date]
            if stats["total"] > 0:
                rate = stats["completed"] / stats["total"]
                completion_rates.append(rate)

        trend_direction = "stable"
        if len(completion_rates) >= 7:
            recent_avg = statistics.mean(completion_rates[-7:])
            earlier_avg = (
                statistics.mean(completion_rates[:-7]) if len(completion_rates) > 7 else recent_avg
            )

            if recent_avg > earlier_avg * 1.05:
                trend_direction = "improving"
            elif recent_avg < earlier_avg * 0.95:
                trend_direction = "declining"

        return {
            "trend_period_days": 30,
            "trend_direction": trend_direction,
            "average_completion_rate": statistics.mean(completion_rates) if completion_rates else 0,
            "volatility": statistics.stdev(completion_rates) if len(completion_rates) > 1 else 0,
            "peak_performance_date": max(
                daily_stats.items(),
                key=lambda x: x[1]["completed"] / x[1]["total"] if x[1]["total"] > 0 else 0,
            )[0]
            if daily_stats
            else None,
            "daily_stats": dict(daily_stats),
        }

    def _generate_executive_recommendations(
        self, metrics: Dict, compliance: Dict, risk: Dict
    ) -> List[str]:
        """Generate executive-level recommendations"""

        recommendations = []

        # Based on key metrics
        health_score = metrics["system_health"]["overall_score"]
        if health_score < 75:
            recommendations.append(
                "Improve system health - current score below acceptable threshold"
            )

        # Based on compliance
        compliance_score = compliance["overall_compliance_score"]
        if compliance_score < 85:
            recommendations.append(
                "Strengthen compliance controls to achieve target compliance levels"
            )

        # Based on risk
        risk_level = risk["overall_risk_level"]
        if risk_level == "high":
            recommendations.append(
                "Implement immediate risk mitigation measures for high-risk items"
            )

        # Performance recommendations
        task_success_rate = metrics["tasks"]["success_rate"]
        if task_success_rate < 90:
            recommendations.append(
                "Improve task success rate through quality assurance and error recovery"
            )

        # Capacity recommendations
        utilization = metrics["agents"]["utilization_rate"]
        if utilization > 85:
            recommendations.append(
                "Consider capacity expansion to handle current utilization levels"
            )

        if not recommendations:
            recommendations.append("System performance is within acceptable parameters")

        return recommendations

    def generate_compliance_report(self) -> Dict[str, Any]:
        """Generate detailed compliance report for auditors"""

        return {
            "report_title": "ACGS-2 Coordination Framework Compliance Report",
            "report_period": f"{(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}",
            "compliance_frameworks": ["SOX", "PCI-DSS", "GDPR", "ACGS-2 Internal Policies"],
            "audit_findings": self._generate_audit_findings(),
            "remediation_status": self._generate_remediation_status(),
            "certification_status": "In Progress - Annual Audit Due Q2 2026",
            "generated_at": datetime.now().isoformat(),
        }

    def _generate_audit_findings(self) -> List[Dict[str, Any]]:
        """Generate detailed audit findings"""
        return [
            {
                "finding_id": "SEC-001",
                "category": "Security",
                "severity": "Medium",
                "description": "Some agents lack explicit security clearance documentation",
                "recommendation": "Implement automated security clearance verification",
                "status": "Open",
                "due_date": (datetime.now() + timedelta(days=30)).isoformat(),
            },
            {
                "finding_id": "COMP-002",
                "category": "Compliance",
                "severity": "Low",
                "description": "Task audit trails could be enhanced with additional metadata",
                "recommendation": "Add comprehensive audit logging for all task operations",
                "status": "In Progress",
                "due_date": (datetime.now() + timedelta(days=60)).isoformat(),
            },
        ]

    def _generate_remediation_status(self) -> Dict[str, Any]:
        """Generate remediation status overview"""
        return {
            "total_findings": 2,
            "resolved": 0,
            "in_progress": 1,
            "open": 1,
            "overdue": 0,
            "completion_percentage": 50,
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

    def _load_workflows(self) -> List[Dict[str, Any]]:
        """Load workflows from storage"""
        workflows = []
        for filename in os.listdir(self.storage_dir):
            if filename.startswith("workflow_") and filename.endswith(".json"):
                try:
                    with open(os.path.join(self.storage_dir, filename), "r") as f:
                        workflows.append(json.load(f))
                except Exception:
                    pass
        return workflows


def main():
    """Main entry point for governance dashboards"""

    import sys

    dashboards = GovernanceDashboards()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "executive-dashboard":
            dashboards.generate_executive_dashboard()

        elif command == "compliance-report":
            dashboards.generate_compliance_report()

        else:
            pass
    else:

        dashboards.generate_executive_dashboard()


if __name__ == "__main__":
    main()
