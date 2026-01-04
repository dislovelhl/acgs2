"""
Constitutional Hash: cdd01ef066bc6cf2
"""

#!/usr/bin/env python3
"""
ACGS-2 Load Test Suite
Tests system behavior under concurrent load using Locust.
"""

import json
import logging
import time
import uuid
from datetime import datetime, timezone

import yaml
from locust import between, events, task
from locust.contrib.fasthttp import FastHttpUser


class E2EUser(FastHttpUser):
    """Load test user that performs end-to-end workflows."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        import os

        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, "e2e_config.yaml")
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

    def create_test_message(self, template_name: str = "governance_request") -> dict:
        """Create a test message for load testing."""
        template = self.config["message_templates"][template_name]

        message = {
            "message_id": str(uuid.uuid4()),
            "conversation_id": str(uuid.uuid4()),
            "content": template["content"],
            "payload": {},
            "from_agent": f"load_test_agent_{self.user_id}",
            "to_agent": None,
            "sender_id": f"load_test_sender_{self.user_id}",
            "message_type": template["message_type"],
            "tenant_id": template["tenant_id"],
            "priority": template["priority"],
            "status": "pending",
            "constitutional_hash": "cdd01ef066bc6cf2",
            "constitutional_validated": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "impact_score": None,
        }
        return message

    @task(3)  # 30% of tasks
    def test_full_e2e_workflow(self):
        """Test complete end-to-end governance workflow."""
        start_time = time.time()

        try:
            message = self.create_test_message()

            # Step 1: Send to Rust Message Bus
            with self.client.post(
                "/rust-message-bus/messages",
                json=message,
                timeout=self.config["services"]["rust_message_bus"]["timeout"],
                catch_response=True,
            ) as response:
                if response.status_code != 200:
                    response.failure(f"Rust Message Bus failed: {response.status_code}")
                    return

            # Step 2: Process through Deliberation Layer
            with self.client.post(
                "/deliberation-layer/process",
                json=message,
                timeout=self.config["services"]["deliberation_layer"]["timeout"],
                catch_response=True,
            ) as deliberation_response:
                if deliberation_response.status_code != 200:
                    deliberation_response.failure(
                        f"Deliberation Layer failed: {deliberation_response.status_code}"
                    )
                    return

                deliberation_data = deliberation_response.json()
                if not deliberation_data.get("success"):
                    deliberation_response.failure("Deliberation processing failed")
                    return

            # Step 3: Generate constraints
            constraint_payload = {"message": message, "context": deliberation_data}
            with self.client.post(
                "/constraint-generation/generate",
                json=constraint_payload,
                timeout=self.config["services"]["constraint_generation"]["timeout"],
                catch_response=True,
            ) as constraint_response:
                if constraint_response.status_code != 200:
                    constraint_response.failure(
                        f"Constraint Generation failed: {constraint_response.status_code}"
                    )
                    return

            # Step 4: Vector search
            search_payload = {
                "query": message["content"],
                "filters": {"tenant_id": message["tenant_id"]},
            }
            with self.client.post(
                "/vector-search/search",
                json=search_payload,
                timeout=self.config["services"]["vector_search"]["timeout"],
                catch_response=True,
            ) as search_response:
                if search_response.status_code != 200:
                    search_response.failure(f"Vector Search failed: {search_response.status_code}")
                    return

            # Step 5: Record audit event
            audit_payload = {
                "event_type": "governance_request",
                "message_id": message["message_id"],
                "data": message,
            }
            with self.client.post(
                "/audit-ledger/record",
                json=audit_payload,
                timeout=self.config["services"]["audit_ledger"]["timeout"],
                catch_response=True,
            ) as audit_response:
                if audit_response.status_code != 200:
                    audit_response.failure(f"Audit Ledger failed: {audit_response.status_code}")
                    return

            # Step 6: Get governance decision
            governance_payload = {
                "message": message,
                "constraints": constraint_response.json(),
                "search_results": search_response.json(),
                "audit_context": audit_response.json(),
            }
            with self.client.post(
                "/adaptive-governance/decide",
                json=governance_payload,
                timeout=self.config["services"]["adaptive_governance"]["timeout"],
                catch_response=True,
            ) as governance_response:
                if governance_response.status_code != 200:
                    governance_response.failure(
                        f"Adaptive Governance failed: {governance_response.status_code}"
                    )
                    return

                governance_data = governance_response.json()

                # Validate response
                required_fields = self.config["expected_responses"]["governance_decision"][
                    "required_fields"
                ]
                for field in required_fields:
                    if field not in governance_data:
                        governance_response.failure(f"Missing required field: {field}")
                        return

                if (
                    governance_data["decision"]
                    not in self.config["expected_responses"]["governance_decision"][
                        "decision_types"
                    ]
                ):
                    governance_response.failure(
                        f"Invalid decision type: {governance_data['decision']}"
                    )
                    return

            # Record total latency
            total_time = (time.time() - start_time) * 1000
            self.environment.events.request.fire(
                request_type="E2E",
                name="full_workflow",
                response_time=total_time,
                response_length=len(json.dumps(governance_data)),
                exception=None,
            )

        except Exception as e:
            self.environment.events.request.fire(
                request_type="E2E",
                name="full_workflow",
                response_time=0,
                response_length=0,
                exception=e,
            )

    @task(2)  # 20% of tasks
    def test_constraint_generation_only(self):
        """Test constraint generation service under load."""
        message = self.create_test_message("constraint_violation")

        with self.client.post(
            "/constraint-generation/generate",
            json={"message": message, "context": {}},
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Constraint generation failed: {response.status_code}")

    @task(2)  # 20% of tasks
    def test_audit_queries(self):
        """Test audit ledger queries under load."""
        with self.client.get("/audit-ledger/events?limit=10", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Audit query failed: {response.status_code}")

    @task(1)  # 10% of tasks
    def test_vector_search_only(self):
        """Test vector search service under load."""
        with self.client.post(
            "/vector-search/search",
            json={"query": "test governance query", "filters": {}},
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Vector search failed: {response.status_code}")

    @task(1)  # 10% of tasks
    def test_deliberation_layer_only(self):
        """Test deliberation layer processing under load."""
        message = self.create_test_message()

        with self.client.post(
            "/deliberation-layer/process", json=message, catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"Deliberation layer failed: {response.status_code}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize test environment."""
    logging.info("Starting ACGS-2 Load Test")
    logging.info(f"Target host: {environment.host}")
    logging.info(
        f"Number of users: {environment.runner.user_count if environment.runner else 'N/A'}"
    )


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Clean up after test."""
    logging.info("Load test completed")
    if environment.runner:
        stats = environment.runner.stats
        logging.info(f"Total requests: {stats.num_requests}")
        logging.error(f"Total failures: {stats.num_failures}")
        logging.info(".2f")
        logging.info(".2f")


if __name__ == "__main__":
    # This file can be run with:
    # locust -f load_test.py --host http://localhost:8080
    # Or for distributed testing:
    # locust -f load_test.py --master --host http://localhost:8080
    # locust -f load_test.py --worker --master-host=localhost

    import locust

    locust.main.main()
