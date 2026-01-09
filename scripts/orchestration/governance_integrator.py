#!/usr/bin/env python3
"""
ACGS-2 Governance and Security Integration
Connects coordination framework with governance policies and security controls
"""

import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List


class GovernanceIntegrator:
    """Integrate coordination framework with ACGS-2 governance and security"""

    def __init__(self, storage_dir: str = "src/claude-flow/claude-flow/storage"):
        self.storage_dir = storage_dir
        self.policies_dir = "src/core/policies"
        self.security_dir = "src/core/security"
        os.makedirs(storage_dir, exist_ok=True)

    def assess_task_governance_compliance(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Assess task compliance with governance policies"""

        compliance_checks = {
            "security_clearance": self._check_security_clearance(task),
            "data_privacy": self._check_data_privacy_compliance(task),
            "regulatory_requirements": self._check_regulatory_compliance(task),
            "resource_limits": self._check_resource_limits(task),
            "audit_trail": self._check_audit_requirements(task),
        }

        overall_compliant = all(check["compliant"] for check in compliance_checks.values())
        risk_level = self._calculate_risk_level(compliance_checks)

        return {
            "task_id": task.get("id"),
            "overall_compliant": overall_compliant,
            "risk_level": risk_level,
            "compliance_checks": compliance_checks,
            "remediation_actions": self._generate_remediation_actions(compliance_checks),
            "assessment_timestamp": datetime.now().timestamp(),
        }

    def _check_security_clearance(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Check if task requires and has appropriate security clearance"""

        sensitive_keywords = [
            "password",
            "authentication",
            "encryption",
            "security",
            "access",
            "authorization",
            "confidential",
            "sensitive",
            "audit",
            "compliance",
        ]

        task_text = f"{task.get('task', '')} {task.get('description', '')}".lower()
        requires_clearance = any(keyword in task_text for keyword in sensitive_keywords)

        agent_type = task.get("agent_type", "")
        security_agents = ["security", "architect"]

        has_clearance = agent_type in security_agents or "security" in task.get("skills", [])

        return {
            "compliant": not requires_clearance or has_clearance,
            "requires_clearance": requires_clearance,
            "has_clearance": has_clearance,
            "reason": (
                "Security-sensitive task requires security-cleared agent"
                if requires_clearance and not has_clearance
                else None
            ),
        }

    def _check_data_privacy_compliance(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Check data privacy compliance requirements"""

        privacy_keywords = ["user", "personal", "data", "privacy", "gdpr", "pii", "sensitive"]
        task_text = f"{task.get('task', '')} {task.get('description', '')}".lower()

        involves_privacy = any(keyword in task_text for keyword in privacy_keywords)

        if not involves_privacy:
            return {
                "compliant": True,
                "involves_privacy": False,
                "reason": "Task does not involve personal data",
            }

        # Check if privacy controls are mentioned
        privacy_controls = ["encryption", "anonymization", "consent", "retention", "audit"]
        has_controls = any(control in task_text for control in privacy_controls)

        return {
            "compliant": has_controls,
            "involves_privacy": True,
            "has_privacy_controls": has_controls,
            "reason": (
                "Privacy-sensitive task requires data protection controls"
                if not has_controls
                else None
            ),
        }

    def _check_regulatory_compliance(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Check regulatory compliance requirements"""

        regulatory_keywords = [
            "financial",
            "healthcare",
            "medical",
            "payment",
            "compliance",
            "regulation",
        ]
        task_text = f"{task.get('task', '')} {task.get('description', '')}".lower()

        regulated_domain = any(keyword in task_text for keyword in regulatory_keywords)

        if not regulated_domain:
            return {
                "compliant": True,
                "regulated_domain": False,
                "reason": "Task does not involve regulated domains",
            }

        # Check for compliance frameworks
        compliance_frameworks = ["sox", "pci-dss", "hipaa", "gdpr", "audit", "compliance"]
        has_compliance = any(framework in task_text for framework in compliance_frameworks)

        return {
            "compliant": has_compliance,
            "regulated_domain": True,
            "has_compliance_framework": has_compliance,
            "reason": (
                "Regulated domain task requires compliance framework"
                if not has_compliance
                else None
            ),
        }

    def _check_resource_limits(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Check resource usage limits"""

        # Define resource limits based on task type
        resource_limits = {
            "coder": {"max_effort": "8 hours", "max_complexity": "high"},
            "researcher": {"max_effort": "6 hours", "max_complexity": "medium"},
            "tester": {"max_effort": "4 hours", "max_complexity": "medium"},
            "architect": {"max_effort": "6 hours", "max_complexity": "high"},
        }

        agent_type = task.get("agent_type", "coder")
        limits = resource_limits.get(agent_type, resource_limits["coder"])

        effort = task.get("estimated_effort", "1-2 hours")
        if "hours" in effort:
            max_hours = float(limits["max_effort"].split()[0])
            task_hours = float(effort.split("-")[0].strip())
            within_limits = task_hours <= max_hours
        else:
            within_limits = True

        return {
            "compliant": within_limits,
            "resource_limits": limits,
            "estimated_effort": effort,
            "within_limits": within_limits,
            "reason": (
                f"Task effort exceeds {agent_type} resource limits" if not within_limits else None
            ),
        }

    def _check_audit_requirements(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Check audit trail requirements"""

        audit_keywords = ["audit", "logging", "tracking", "compliance", "security", "access"]
        task_text = f"{task.get('task', '')} {task.get('description', '')}".lower()

        requires_audit = any(keyword in task_text for keyword in audit_keywords)

        if not requires_audit:
            return {
                "compliant": True,
                "requires_audit": False,
                "reason": "Task does not require audit trail",
            }

        # Check if audit mechanisms are mentioned
        audit_mechanisms = ["logging", "audit", "tracking", "monitoring", "trace"]
        has_audit = any(mechanism in task_text for mechanism in audit_mechanisms)

        return {
            "compliant": has_audit,
            "requires_audit": True,
            "has_audit_mechanisms": has_audit,
            "reason": "Audit-required task needs audit mechanisms" if not has_audit else None,
        }

    def _calculate_risk_level(self, compliance_checks: Dict[str, Any]) -> str:
        """Calculate overall risk level based on compliance checks"""

        failed_checks = [
            check for check in compliance_checks.values() if not check.get("compliant", True)
        ]

        if len(failed_checks) >= 3:
            return "critical"
        elif len(failed_checks) >= 2:
            return "high"
        elif len(failed_checks) >= 1:
            return "medium"
        else:
            return "low"

    def _generate_remediation_actions(self, compliance_checks: Dict[str, Any]) -> List[str]:
        """Generate remediation actions for failed compliance checks"""

        actions = []

        for check_name, check_result in compliance_checks.items():
            if not check_result.get("compliant", True):
                check_result.get("reason", f"{check_name} compliance issue")

                if check_name == "security_clearance":
                    actions.append("Assign task to security-cleared agent or reduce task scope")
                elif check_name == "data_privacy":
                    actions.append("Add data privacy controls (encryption, anonymization, consent)")
                elif check_name == "regulatory_requirements":
                    actions.append(
                        "Implement appropriate compliance framework (SOX, PCI-DSS, HIPAA, GDPR)"
                    )
                elif check_name == "resource_limits":
                    actions.append(
                        "Break down task into smaller units or adjust resource allocation"
                    )
                elif check_name == "audit_trail":
                    actions.append("Add audit logging and monitoring mechanisms")

        return actions

    def apply_governance_policies(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply governance policies to a set of tasks"""

        governance_assessments = []
        approved_tasks = []
        rejected_tasks = []
        remediation_required = []

        for task in tasks:
            assessment = self.assess_task_governance_compliance(task)
            governance_assessments.append(assessment)

            if assessment["overall_compliant"]:
                approved_tasks.append(task)
            elif assessment["risk_level"] == "critical":
                rejected_tasks.append(task)
            else:
                remediation_required.append({"task": task, "assessment": assessment})

        # Generate governance report
        report = {
            "assessment_timestamp": datetime.now().timestamp(),
            "total_tasks": len(tasks),
            "approved_tasks": len(approved_tasks),
            "rejected_tasks": len(rejected_tasks),
            "remediation_required": len(remediation_required),
            "governance_assessments": governance_assessments,
            "policy_violations": self._summarize_policy_violations(governance_assessments),
            "recommendations": self._generate_governance_recommendations(governance_assessments),
        }

        return report

    def _summarize_policy_violations(self, assessments: List[Dict[str, Any]]) -> Dict[str, int]:
        """Summarize types of policy violations"""

        violations = {}
        for assessment in assessments:
            if not assessment.get("overall_compliant", True):
                risk_level = assessment.get("risk_level", "unknown")
                violations[risk_level] = violations.get(risk_level, 0) + 1

        return violations

    def _generate_governance_recommendations(self, assessments: List[Dict[str, Any]]) -> List[str]:
        """Generate governance recommendations based on assessments"""

        recommendations = []

        # Check for patterns in violations
        security_violations = sum(
            1 for a in assessments if not a["compliance_checks"]["security_clearance"]["compliant"]
        )
        privacy_violations = sum(
            1 for a in assessments if not a["compliance_checks"]["data_privacy"]["compliant"]
        )

        if security_violations > len(assessments) * 0.5:
            recommendations.append(
                "Increase security agent capacity or implement automated security reviews"
            )

        if privacy_violations > len(assessments) * 0.3:
            recommendations.append(
                "Implement organization-wide data privacy training and automated privacy checks"
            )

        if not recommendations:
            recommendations.append("Governance controls are functioning effectively")

        return recommendations

    def audit_swarm_operations(self) -> Dict[str, Any]:
        """Audit swarm operations for governance compliance"""

        # Load swarm operations data
        agents = self._load_agents()
        tasks = self._load_tasks()
        swarms = self._load_swarms()

        # Audit checks
        audit_findings = {
            "agent_compliance": self._audit_agent_compliance(agents),
            "task_governance": self._audit_task_governance(tasks),
            "swarm_security": self._audit_swarm_security(swarms, agents),
            "operational_integrity": self._audit_operational_integrity(tasks, agents),
        }

        # Calculate compliance score
        total_checks = sum(len(findings) for findings in audit_findings.values())
        passed_checks = sum(
            sum(1 for finding in findings if finding.get("status") == "passed")
            for findings in audit_findings.values()
        )
        compliance_score = (passed_checks / total_checks * 100) if total_checks > 0 else 0

        return {
            "audit_timestamp": datetime.now().timestamp(),
            "compliance_score": round(compliance_score, 1),
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "findings": audit_findings,
            "recommendations": self._generate_audit_recommendations(audit_findings),
        }

    def _audit_agent_compliance(self, agents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Audit agent compliance with governance policies"""
        findings = []

        for agent in agents:
            # Check if agent has required security clearance for sensitive operations
            sensitive_types = ["security", "architect"]
            if agent.get("type") in sensitive_types:
                has_clearance = "security" in agent.get("capabilities", [])
                findings.append(
                    {
                        "type": "agent_security_clearance",
                        "agent_id": agent.get("agent_id"),
                        "status": "passed" if has_clearance else "failed",
                        "details": f"Agent {agent.get('name')} security clearance check",
                    }
                )

        return findings

    def _audit_task_governance(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Audit task governance compliance"""
        findings = []

        for task in tasks:
            assessment = self.assess_task_governance_compliance(task)
            findings.append(
                {
                    "type": "task_compliance",
                    "task_id": task.get("id"),
                    "status": "passed" if assessment["overall_compliant"] else "failed",
                    "risk_level": assessment["risk_level"],
                    "details": f"Task governance assessment for {task.get('task')}",
                }
            )

        return findings

    def _audit_swarm_security(
        self, swarms: Dict[str, Dict[str, Any]], agents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Audit swarm security configuration"""
        findings = []

        for swarm_id, swarm in swarms.items():
            # Check swarm security features
            has_memory_security = swarm.get("memory_enabled", False)
            swarm.get("github_enabled", False)

            findings.append(
                {
                    "type": "swarm_memory_security",
                    "swarm_id": swarm_id,
                    "status": "passed" if has_memory_security else "warning",
                    "details": f"Swarm {swarm_id} memory persistence security",
                }
            )

        return findings

    def _audit_operational_integrity(
        self, tasks: List[Dict[str, Any]], agents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Audit operational integrity"""
        findings = []

        # Check for orphaned tasks (assigned but no active agent)
        active_agent_ids = {
            agent["agent_id"] for agent in agents if agent.get("status") == "active"
        }
        for task in tasks:
            if task.get("assigned_agent") and task.get("assigned_agent") not in active_agent_ids:
                findings.append(
                    {
                        "type": "orphaned_task",
                        "task_id": task.get("id"),
                        "status": "warning",
                        "details": f"Task assigned to inactive agent {task.get('assigned_agent')}",
                    }
                )

        return findings

    def _generate_audit_recommendations(
        self, findings: Dict[str, List[Dict[str, Any]]]
    ) -> List[str]:
        """Generate audit recommendations based on findings"""
        recommendations = []

        failed_checks = sum(
            len([f for f in findings_list if f.get("status") == "failed"])
            for findings_list in findings.values()
        )

        warning_checks = sum(
            len([f for f in findings_list if f.get("status") == "warning"])
            for findings_list in findings.values()
        )

        if failed_checks > 0:
            recommendations.append(
                f"Address {failed_checks} critical compliance failures immediately"
            )

        if warning_checks > 0:
            recommendations.append(
                f"Review {warning_checks} warning conditions for potential improvements"
            )

        return recommendations or ["All governance checks passed"]

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

    def _load_swarms(self) -> Dict[str, Dict[str, Any]]:
        """Load swarms from storage"""
        swarms = {}
        for filename in os.listdir(self.storage_dir):
            if filename.startswith("swarm_") and filename.endswith(".json"):
                try:
                    with open(os.path.join(self.storage_dir, filename), "r") as f:
                        config = json.load(f)
                        swarm_id = config.get("swarm_id")
                        if swarm_id:
                            swarms[swarm_id] = config
                except Exception:
                    pass
        return swarms


def main():
    """Main entry point for governance integration"""
    integrator = GovernanceIntegrator()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "assess-task":
            task_id = sys.argv[2] if len(sys.argv) > 2 else None
            if task_id:
                tasks = integrator._load_tasks()
                task = next((t for t in tasks if t.get("id") == task_id), None)
                if task:
                    integrator.assess_task_governance_compliance(task)
                else:
                    pass
            else:
                pass

        elif command == "audit":
            integrator.audit_swarm_operations()

        elif command == "apply-policies":
            tasks = integrator._load_tasks()
            integrator.apply_governance_policies(tasks)

        else:
            pass
    else:
        # Run full governance audit
        integrator.audit_swarm_operations()


if __name__ == "__main__":
    main()
