/**
 * ACGS-2 TypeScript SDK - Policy Registry Example
 * Constitutional Hash: cdd01ef066bc6cf2
 *
 * This example demonstrates how to use the Policy Registry service
 * to manage policies, bundles, and authentication.
 */

import { ACGS2Client } from '../src/client';

async function main() {
  console.log('🛡️  ACGS-2 Policy Registry Example');
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
    const policyService = client.policyRegistry();

    // 1. Health Check
    console.log('\n1. Health Check');
    const health = await policyService.healthCheck();
    console.log(`   Status:`, health);

    // 2. List Policies
    console.log('\n2. List Policies');
    const policies = await policyService.listPolicies({ limit: 5 });
    console.log(`   Found ${policies.length} policies`);
    if (policies.length > 0) {
      const policy = policies[0];
      console.log(`   Example: ${policy.name} (Status: ${policy.status})`);
    }

    // 3. Create a Policy
    console.log('\n3. Create Policy');
    const newPolicy = await policyService.createPolicy({
      name: 'example-security-policy',
      rules: [
        {
          effect: 'allow',
          principal: 'user:*',
          action: 'read',
          resource: 'document:*',
          conditions: {
            ip_address: { type: 'CIDR', value: '192.168.1.0/24' }
          }
        }
      ],
      description: 'Example security policy with IP restrictions',
      tags: ['security', 'example'],
      complianceTags: ['gdpr', 'sox']
    });
    console.log(`   Created policy: ${newPolicy.name} (ID: ${newPolicy.id})`);

    // 4. Get Policy Details
    console.log('\n4. Get Policy Details');
    const policyDetails = await policyService.getPolicy(newPolicy.id);
    console.log(`   Policy: ${policyDetails.name}`);
    console.log(`   Rules: ${policyDetails.rules.length}`);
    console.log(`   Status: ${policyDetails.status}`);

    // 5. Verify Policy
    console.log('\n5. Verify Policy');
    const verification = await policyService.verifyPolicy(newPolicy.id, {
      input: {
        principal: 'user:alice',
        action: 'read',
        resource: 'document:confidential',
        context: {
          ip_address: '192.168.1.100',
          time: '2024-01-15T10:00:00Z'
        }
      }
    });
    console.log(`   Verification: ${verification.allowed ? 'ALLOWED' : 'DENIED'}`);
    if (!verification.allowed && verification.reason) {
      console.log(`   Reason: ${verification.reason}`);
    }

    // 6. Get Policy Versions
    console.log('\n6. Get Policy Versions');
    const versions = await policyService.getPolicyVersions(newPolicy.id);
    console.log(`   Policy has ${versions.length} versions`);

    // 7. Create Policy Version
    console.log('\n7. Create Policy Version');
    const newVersion = await policyService.createPolicyVersion(
      newPolicy.id,
      {
        rules: [
          {
            effect: 'allow',
            principal: 'user:*',
            action: ['read', 'write'],
            resource: 'document:*',
            conditions: {
              ip_address: { type: 'CIDR', value: '192.168.1.0/24' },
              department: { type: 'StringEquals', value: 'engineering' }
            }
          }
        ]
      },
      'Enhanced policy with write permissions and department restrictions'
    );
    console.log(`   Created version: ${newVersion.version}`);

    // 8. List Policy Bundles
    console.log('\n8. List Policy Bundles');
    const bundles = await policyService.listBundles();
    console.log(`   Found ${bundles.length} bundles`);

    // 9. Create Policy Bundle
    console.log('\n9. Create Policy Bundle');
    const bundle = await policyService.createBundle({
      name: 'security-bundle',
      policies: [newPolicy.id],
      description: 'Bundle containing security policies'
    });
    console.log(`   Created bundle: ${bundle.name} (ID: ${bundle.id})`);

    // 10. Get Active Bundle
    console.log('\n10. Get Active Bundle');
    const activeBundle = await policyService.getActiveBundle();
    console.log(`   Active bundle: ${activeBundle.name}`);

    // 11. Authentication (if credentials provided)
    const username = process.env.ACGS2_USERNAME;
    const password = process.env.ACGS2_PASSWORD;

    if (username && password) {
      console.log('\n11. Authentication');
      const authResult = await policyService.authenticate({
        username,
        password
      });
      console.log(`   Authenticated as: ${authResult.user.username}`);
      console.log(`   Roles: ${authResult.user.roles.join(', ')}`);
    }

    console.log('\n✅ Policy Registry example completed successfully!');

  } catch (error) {
    console.error('\n❌ Example failed:', error);
    throw error;
  } finally {
    client.close();
  }
}

// Run the example
main().catch(console.error);
