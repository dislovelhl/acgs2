#!/usr/bin/env python3
"""
ACGS-2 Continuous Governance Monitoring and Alerting System
Provides real-time monitoring of coordination framework with automated alerting
for governance violations, compliance issues, and system health anomalies.
"""

import asyncio
import json
import logging
import os
import smtplib
import time
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional


class AlertManager:
    """Manages alerts and notifications for governance violations"""

    def __init__(self, alert_config: Dict[str, Any] = None):
        self.config = alert_config or self._default_config()
        self.alert_history = []
        self.alert_handlers = {
            "email": self._send_email_alert,
            "log": self._log_alert,
            "webhook": self._send_webhook_alert,
        }

    def _default_config(self) -> Dict[str, Any]:
        return {
            "email": {
                "enabled": True,
                "smtp_server": "localhost",
                "smtp_port": 587,
                "sender": "acgs2-monitor@system.local",
                "recipients": ["security@acgs2.local", "ops@acgs2.local"],
                "use_tls": True,
            },
            "webhook": {
                "enabled": False,
                "url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
                "headers": {},
            },
            "thresholds": {
                "critical_compliance_drop": 70,  # Alert if compliance drops below 70%
                "high_risk_tasks": 3,  # Alert if more than 3 high-risk tasks
                "agent_failure_rate": 20,  # Alert if agent failure rate > 20%
                "resource_exhaustion": 90,  # Alert if resource utilization > 90%
            },
            "cooldown_minutes": 15,  # Don't send duplicate alerts within this window
        }

    async def send_alert(
        self, alert_type: str, severity: str, message: str, details: Dict[str, Any] = None
    ) -> bool:
        """Send an alert through configured channels"""

        alert = {
            "id": f"alert-{int(time.time())}-{hash(message) % 10000}",
            "timestamp": datetime.now().isoformat(),
            "type": alert_type,
            "severity": severity,
            "message": message,
            "details": details or {},
            "acknowledged": False,
        }

        # Check for duplicate alerts within cooldown period
        if self._is_duplicate_alert(alert):
            return False

        self.alert_history.append(alert)

        # Send through all enabled channels
        success = False
        for channel, enabled in self.config.items():
            if isinstance(enabled, dict) and enabled.get("enabled", False):
                if channel in self.alert_handlers:
                    try:
                        await self.alert_handlers[channel](alert)
                        success = True
                    except Exception:
                        pass

        return success

    def _is_duplicate_alert(self, alert: Dict[str, Any]) -> bool:
        """Check if this is a duplicate alert within cooldown period"""
        cooldown = timedelta(minutes=self.config.get("cooldown_minutes", 15))
        cutoff_time = datetime.now() - cooldown

        for prev_alert in self.alert_history:
            if (
                prev_alert["type"] == alert["type"]
                and prev_alert["severity"] == alert["severity"]
                and prev_alert["message"] == alert["message"]
                and datetime.fromisoformat(prev_alert["timestamp"]) > cutoff_time
            ):
                return True

        return False

    async def _send_email_alert(self, alert: Dict[str, Any]):
        """Send alert via email"""
        email_config = self.config["email"]

        msg = MIMEMultipart()
        msg["From"] = email_config["sender"]
        msg["To"] = ", ".join(email_config["recipients"])
        msg["Subject"] = f"ACGS-2 {alert['severity'].upper()} Alert: {alert['type']}"

        body = f"""
ACGS-2 Coordination Framework Alert

Severity: {alert["severity"].upper()}
Type: {alert["type"]}
Time: {alert["timestamp"]}

Message:
{alert["message"]}

Details:
{json.dumps(alert["details"], indent=2)}

This is an automated alert from the ACGS-2 governance monitoring system.
Please investigate immediately.
        """

        msg.attach(MIMEText(body, "plain"))

        try:
            server = smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"])
            if email_config.get("use_tls"):
                server.starttls()
            # Note: In production, add authentication here
            server.sendmail(email_config["sender"], email_config["recipients"], msg.as_string())
            server.quit()
        except Exception as e:
            raise Exception(f"Email sending failed: {e}") from e

    async def _log_alert(self, alert: Dict[str, Any]):
        """Log alert to system logs"""
        logging.warning(f"ALERT [{alert['severity'].upper()}] {alert['type']}: {alert['message']}")

    async def _send_webhook_alert(self, alert: Dict[str, Any]):
        """Send alert via webhook (e.g., Slack)"""
        # Placeholder for webhook implementation


