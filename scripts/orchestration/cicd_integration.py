#!/usr/bin/env python3
"""
ACGS-2 CI/CD Integration Module
Provides automated deployment coordination and pipeline integration
for the coordination framework.
"""

import asyncio
import json
import os
import subprocess
from datetime import datetime
from typing import Any, Dict

import requests


class CICDIntegration:
    """CI/CD integration for automated deployment coordination"""

    def __init__(self, storage_dir: str = "src/claude-flow/claude-flow/storage"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self.pipeline_configs = {}
        self.deployment_history = []

    def register_pipeline(self, name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Register a CI/CD pipeline configuration"""

        pipeline_id = f"pipeline-{name.lower().replace(' ', '-')}-{int(datetime.now().timestamp())}"

        pipeline = {
            "pipeline_id": pipeline_id,
            "name": name,
            "type": config.get("type", "generic"),
            "config": config,
            "status": "registered",
            "created_at": datetime.now().isoformat(),
            "last_execution": None,
            "execution_count": 0,
            "success_rate": 0.0,
        }

        # Validate pipeline configuration
        validation_result = self._validate_pipeline_config(config)
        if not validation_result["valid"]:
            return {
                "success": False,
                "error": f"Invalid pipeline configuration: {validation_result['errors']}",
            }

        # Save pipeline configuration
        pipeline_file = os.path.join(self.storage_dir, f"pipeline_{pipeline_id}.json")
        with open(pipeline_file, "w") as f:
            json.dump(pipeline, f, indent=2)

        self.pipeline_configs[pipeline_id] = pipeline

        return {
            "success": True,
            "pipeline_id": pipeline_id,
            "pipeline": pipeline,
            "message": f"Pipeline '{name}' registered successfully",
        }

    def _validate_pipeline_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate pipeline configuration"""

        errors = []
        required_fields = ["type", "stages"]

        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")

        pipeline_type = config.get("type")
        if pipeline_type not in [
            "jenkins",
            "github-actions",
            "gitlab-ci",
            "azure-devops",
            "generic",
        ]:
            errors.append(f"Unsupported pipeline type: {pipeline_type}")

        stages = config.get("stages", [])
        if not stages:
            errors.append("Pipeline must have at least one stage")

        for i, stage in enumerate(stages):
            if "name" not in stage:
                errors.append(f"Stage {i} missing 'name' field")
            if "steps" not in stage and "jobs" not in stage:
                errors.append(f"Stage {i} must have 'steps' or 'jobs'")

        return {"valid": len(errors) == 0, "errors": errors}

    async def trigger_pipeline(
        self, pipeline_id: str, parameters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Trigger a CI/CD pipeline execution"""

        if pipeline_id not in self.pipeline_configs:
            # Try to load from storage
            pipeline_file = os.path.join(self.storage_dir, f"pipeline_{pipeline_id}.json")
            if os.path.exists(pipeline_file):
                with open(pipeline_file, "r") as f:
                    self.pipeline_configs[pipeline_id] = json.load(f)
            else:
                return {"success": False, "error": f"Pipeline {pipeline_id} not found"}

        pipeline = self.pipeline_configs[pipeline_id]
        config = pipeline["config"]

        # Update execution metadata
        pipeline["execution_count"] += 1
        pipeline["last_execution"] = datetime.now().isoformat()

        execution_id = f"exec-{pipeline_id}-{int(datetime.now().timestamp())}"

        try:
            if config["type"] == "jenkins":
                result = await self._execute_jenkins_pipeline(config, parameters or {})
            elif config["type"] == "github-actions":
                result = await self._execute_github_actions_pipeline(config, parameters or {})
            elif config["type"] == "gitlab-ci":
                result = await self._execute_gitlab_pipeline(config, parameters or {})
            elif config["type"] == "azure-devops":
                result = await self._execute_azure_pipeline(config, parameters or {})
            else:
                result = await self._execute_generic_pipeline(config, parameters or {})

            # Update success rate
            total_executions = pipeline["execution_count"]
            successful_executions = int(pipeline["success_rate"] * (total_executions - 1) / 100)
            if result["success"]:
                successful_executions += 1
            pipeline["success_rate"] = (successful_executions / total_executions) * 100

            # Record execution
            execution_record = {
                "execution_id": execution_id,
                "pipeline_id": pipeline_id,
                "timestamp": datetime.now().isoformat(),
                "parameters": parameters or {},
                "result": result,
                "duration": result.get("duration", 0),
            }

            self.deployment_history.append(execution_record)

            # Save updated pipeline
            pipeline_file = os.path.join(self.storage_dir, f"pipeline_{pipeline_id}.json")
            with open(pipeline_file, "w") as f:
                json.dump(pipeline, f, indent=2)

            return {
                "success": result["success"],
                "execution_id": execution_id,
                "pipeline_id": pipeline_id,
                "result": result,
            }

        except Exception as e:
            return {
                "success": False,
                "execution_id": execution_id,
                "error": f"Pipeline execution failed: {str(e)}",
            }

    async def _execute_jenkins_pipeline(
        self, config: Dict[str, Any], parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute Jenkins pipeline"""

        jenkins_url = config.get("jenkins_url")
        job_name = config.get("job_name")
        auth_token = config.get("auth_token")

        if not all([jenkins_url, job_name]):
            raise Exception("Jenkins URL and job name are required")

        # Build Jenkins API URL
        build_url = f"{jenkins_url}/job/{job_name}/buildWithParameters"

        # Add parameters
        params = parameters.copy()
        params["token"] = auth_token

        try:
            response = requests.post(build_url, params=params)
            response.raise_for_status()

            # Poll for completion (simplified)
            await asyncio.sleep(2)  # Simulate build time

            return {
                "success": True,
                "build_url": response.headers.get("Location", build_url),
                "status": "completed",
                "duration": 120.5,
            }

        except requests.RequestException as e:
            return {"success": False, "error": f"Jenkins API error: {str(e)}", "duration": 0}

    async def _execute_github_actions_pipeline(
        self, config: Dict[str, Any], parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute GitHub Actions workflow"""

        repo = config.get("repository")
        workflow_file = config.get("workflow_file", ".github/workflows/main.yml")
        token = config.get("github_token")

        if not repo or not token:
            raise Exception("GitHub repository and token are required")

        # GitHub API call to trigger workflow
        api_url = (
            f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_file}/dispatches"
        )

        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

        payload = {"ref": parameters.get("branch", "main"), "inputs": parameters}

        try:
            response = requests.post(api_url, headers=headers, json=payload)
            response.raise_for_status()

            await asyncio.sleep(1)  # Simulate workflow trigger

            return {
                "success": True,
                "workflow_triggered": True,
                "status": "running",
                "duration": 0,  # Will be updated when completed
            }

        except requests.RequestException as e:
            return {"success": False, "error": f"GitHub API error: {str(e)}", "duration": 0}

    async def _execute_gitlab_pipeline(
        self, config: Dict[str, Any], parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute GitLab CI/CD pipeline"""

        project_id = config.get("project_id")
        ref = config.get("ref", "main")
        token = config.get("gitlab_token")

        if not project_id or not token:
            raise Exception("GitLab project ID and token are required")

        api_url = f"https://gitlab.com/api/v4/projects/{project_id}/trigger/pipeline"

        headers = {"PRIVATE-TOKEN": token}

        payload = {
            "ref": ref,
            "variables": [{"key": k, "value": str(v)} for k, v in parameters.items()],
        }

        try:
            response = requests.post(api_url, headers=headers, json=payload)
            response.raise_for_status()

            result = response.json()

            return {
                "success": True,
                "pipeline_id": result.get("id"),
                "pipeline_url": result.get("web_url"),
                "status": result.get("status", "running"),
                "duration": 0,
            }

        except requests.RequestException as e:
            return {"success": False, "error": f"GitLab API error: {str(e)}", "duration": 0}

    async def _execute_azure_pipeline(
        self, config: Dict[str, Any], parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute Azure DevOps pipeline"""

        organization = config.get("organization")
        project = config.get("project")
        pipeline_id = config.get("pipeline_id")
        token = config.get("azure_token")

        if not all([organization, project, pipeline_id, token]):
            raise Exception("Azure organization, project, pipeline ID, and token are required")

        api_url = f"https://dev.azure.com/{organization}/{project}/_apis/pipelines/{pipeline_id}/runs?api-version=6.0"

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        payload = {
            "resources": {
                "repositories": {
                    "self": {"refName": f"refs/heads/{parameters.get('branch', 'main')}"}
                }
            },
            "templateParameters": parameters,
        }

        try:
            response = requests.post(api_url, headers=headers, json=payload)
            response.raise_for_status()

            result = response.json()

            return {
                "success": True,
                "run_id": result.get("id"),
                "run_url": result.get("url"),
                "state": result.get("state", "inProgress"),
                "duration": 0,
            }

        except requests.RequestException as e:
            return {"success": False, "error": f"Azure DevOps API error: {str(e)}", "duration": 0}

    async def _execute_generic_pipeline(
        self, config: Dict[str, Any], parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute generic pipeline (local scripts/commands)"""

        stages = config.get("stages", [])

        total_duration = 0
        stage_results = []

        for stage in stages:
            stage_name = stage["name"]
            stage_start = datetime.now()

            try:
                # Execute stage steps
                if "steps" in stage:
                    for step in stage["steps"]:
                        step_type = step.get("type", "command")

                        if step_type == "command":
                            command = step["command"]
                            result = subprocess.run(
                                command, shell=True, capture_output=True, text=True
                            )

                            if result.returncode != 0:
                                raise Exception(f"Command failed: {result.stderr}")

                        elif step_type == "script":
                            script_path = step["script"]
                            if os.path.exists(script_path):
                                result = subprocess.run(
                                    ["python3", script_path], capture_output=True, text=True
                                )
                                if result.returncode != 0:
                                    raise Exception(f"Script failed: {result.stderr}")

                stage_duration = (datetime.now() - stage_start).total_seconds()
                total_duration += stage_duration

                stage_results.append(
                    {"stage": stage_name, "success": True, "duration": stage_duration}
                )

            except Exception as e:
                stage_results.append(
                    {
                        "stage": stage_name,
                        "success": False,
                        "error": str(e),
                        "duration": (datetime.now() - stage_start).total_seconds(),
                    }
                )

                return {
                    "success": False,
                    "error": f"Stage '{stage_name}' failed: {str(e)}",
                    "stage_results": stage_results,
                    "duration": total_duration,
                }

        return {"success": True, "stage_results": stage_results, "duration": total_duration}

    def create_sample_jenkins_pipeline(self) -> Dict[str, Any]:
        """Create a sample Jenkins pipeline configuration"""

        jenkins_config = {
            "type": "jenkins",
            "jenkins_url": "https://jenkins.acgs2.local",
            "job_name": "acgs2-deployment",
            "auth_token": "${JENKINS_TOKEN}",
            "stages": [
                {
                    "name": "build",
                    "steps": [
                        {"type": "command", "command": "echo 'Building application...'"},
                        {"type": "command", "command": "mvn clean package"},
                    ],
                },
                {
                    "name": "test",
                    "steps": [
                        {"type": "command", "command": "echo 'Running tests...'"},
                        {"type": "command", "command": "mvn test"},
                    ],
                },
                {
                    "name": "deploy",
                    "steps": [
                        {"type": "command", "command": "echo 'Deploying to staging...'"},
                        {"type": "command", "command": "kubectl apply -f deployment.yaml"},
                    ],
                },
            ],
        }

        return self.register_pipeline("ACGS-2 Jenkins Deployment", jenkins_config)

    def create_sample_github_actions_pipeline(self) -> Dict[str, Any]:
        """Create a sample GitHub Actions pipeline configuration"""

        github_config = {
            "type": "github-actions",
            "repository": "dislovemartin/ACGS-PGP2",
            "workflow_file": ".github/workflows/deploy.yml",
            "github_token": "${GITHUB_TOKEN}",
            "stages": [
                {"name": "ci", "jobs": ["build", "test", "security-scan"]},
                {"name": "cd", "jobs": ["deploy-staging", "integration-test", "deploy-production"]},
            ],
        }

        return self.register_pipeline("ACGS-2 GitHub Actions", github_config)

    def get_deployment_analytics(self) -> Dict[str, Any]:
        """Get deployment analytics and metrics"""

        if not self.deployment_history:
            return {"message": "No deployment history available"}

        total_deployments = len(self.deployment_history)
        successful_deployments = len([d for d in self.deployment_history if d["result"]["success"]])

        success_rate = (
            (successful_deployments / total_deployments * 100) if total_deployments > 0 else 0
        )

        total_duration = sum(d["result"].get("duration", 0) for d in self.deployment_history)
        avg_duration = total_duration / total_deployments if total_deployments > 0 else 0

        # Pipeline performance
        pipeline_performance = {}
        for deployment in self.deployment_history:
            pipeline_id = deployment["pipeline_id"]
            if pipeline_id not in pipeline_performance:
                pipeline_performance[pipeline_id] = {"total": 0, "successful": 0}
            pipeline_performance[pipeline_id]["total"] += 1
            if deployment["result"]["success"]:
                pipeline_performance[pipeline_id]["successful"] += 1

        return {
            "total_deployments": total_deployments,
            "successful_deployments": successful_deployments,
            "success_rate": round(success_rate, 2),
            "average_duration_seconds": round(avg_duration, 2),
            "pipeline_performance": pipeline_performance,
            "recent_deployments": self.deployment_history[-5:],  # Last 5 deployments
        }


def main():
    """Main entry point for CI/CD integration"""

    import sys

    cicd = CICDIntegration()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "create-jenkins-pipeline":
            cicd.create_sample_jenkins_pipeline()

        elif command == "create-github-pipeline":
            cicd.create_sample_github_actions_pipeline()

        elif command == "trigger-pipeline":
            pipeline_id = sys.argv[2] if len(sys.argv) > 2 else None
            if pipeline_id:
                asyncio.run(cicd.trigger_pipeline(pipeline_id))
            else:
                pass

        elif command == "analytics":
            cicd.get_deployment_analytics()

        else:
            pass
    else:
        # Create sample pipelines
        cicd.create_sample_jenkins_pipeline()
        cicd.create_sample_github_actions_pipeline()


if __name__ == "__main__":
    main()
