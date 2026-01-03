/**
 * ACGS-2 TypeScript SDK - API Gateway Example
 * Constitutional Hash: cdd01ef066bc6cf2
 *
 * This example demonstrates how to use the API Gateway service
 * for health checks, feedback submission, and service discovery.
 */

import { ACGS2Client } from '../src/client';

async function main() {
  console.log('🌐 ACGS-2 API Gateway Example');
  console.log('='.repeat(50));

  // Configuration
  const client = new ACGS2Client({
    baseURL: 'http://localhost:8080', // API Gateway URL
    tenantId: 'example-tenant',
    // Add authentication as needed
    // apiKey: 'your-api-key',
    // svidToken: 'your-svid-token',
  });

  try {
    const gatewayService = client.apiGateway();

    // 1. Health Check
    console.log('\n1. Health Check');
    const health = await gatewayService.healthCheck();
    console.log(`   Status: ${health.healthy ? 'Healthy' : 'Unhealthy'}`);
    if (health.healthy) {
      console.log(`   Version: ${health.version || 'Unknown'}`);
      console.log(`   Constitutional Hash: ${health.constitutionalHash}`);
    }

    // 2. Submit Feedback
    console.log('\n2. Submit Feedback');
    const feedback = await gatewayService.submitFeedback({
      userId: 'example-user-123',
      category: 'feature',
      rating: 5,
      title: 'Excellent SDK Experience',
      description: 'The new SDK makes integration much easier with comprehensive type safety and retry logic.',
      metadata: {
        sdkVersion: '2.0.0',
        language: 'typescript',
        useCase: 'policy_management'
      }
    });
    console.log(`   Feedback submitted with ID: ${feedback.id}`);
    console.log(`   Status: ${feedback.status}`);

    // 3. Get Feedback Statistics
    console.log('\n3. Get Feedback Statistics');
    const stats = await gatewayService.getFeedbackStats();
    console.log(`   Total feedback: ${stats.totalFeedback}`);
    console.log(`   Average rating: ${stats.averageRating.toFixed(1)}/5.0`);

    if (Object.keys(stats.categoryBreakdown).length > 0) {
      console.log('   Category breakdown:');
      Object.entries(stats.categoryBreakdown).forEach(([category, count]) => {
        console.log(`     ${category}: ${count}`);
      });
    }

    if (stats.recentFeedback.length > 0) {
      console.log('   Recent feedback:');
      stats.recentFeedback.slice(0, 3).forEach((fb) => {
        console.log(`     ${fb.rating}⭐ '${fb.title}' by ${fb.userId}`);
      });
    }

    // 4. List Available Services
    console.log('\n4. Service Discovery');
    const servicesResponse = await gatewayService.listServices();

    console.log(`   Gateway Version: ${servicesResponse.gateway.version}`);
    console.log(`   Uptime: ${servicesResponse.gateway.uptime} seconds`);
    console.log(`   Active Connections: ${servicesResponse.gateway.activeConnections}`);

    console.log(`\n   Available Services (${servicesResponse.services.length}):`);
    servicesResponse.services.forEach((service) => {
      const statusIcon = service.status === 'healthy' ? '✅' :
                        service.status === 'degraded' ? '⚠️' : '❌';
      console.log(`     ${statusIcon} ${service.name}`);
      console.log(`         Status: ${service.status}`);
      console.log(`         Version: ${service.version}`);
      if (service.description) {
        console.log(`         Description: ${service.description}`);
      }
      if (service.endpoints.length > 0) {
        const endpointList = service.endpoints.slice(0, 3).join(', ');
        const suffix = service.endpoints.length > 3 ? '...' : '';
        console.log(`         Endpoints: ${endpointList}${suffix}`);
      }
    });

    console.log('\n✅ API Gateway example completed successfully!');

  } catch (error) {
    console.error('\n❌ Example failed:', error);
    throw error;
  } finally {
    client.close();
  }
}

// Run the example
main().catch(console.error);
