#!/usr/bin/env python3
"""
ACGS Code Analysis Engine - Phase 4 Service Integration Examples
Comprehensive examples demonstrating integration with the ACGS Code Analysis Engine.

Constitutional Hash: cdd01ef066bc6cf2
Service URL: http://localhost:8107
"""

import asyncio
from datetime import datetime
import json
import logging
import sys
import time
from typing import Any, Dict, Optional

import aiohttp
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ACGSCodeAnalysisClient:
    """Client for integrating with ACGS Code Analysis Engine"""

    def __init__(self, base_url: str = "http://localhost:8107") -> None:
        self.base_url = base_url
        self.constitutional_hash = "cdd01ef066bc6cf2"
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "ACGSCodeAnalysisClient":
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    def verify_constitutional_compliance(self, response_data: dict[str, Any]) -> bool:
        """Verify constitutional compliance in response"""
        try:
            return response_data.get("constitutional_hash") == self.constitutional_hash
        except Exception as e:
            logger.error(f"Operation failed: {e}")
            raise

    async def health_check(self) -> dict[str, Any]:
        """Check service health and constitutional compliance"""
        try:
            if not self.session:
                raise RuntimeError("Session not initialized. Use async context manager.")
                
            async with self.session.get(f"{self.base_url}/health") as response:
                data = await response.json()

                if not self.verify_constitutional_compliance(data):
                    msg = (
                        "Constitutional compliance violation:"
                        f" {data.get('constitutional_hash')}"
                    )
                    raise ValueError(msg)

                return {
                    "status": data.get("status"),
                    "constitutional_compliant": True,
                    "service_version": data.get("version"),
                    "timestamp": data.get("timestamp"),
                }
        except Exception as e:
            logger.error(f"Operation failed: {e}")
            raise

    async def search_code(self, query: str, limit: int = 10) -> dict[str, Any]:
        """Search for code patterns and symbols"""
        try:
            payload = {
                "query": query,
                "limit": limit,
                "constitutional_hash": self.constitutional_hash,
            }

            if not self.session:
                raise RuntimeError("Session not initialized. Use async context manager.")

            async with self.session.post(
                f"{self.base_url}/api/v1/search",
                json=payload,
            ) as response:
                data = await response.json()

                if not self.verify_constitutional_compliance(data):
                    msg = "Constitutional compliance violation in search response"
                    raise ValueError(msg)

                return {
                    "results": data.get("results", []),
                    "total": data.get("total", 0),
                    "query": query,
                    "constitutional_compliant": True,
                }
        except Exception as e:
            logger.error(f"Operation failed: {e}")
            raise

    async def analyze_code(
        self,
        code_content: str,
        language: str = "python",
    ) -> dict[str, Any]:
        """Analyze code for patterns, dependencies, and metrics"""
        try:
            payload = {
                "code": code_content,
                "language": language,
                "constitutional_hash": self.constitutional_hash,
            }

            if not self.session:
                raise RuntimeError("Session not initialized. Use async context manager.")

            async with self.session.post(
                f"{self.base_url}/api/v1/analyze",
                json=payload,
            ) as response:
                data = await response.json()

                if not self.verify_constitutional_compliance(data):
                    msg = "Constitutional compliance violation in analysis response"
                    raise ValueError(msg)

                return {
                    "analysis": data.get("analysis", "mock_analysis"),
                    "language": language,
                    "constitutional_compliant": True,
                    "timestamp": datetime.now().isoformat(),
                }
        except Exception as e:
            logger.error(f"Operation failed: {e}")
            raise

    def sync_health_check(self) -> dict[str, Any]:
        """Synchronous health check for simple integrations"""
        try:
            try:
                response = requests.get(f"{self.base_url}/health", timeout=10)
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise
            data = response.json()

            if not self.verify_constitutional_compliance(data):
                msg = (
                    "Constitutional compliance violation:"
                    f" {data.get('constitutional_hash')}"
                )
                raise ValueError(msg)

            return {
                "status": data.get("status"),
                "constitutional_compliant": True,
                "service_version": data.get("version"),
                "response_time_ms": response.elapsed.total_seconds() * 1000,
            }
        except Exception as e:
            logger.error(f"Operation failed: {e}")
            raise


