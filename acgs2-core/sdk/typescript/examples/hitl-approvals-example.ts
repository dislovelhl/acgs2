#!/usr/bin/env tsx
/**
 * ACGS-2 HITL Approvals SDK Example
 * Demonstrates Human-in-the-Loop approval workflows
 * Constitutional Hash: cdd01ef066bc6cf2
 */

import { createACGS2SDK } from '../src/index.js';

async function main() {
  console.log('🚀 ACGS-2 HITL Approvals Example\n');

  // Initialize SDK
  const sdk = createACGS2SDK({
    baseUrl: 'http://localhost:8200', // HITL Approvals service
    timeout: 30000,
  });

  try {
    // Health check
    console.log('🔍 Checking HITL Approvals service health...');
    const health = await sdk.healthCheck();
    console.log(`✅ Service healthy: ${health.healthy} (${health.latencyMs}ms)\n`);

    // Example 1: Create an approval request
    console.log('📝 Creating approval request...');
    const approvalRequest = await sdk.hitlApprovals.createApprovalRequest({
      requestType: 'model_deployment',
      payload: {
        model_name: 'fraud_detection_v2',
        version: '2.1.0',
        deployment_environment: 'production',
        risk_assessment: {
          risk_level: 'medium',
          impact_areas: ['financial', 'customer_trust'],
          rollback_plan: 'Automated rollback to v2.0.1',
        },
        performance_metrics: {
          accuracy: 0.94,
          precision: 0.91,
          recall: 0.89,
        },
      },
      riskScore: 65.0,
    });
    console.log(`✅ Created approval request: ${approvalRequest.id}`);
    console.log(`   Status: ${approvalRequest.status}`);
    console.log(`   Required approvers: ${approvalRequest.requiredApprovers}\n`);

    // Example 2: List approval requests
    console.log('📋 Listing approval requests...');
    const requests = await sdk.hitlApprovals.listApprovalRequests({
      status: 'pending',
      page: 1,
      pageSize: 10,
    });
    console.log(`📊 Found ${requests.total} approval requests`);
    requests.data.slice(0, 3).forEach((req, i) => {
      console.log(`   ${i + 1}. ${req.id}: ${req.requestType} - ${req.status}`);
    });
    console.log();

    // Example 3: Get specific approval request
    console.log(`🔍 Getting approval request details: ${approvalRequest.id}`);
    const details = await sdk.hitlApprovals.getApprovalRequest(approvalRequest.id);
    console.log(`📋 Request details: ${details.requestType}`);
    console.log(`   Risk Score: ${details.riskScore}`);
    console.log(`   Current Approvals: ${details.currentApprovals}/${details.requiredApprovers}\n`);

    // Example 4: Submit approval decision (approve)
    console.log('✅ Submitting approval decision...');
    const decision = await sdk.hitlApprovals.submitDecision(approvalRequest.id, {
      decision: 'approve',
      reasoning: 'Model performance metrics meet production standards. Risk mitigation plan is comprehensive.',
    });
    console.log(`✅ Decision submitted: ${decision.status}\n`);

    // Example 5: Get pending approvals for a user
    console.log("👤 Getting pending approvals for user 'alice@example.com'...");
    const pending = await sdk.hitlApprovals.getPendingApprovals('alice@example.com', {
      page: 1,
      pageSize: 5,
    });
    console.log(`📋 User has ${pending.data.length} pending approvals\n`);

    // Example 6: Get approval workflow configuration
    console.log('⚙️ Getting approval workflow configuration...');
    const config = await sdk.hitlApprovals.getApprovalWorkflowConfig();
    console.log(`🔧 Workflow config sections: ${Object.keys(config).join(', ')}\n`);

    // Example 7: Get approval metrics
    console.log('📊 Getting approval metrics...');
    const metrics = await sdk.hitlApprovals.getApprovalMetrics({
      startDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      endDate: new Date().toISOString().split('T')[0],
    });
    console.log(`📈 Available metrics: ${Object.keys(metrics).join(', ')}\n`);

    // Example 8: Escalate a request (if needed)
    console.log('🚨 Escalating approval request...');
    const escalated = await sdk.hitlApprovals.escalateApprovalRequest(
      approvalRequest.id,
      'Urgent production deployment required for critical business feature'
    );
    console.log(`📢 Request escalated: ${escalated.status}\n`);

    console.log('🎉 HITL Approvals example completed successfully!');

  } catch (error) {
    console.error('❌ Error:', error);
    process.exit(1);
  }
}

// Run the example
main().catch(console.error);
