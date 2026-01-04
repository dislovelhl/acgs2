#!/usr/bin/env python3
"""
ACGS-2 HITL Approvals SDK Example
Demonstrates Human-in-the-Loop approval workflows
Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import logging
from datetime import datetime, timedelta

from acgs2_sdk import (
    ACGS2Config,
    HITLApprovalsService,
    create_client,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Demonstrate HITL approvals functionality."""

    # Configure client
    config = ACGS2Config(
        base_url="http://localhost:8200",  # HITL Approvals service
        timeout=30.0,
    )

    async with create_client(config) as client:
        hitl_service = HITLApprovalsService(client)

        try:
            # Health check
            logger.info("🔍 Checking HITL Approvals service health...")
            health = await client.health_check()
            logger.info(f"✅ Service healthy: {health}")

            # Example 1: Create an approval request
            logger.info("\n📝 Creating approval request...")
            approval_request = await hitl_service.create_approval_request(
                request_type="model_deployment",
                payload={
                    "model_name": "fraud_detection_v2",
                    "version": "2.1.0",
                    "deployment_environment": "production",
                    "risk_assessment": {
                        "risk_level": "medium",
                        "impact_areas": ["financial", "customer_trust"],
                        "rollback_plan": "Automated rollback to v2.0.1",
                    },
                    "performance_metrics": {
                        "accuracy": 0.94,
                        "precision": 0.91,
                        "recall": 0.89,
                    },
                },
                risk_score=65.0,
            )
            logger.info(f"✅ Created approval request: {approval_request.id}")
            logger.info(f"   Status: {approval_request.status}")
            logger.info(f"   Required approvers: {approval_request.required_approvers}")

            # Example 2: List approval requests
            logger.info("\n📋 Listing approval requests...")
            requests = await hitl_service.list_approval_requests(
                status="pending", page=1, page_size=10
            )
            logger.info(f"📊 Found {requests.total} approval requests")
            for req in requests.data[:3]:  # Show first 3
                logger.info(f"   • {req.id}: {req.request_type} - {req.status}")

            # Example 3: Get specific approval request
            logger.info(f"\n🔍 Getting approval request details: {approval_request.id}")
            details = await hitl_service.get_approval_request(approval_request.id)
            logger.info(f"📋 Request details: {details.request_type}")
            logger.info(f"   Risk Score: {details.risk_score}")
            logger.info(
                f"   Current Approvals: {details.current_approvals}/{details.required_approvers}"
            )

            # Example 4: Submit approval decision (approve)
            logger.info("\n✅ Submitting approval decision...")
            decision = await hitl_service.submit_decision(
                request_id=approval_request.id,
                decision="approve",
                reasoning="Model performance metrics meet production standards. Risk mitigation plan is comprehensive.",
            )
            logger.info(f"✅ Decision submitted: {decision.status}")

            # Example 5: Get pending approvals for a user
            logger.info("\n👤 Getting pending approvals for user 'alice@example.com'...")
            pending = await hitl_service.get_pending_approvals(
                user_id="alice@example.com", page=1, page_size=5
            )
            logger.info(f"📋 User has {len(pending.data)} pending approvals")

            # Example 6: Get approval workflow configuration
            logger.info("\n⚙️ Getting approval workflow configuration...")
            config_data = await hitl_service.get_approval_workflow_config()
            logger.info(f"🔧 Workflow config: {list(config_data.keys())}")

            # Example 7: Get approval metrics
            logger.info("\n📊 Getting approval metrics...")
            metrics = await hitl_service.get_approval_metrics(
                start_date=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                end_date=datetime.now().strftime("%Y-%m-%d"),
            )
            logger.info(f"📈 Metrics: {list(metrics.keys())}")

            # Example 8: Escalate a request (if needed)
            logger.info("\n🚨 Escalating approval request...")
            escalated = await hitl_service.escalate(
                request_id=approval_request.id,
                reason="Urgent production deployment required for critical business feature",
            )
            logger.info(f"📢 Request escalated: {escalated.status}")

        except Exception as e:
            logger.error(f"❌ Error: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
