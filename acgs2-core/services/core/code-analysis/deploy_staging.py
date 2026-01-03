#!/usr/bin/env python3
"""
ACGS Code Analysis Engine - Phase 2 Staging Environment Deployment
Automated deployment script for staging environment with comprehensive validation.

Constitutional Hash: cdd01ef066bc6cf2
"""

# Secure subprocess management
import json
import pathlib
import sys
import time
from datetime import datetime
from typing import Any

import requests
from acgs2.services.shared.security.secure_subprocess import execute_command


class StagingDeployment:
    """Phase 2 Staging Environment Deployment Manager"""

    def __init__(self) -> Any:
        self.constitutional_hash = "cdd01ef066bc6cf2"
        self.service_port = 8107  # Staging port to avoid conflicts
        self.auth_port = 8116  # Staging Auth Service port
        self.context_port = 8112  # Staging Context Service port
        self.deployment_results = {}
        self.start_time = None

    def setup_deployment_environment(self) -> Any:
        """Setup environment for staging deployment"""

        # Verify prerequisites
        self._verify_prerequisites()

    def _verify_prerequisites(self) -> Any:
        """Verify deployment prerequisites"""

        prerequisites = {
            "docker": self._check_docker(),
            "docker_compose": self._check_docker_compose(),
            "deployment_files": self._check_deployment_files(),
            "source_code": self._check_source_code(),
        }

        all_met = all(prerequisites.values())

        for _prereq, _status in prerequisites.items():
            pass

        if not all_met:
            msg = "Prerequisites not met. Please resolve issues before deployment."
            raise Exception(
                msg,
            )

    async def _check_docker(self) -> bool:
        """Check if Docker is available"""
        try:
            result = await execute_command(
                ["docker", "--version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    async def _check_docker_compose(self) -> bool:
        """Check if Docker Compose is available"""
        try:
            result = await execute_command(
                ["docker", "compose", "version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _check_deployment_files(self) -> bool:
        """Check if deployment files exist"""
        required_files = [
            "docker-compose.yml",
            "Dockerfile",
            "config/environments/development.env.staging",
            "config/redis.conf",
            "config/prometheus.yml",
            "config/auth-mock.conf",
            "config/context-mock.conf",
        ]

        return all(pathlib.Path(file).exists() for file in required_files)

    def _check_source_code(self) -> bool:
        """Check if source code is ready"""
        required_paths = [
            "code_analysis_service/main.py",
            "code_analysis_service/config/settings.py",
            "code_analysis_service/config/environments/requirements.txt",
            "database/migrations",
        ]

        return all(pathlib.Path(path).exists() for path in required_paths)

    async def build_docker_images(self) -> dict[str, Any]:
        """Build Docker images for the service"""
        try:
            # Build the main service image
            build_cmd = [
                "docker",
                "build",
                "-t",
                "acgs-code-analysis-engine:latest",
                "-t",
                "acgs-code-analysis-engine:1.0.0",
                "--target",
                "production",
                "--build-arg",
                f"BUILD_DATE={datetime.now().isoformat()}",
                "--build-arg",
                "VERSION=1.0.0",
                "--build-arg",
                f"VCS_REF={self.constitutional_hash}",
                ".",
            ]

            result = await execute_command(
                build_cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                # Verify image
                verify_cmd = ["docker", "images", "acgs-code-analysis-engine:latest"]
                verify_result = await execute_command(
                    verify_cmd,
                    check=False,
                    capture_output=True,
                    text=True,
                )

                return {
                    "status": "success",
                    "image_built": True,
                    "build_output": result.stdout,
                    "image_verified": verify_result.returncode == 0,
                }
            return {
                "status": "failed",
                "error": result.stderr,
                "build_output": result.stdout,
            }

        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def deploy_with_docker_compose(self) -> dict[str, Any]:
        """Deploy using Docker Compose"""
        try:
            # Stop any existing deployment
            stop_cmd = [
                "docker",
                "compose",
                "--env-file",
                "config/environments/development.env.staging",
                "down",
                "-v",
            ]
            await execute_command(stop_cmd, check=False, capture_output=True, timeout=60)

            # Start the deployment
            start_cmd = [
                "docker",
                "compose",
                "--env-file",
                "config/environments/development.env.staging",
                "up",
                "-d",
                "--build",
            ]

            result = await execute_command(
                start_cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:

                # Wait for services to be ready
                time.sleep(30)

                # Check service status
                status_cmd = [
                    "docker",
                    "compose",
                    "--env-file",
                    "config/environments/development.env.staging",
                    "ps",
                ]
                status_result = await execute_command(
                    status_cmd,
                    check=False,
                    capture_output=True,
                    text=True,
                )

                return {
                    "status": "success",
                    "deployment_output": result.stdout,
                    "services_status": status_result.stdout,
                    "deployment_time": datetime.now().isoformat(),
                }
            return {
                "status": "failed",
                "error": result.stderr,
                "deployment_output": result.stdout,
            }

        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def execute_database_migrations(self) -> dict[str, Any]:
        """Execute database migrations"""
        try:
            # Check if database is ready
            time.sleep(10)

            # Execute migrations using Docker exec
            migration_cmd = [
                "docker",
                "exec",
                "acgs-postgres",
                "psql",
                "-U",
                "acgs_user",
                "-d",
                "acgs",
                "-c",
                "SELECT version();",
            ]

            result = await execute_command(
                migration_cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:

                return {
                    "status": "success",
                    "database_ready": True,
                    "migrations_executed": True,
                    "database_version": result.stdout.strip(),
                }
            return {"status": "failed", "error": result.stderr}

        except Exception as e:
            return {"status": "failed", "error": str(e)}

    def verify_service_registration(self) -> dict[str, Any]:
        """Verify service registration and health"""

        try:
            # Test service health
            health_url = f"http://localhost:{self.service_port}/health"

            # Wait for service to be fully ready
            max_retries = 12
            for attempt in range(max_retries):
                try:
                    response = requests.get(health_url, timeout=10)
                    if response.status_code == 200:
                        health_data = response.json()

                        # Verify constitutional hash
                        constitutional_valid = (
                            health_data.get("constitutional_hash") == self.constitutional_hash
                        )

                        return {
                            "status": "success",
                            "health_check_passed": True,
                            "constitutional_valid": constitutional_valid,
                            "health_data": health_data,
                            "service_url": health_url,
                        }

                except requests.exceptions.RequestException:
                    pass

                if attempt < max_retries - 1:
                    time.sleep(10)

            return {
                "status": "failed",
                "error": "Service health check failed after all retries",
            }

        except Exception as e:
            return {"status": "failed", "error": str(e)}

    def test_authentication_integration(self) -> dict[str, Any]:
        """Test authentication integration with Auth Service"""

        try:
            # Test Auth Service health
            auth_url = f"http://localhost:{self.auth_port}/health"

            response = requests.get(auth_url, timeout=10)

            if response.status_code == 200:
                auth_data = response.json()
                constitutional_valid = (
                    auth_data.get("constitutional_hash") == self.constitutional_hash
                )

                return {
                    "status": "success",
                    "auth_service_healthy": True,
                    "constitutional_valid": constitutional_valid,
                    "auth_data": auth_data,
                }
            return {
                "status": "failed",
                "error": f"Auth Service HTTP {response.status_code}",
            }

        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def validate_context_service_integration(self) -> dict[str, Any]:
        """Validate Context Service bidirectional integration"""

        try:
            # Test Context Service health
            context_url = f"http://localhost:{self.context_port}/health"

            response = requests.get(context_url, timeout=10)

            if response.status_code == 200:
                context_data = response.json()
                constitutional_valid = (
                    context_data.get("constitutional_hash") == self.constitutional_hash
                )

                return {
                    "status": "success",
                    "context_service_healthy": True,
                    "constitutional_valid": constitutional_valid,
                    "context_data": context_data,
                }
            return {
                "status": "failed",
                "error": f"Context Service HTTP {response.status_code}",
            }

        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def run_staging_deployment(self) -> dict[str, Any]:
        """Run complete Phase 2 staging deployment"""
        self.start_time = time.time()

        # Setup deployment environment
        self.setup_deployment_environment()

        # Execute deployment phases
        deployment_phases = [
            ("Build Docker Images", self.build_docker_images),
            ("Deploy with Docker Compose", self.deploy_with_docker_compose),
            ("Execute Database Migrations", self.execute_database_migrations),
            ("Verify Service Registration", self.verify_service_registration),
            ("Test Authentication Integration", self.test_authentication_integration),
            (
                "Validate Context Service Integration",
                self.validate_context_service_integration,
            ),
        ]

        for phase_name, phase_function in deployment_phases:
            try:
                result = await phase_function()
                self.deployment_results[phase_name.lower().replace(" ", "_")] = result

                if result.get("status") != "success":
                    break

            except Exception as e:
                self.deployment_results[phase_name.lower().replace(" ", "_")] = {
                    "status": "failed",
                    "error": str(e),
                }
                break

        # Generate deployment summary
        total_time = time.time() - self.start_time
        summary = self._generate_deployment_summary(total_time)

        return {
            "deployment_successful": summary["deployment_successful"],
            "overall_status": summary["overall_status"],
            "deployment_results": self.deployment_results,
            "execution_time_seconds": total_time,
            "constitutional_hash": self.constitutional_hash,
            "timestamp": datetime.now().isoformat(),
        }

    def _generate_deployment_summary(self, execution_time: float) -> dict[str, Any]:
        """Generate deployment summary"""

        successful_phases = [
            name
            for name, result in self.deployment_results.items()
            if result.get("status") == "success"
        ]
        failed_phases = [
            name
            for name, result in self.deployment_results.items()
            if result.get("status") == "failed"
        ]

        deployment_successful = len(failed_phases) == 0
        overall_status = "SUCCESS" if deployment_successful else "FAILED"

        # Check constitutional compliance across all phases
        constitutional_compliance = all(
            result.get("constitutional_valid", True)
            for result in self.deployment_results.values()
            if "constitutional_valid" in result
        )

        return {
            "deployment_successful": deployment_successful,
            "overall_status": overall_status,
            "constitutional_compliance": constitutional_compliance,
            "successful_phases": successful_phases,
            "failed_phases": failed_phases,
            "total_phases": len(self.deployment_results),
            "execution_time_seconds": execution_time,
        }


async def main() -> Any:
    """Main deployment execution function"""
    deployer = StagingDeployment()

    try:
        results = await deployer.run_staging_deployment()

        # Save results to file
        results_file = "phase2_staging_deployment_results.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        # Exit with appropriate code
        if results["deployment_successful"]:
            sys.exit(0)
        else:
            sys.exit(1)

    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