class IntegrationExamples:
    """Comprehensive integration examples for ACGS Code Analysis Engine"""

    def __init__(self) -> None:
        self.results: Dict[str, Any] = {}

    async def example_1_basic_health_monitoring(self) -> Any:
        """Example 1: Basic health monitoring integration"""

        try:
            async with ACGSCodeAnalysisClient() as client:
                # Perform health check
                await client.health_check()

                # Monitor service over time
                for _i in range(5):
                    start_time = time.time()
                    await client.health_check()
                    # (time.time() - start_time) * 1000  # Unused result

                    await asyncio.sleep(1)

                self.results["basic_health_monitoring"] = {
                    "status": "success",
                    "constitutional_compliant": True,
                    "checks_completed": 5,
                }

        except Exception as e:
            logger.error(f"Operation failed: {e}")
            self.results["basic_health_monitoring"] = {
                "status": "failed",
                "error": str(e),
            }

    async def example_2_code_search_integration(self) -> Any:
        """Example 2: Code search integration"""

        try:
            async with ACGSCodeAnalysisClient() as client:
                # Example search queries
                search_queries = [
                    "function definition",
                    "class inheritance",
                    "async await pattern",
                    "error handling",
                    "database connection",
                ]

                search_results = []

                for query in search_queries:

                    start_time = time.time()
                    result = await client.search_code(query, limit=5)
                    search_time = (time.time() - start_time) * 1000

                    search_results.append(
                        {
                            "query": query,
                            "total_results": result["total"],
                            "search_time_ms": search_time,
                            "constitutional_compliant": result[
                                "constitutional_compliant"
                            ],
                        },
                    )

                self.results["code_search_integration"] = {
                    "status": "success",
                    "searches_completed": len(search_queries),
                    "search_results": search_results,
                    "constitutional_compliant": True,
                }

        except Exception as e:
            logger.error(f"Operation failed: {e}")
            self.results["code_search_integration"] = {
                "status": "failed",
                "error": str(e),
            }

    async def example_3_code_analysis_integration(self) -> Any:
        """Example 3: Code analysis integration"""

        try:
            async with ACGSCodeAnalysisClient() as client:
                # Example code snippets for analysis
                code_examples = [
                    {
                        "name": "Simple Function",
                        "code": """
def calculate_fibonacci(n) -> Any:
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)
""",
                        "language": "python",
                    },
                    {
                        "name": "Async Function",
                        "code": """
try:
    async def fetch_data(url) -> Optional[Dict[str, Any]]:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise
""",
                        "language": "python",
                    },
                    {
                        "name": "Class Definition",
                        "code": """
class DatabaseManager:
    def __init__(self, connection_string) -> Any:
        self.connection_string = connection_string
        self.connection = None

    async def connect(self) -> Any:
        # Implementation here
        pass
""",
                        "language": "python",
                    },
                ]

                analysis_results = []

                for example in code_examples:

                    start_time = time.time()
                    result = await client.analyze_code(
                         example["code"],
                         example["language"],
                    )
                    analysis_time = (time.time() - start_time) * 1000

                    analysis_results.append(
                        {
                            "name": example["name"],
                            "language": example["language"],
                            "analysis_time_ms": analysis_time,
                            "constitutional_compliant": result[
                                "constitutional_compliant"
                            ],
                        },
                    )

                self.results["code_analysis_integration"] = {
                    "status": "success",
                    "analyses_completed": len(code_examples),
                    "analysis_results": analysis_results,
                    "constitutional_compliant": True,
                }

        except Exception as e:
            logger.error(f"Operation failed: {e}")
            self.results["code_analysis_integration"] = {
                "status": "failed",
                "error": str(e),
            }

    def example_4_synchronous_integration(self) -> Any:
        """Example 4: Synchronous integration for simple use cases"""

        try:
            client = ACGSCodeAnalysisClient()

            # Simple synchronous health checks
            for _i in range(3):
                # start_time = time.time()
                client.sync_health_check()
                # time.time() - start_time

            # Test error handling
            try:
                # This should work fine
                client.sync_health_check()

            except Exception:
                pass

            self.results["synchronous_integration"] = {
                "status": "success",
                "checks_completed": 3,
                "constitutional_compliant": True,
            }

        except Exception as e:
            logger.error(f"Operation failed: {e}")
            self.results["synchronous_integration"] = {
                "status": "failed",
                "error": str(e),
            }

    async def run_all_integration_examples(self) -> bool:
        """Run all integration examples"""

        # Run all examples
        await self.example_1_basic_health_monitoring()
        await self.example_2_code_search_integration()
        await self.example_3_code_analysis_integration()
        self.example_4_synchronous_integration()

        # Generate summary
        return self.generate_integration_summary()

    def generate_integration_summary(self) -> bool:
        """Generate comprehensive integration summary"""

        failed_examples = [
            name
            for name, result in self.results.items()
            if result.get("status") == "failed"
        ]

        constitutional_compliant = all(
            result.get("constitutional_compliant", True)
            for result in self.results.values()
        )

        overall_success = len(failed_examples) == 0

        # Save results
        results_file = "phase4_integration_examples_results.json"
        try:
            with open(results_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "overall_success": overall_success,
                        "constitutional_compliant": constitutional_compliant,
                        "examples_results": self.results,
                        "timestamp": datetime.now().isoformat(),
                    },
                    f,
                    indent=2,
                )
        except Exception as e:
            logger.error(f"Unexpected error saving results: {e}")
            raise

        return overall_success


async def main() -> None:
    """Main function to run Phase 4 integration examples"""
    examples = IntegrationExamples()

    try:
        success = await examples.run_all_integration_examples()
        sys.exit(0 if success else 1)

    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