class ContinuousMonitor:
    """Continuous monitoring system for governance compliance and system health"""

    def __init__(self, storage_dir: str = "src/claude-flow/claude-flow/storage"):
        self.storage_dir = storage_dir
        self.is_monitoring = False
        self.monitoring_task = None
        self.alert_manager = AlertManager()
        self.governance_integrator = None
        self.last_check = {}

    async def start_monitoring(self, interval_seconds: int = 60):
        """Start continuous monitoring"""
        if self.is_monitoring:
            return

        self.is_monitoring = True

        # Initialize governance integrator
        from governance_integrator import GovernanceIntegrator

        self.governance_integrator = GovernanceIntegrator(self.storage_dir)

        try:
            while self.is_monitoring:
                await self._perform_monitoring_cycle()
                await asyncio.sleep(interval_seconds)
        except Exception as e:
            await self.alert_manager.send_alert(
                "monitoring_failure",
                "high",
                f"Continuous monitoring system encountered an error: {str(e)}",
            )

    def stop_monitoring(self):
        """Stop continuous monitoring"""
        self.is_monitoring = False

    async def _perform_monitoring_cycle(self):
        """Perform one complete monitoring cycle"""

        try:
            # Run governance audit
            audit_report = self.governance_integrator.audit_swarm_operations()

            # Check for alert conditions
            await self._check_governance_alerts(audit_report)
            await self._check_system_health_alerts()
            await self._check_task_completion_alerts()

            # Update monitoring status
            self.last_check = {
                "timestamp": datetime.now().isoformat(),
                "audit_report": audit_report,
            }

        except Exception as e:
            await self.alert_manager.send_alert(
                "monitoring_cycle_failure",
                "medium",
                f"Failed to complete monitoring cycle: {str(e)}",
            )

    async def _check_governance_alerts(self, audit_report: Dict[str, Any]):
        """Check for governance compliance alerts"""

        compliance_score = audit_report.get("compliance_score", 100)
        thresholds = self.alert_manager.config["thresholds"]

        # Critical compliance drop
        if compliance_score < thresholds["critical_compliance_drop"]:
            await self.alert_manager.send_alert(
                "governance_violation",
                "critical",
                f"Governance compliance dropped to {compliance_score}% (below {thresholds['critical_compliance_drop']}% threshold)",
                {"compliance_score": compliance_score, "audit_report": audit_report},
            )

        # High-risk task accumulation
        findings = audit_report.get("findings", {})
        task_findings = findings.get("task_governance", [])
        high_risk_count = sum(
            1 for f in task_findings if f.get("risk_level") in ["high", "critical"]
        )

        if high_risk_count > thresholds["high_risk_tasks"]:
            await self.alert_manager.send_alert(
                "risk_accumulation",
                "high",
                f"High-risk task accumulation: {high_risk_count} tasks exceed threshold of {thresholds['high_risk_tasks']}",
                {"high_risk_count": high_risk_count, "task_findings": task_findings},
            )

    async def _check_system_health_alerts(self):
        """Check for system health alerts"""

        # Load current system status
        agents = self._load_agents()
        tasks = self._load_tasks()

        thresholds = self.alert_manager.config["thresholds"]

        # Agent failure rate (simplified check)
        failed_tasks = len([t for t in tasks if t.get("status") == "failed"])
        total_tasks = len(tasks)

        if total_tasks > 0:
            failure_rate = (failed_tasks / total_tasks) * 100
            if failure_rate > thresholds["agent_failure_rate"]:
                await self.alert_manager.send_alert(
                    "high_failure_rate",
                    "high",
                    f"Agent failure rate exceeded threshold: {failure_rate:.1f}% ({failed_tasks}/{total_tasks} tasks failed)",
                    {
                        "failure_rate": failure_rate,
                        "failed_tasks": failed_tasks,
                        "total_tasks": total_tasks,
                    },
                )

        # Resource exhaustion
        active_agents = len([a for a in agents if a.get("status") == "active"])
        busy_agents = len([a for a in agents if a.get("status") == "busy"])

        if active_agents > 0:
            utilization = (busy_agents / active_agents) * 100
            if utilization > thresholds["resource_exhaustion"]:
                await self.alert_manager.send_alert(
                    "resource_exhaustion",
                    "medium",
                    f"Resource utilization exceeded threshold: {utilization:.1f}% ({busy_agents}/{active_agents} agents busy)",
                    {
                        "utilization": utilization,
                        "busy_agents": busy_agents,
                        "active_agents": active_agents,
                    },
                )

    async def _check_task_completion_alerts(self):
        """Check for task completion and SLA alerts"""

        tasks = self._load_tasks()
        now = datetime.now()

        # Check for overdue tasks
        overdue_tasks = []
        for task in tasks:
            if task.get("status") in ["in-progress", "pending"]:
                assigned_at = task.get("assigned_at")
                if assigned_at:
                    assigned_time = datetime.fromtimestamp(assigned_at)
                    estimated_hours = self._parse_effort_estimate(
                        task.get("estimated_effort", "2-4 hours")
                    )

                    if estimated_hours and (now - assigned_time).total_seconds() > (
                        estimated_hours * 3600 * 1.5
                    ):
                        overdue_tasks.append(task)

        if overdue_tasks:
            await self.alert_manager.send_alert(
                "overdue_tasks",
                "medium",
                f"{len(overdue_tasks)} tasks are overdue (exceeded 150% of estimated time)",
                {"overdue_tasks": [{"id": t["id"], "task": t["task"]} for t in overdue_tasks]},
            )

    def _parse_effort_estimate(self, effort: str) -> Optional[float]:
        """Parse effort estimate string to hours"""
        if not effort or "hours" not in effort:
            return None

        try:
            # Extract first number from range like "2-4 hours"
            hours = float(effort.split("-")[0].strip())
            return hours
        except (ValueError, IndexError):
            return None

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

    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status"""
        return {
            "is_monitoring": self.is_monitoring,
            "last_check": self.last_check,
            "alert_history": self.alert_manager.alert_history[-10:],  # Last 10 alerts
            "alert_config": self.alert_manager.config,
        }


async def main():
    """Main entry point for continuous monitoring"""

    import sys

    monitor = ContinuousMonitor()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "start":
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
            try:
                await monitor.start_monitoring(interval)
            except KeyboardInterrupt:
                monitor.stop_monitoring()

        elif command == "status":
            monitor.get_monitoring_status()

        elif command == "test-alert":
            await monitor.alert_manager.send_alert(
                "test_alert", "low", "This is a test alert to verify alerting functionality"
            )

        else:
            pass
    else:
        pass


if __name__ == "__main__":
    asyncio.run(main())
