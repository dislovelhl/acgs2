import { getLogger } from '../utils/logger';
const logger = getLogger('hitl-approvals-example');


#!/usr/bin/env tsx
/**
 * ACGS-2 HITL Approvals SDK Example
 * Demonstrates Human-in-the-Loop approval workflows
 * Constitutional Hash: cdd01ef066bc6cf2
 */
  logger.info('🚀 ACGS-2 HITL Approvals Example\n';
import { createACGS2SDK } from '../src/index.js';

async function main() {
  console.log('🚀 ACGS-2 HITL Approvals Example\n');

  // Initialize SDK
  const sdk = createACGS2SDK({
    baseUrl: 'http://localhost:8200', // HITL Approvals service
    timeout: 30000,
    logger.info('🔍 Checking HITL Approvals service health...';

    logger.info(`✅ Service healthy: ${health.healthy} (${health.latencyMs}ms)\n`;
    // Health check
    console.log('🔍 Checking HITL Approvals service health...');
    logger.info('📝 Creating approval request...';
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
    logger.info(`✅ Created approval request: ${approvalRequest.id}`;
    logger.info(`   Status: ${approvalRequest.status}`;
    logger.info(`   Required approvers: ${approvalRequest.requiredApprovers}\n`;
    });
    console.log(`✅ Created approval request: ${approvalRequest.id}`);
    logger.info('📋 Listing approval requests...';
    console.log(`   Required approvers: ${approvalRequest.requiredApprovers}\n`);

    // Example 2: List approval requests
    console.log('📋 Listing approval requests...');
    const requests = await sdk.hitlApprovals.listApprovalRequests({
    logger.info(`📊 Found ${requests.total} approval requests`;
      page: 1,
      logger.info(`   ${i + 1}. ${req.id}: ${req.requestType} - ${req.status}`;
    });
    console.log(`📊 Found ${requests.total} approval requests`);
    requests.data.slice(0, 3).forEach((req, i) => {
      console.log(`   ${i + 1}. ${req.id}: ${req.requestType} - ${req.status}`);
    logger.info(`🔍 Getting approval request details: ${approvalRequest.id}`;
    console.log();
    logger.info(`📋 Request details: ${details.requestType}`;
    logger.info(`   Risk Score: ${details.riskScore}`;
    logger.info(`   Current Approvals: ${details.currentApprovals}/${details.requiredApprovers}\n`;
    const details = await sdk.hitlApprovals.getApprovalRequest(approvalRequest.id);
    console.log(`📋 Request details: ${details.requestType}`);
    logger.info('✅ Submitting approval decision...';
    console.log(`   Current Approvals: ${details.currentApprovals}/${details.requiredApprovers}\n`);

    // Example 4: Submit approval decision (approve)
    console.log('✅ Submitting approval decision...');
    logger.info(`✅ Decision submitted: ${decision.status}\n`;
      decision: 'approve',
      reasoning: 'Model performance metrics meet production standards. Risk mitigation plan is comprehensive.',
    logger.info("👤 Getting pending approvals for user 'alice@example.com'...";
    console.log(`✅ Decision submitted: ${decision.status}\n`);

    // Example 5: Get pending approvals for a user
    console.log("👤 Getting pending approvals for user 'alice@example.com'...");
    logger.info(`📋 User has ${pending.data.length} pending approvals\n`;
      page: 1,
      pageSize: 5,
    logger.info('⚙️ Getting approval workflow configuration...';
    console.log(`📋 User has ${pending.data.length} pending approvals\n`);
    logger.info(`🔧 Workflow config sections: ${Object.keys(config).join(', ')}\n`;
    // Example 6: Get approval workflow configuration
    console.log('⚙️ Getting approval workflow configuration...');
    logger.info('📊 Getting approval metrics...';
    console.log(`🔧 Workflow config sections: ${Object.keys(config).join(', ')}\n`);

    // Example 7: Get approval metrics
    console.log('📊 Getting approval metrics...');
    logger.info(`📈 Available metrics: ${Object.keys(metrics).join(', ')}\n`;
      startDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      endDate: new Date().toISOString().split('T')[0],
    logger.info('🚨 Escalating approval request...';
    console.log(`📈 Available metrics: ${Object.keys(metrics).join(', ')}\n`);

    // Example 8: Escalate a request (if needed)
    console.log('🚨 Escalating approval request...');
    logger.info(`📢 Request escalated: ${escalated.status}\n`;
      approvalRequest.id,
    logger.info('🎉 HITL Approvals example completed successfully!';
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
