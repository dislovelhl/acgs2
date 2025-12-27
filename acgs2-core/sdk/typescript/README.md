# ACGS-2 TypeScript SDK

Official TypeScript SDK for the AI Constitutional Governance System (ACGS-2).

**Constitutional Hash:** `cdd01ef066bc6cf2`

## Installation

```bash
npm install @acgs/sdk
# or
yarn add @acgs/sdk
# or
pnpm add @acgs/sdk
```

## Quick Start

```typescript
import { createACGS2SDK } from '@acgs/sdk';

// Initialize the SDK
const sdk = createACGS2SDK({
  baseUrl: 'https://api.acgs.io',
  apiKey: 'your-api-key',
  tenantId: 'your-tenant-id',
});

// Check API health
const health = await sdk.healthCheck();
console.log('API healthy:', health.healthy);

// List policies
const policies = await sdk.policies.list();
console.log('Policies:', policies.data);

// Validate compliance
const result = await sdk.compliance.validate({
  policyId: 'policy-uuid',
  context: {
    action: 'deploy',
    environment: 'production',
    riskLevel: 'low',
  },
});
console.log('Compliant:', result.status === 'compliant');
```

## Features

- **Type-Safe**: Full TypeScript support with Zod runtime validation
- **Constitutional Compliance**: Built-in constitutional hash validation
- **Comprehensive Services**: Policy, Agent, Compliance, Audit, and Governance
- **Error Handling**: Detailed error types for different failure scenarios
- **Retry Logic**: Automatic retry with exponential backoff
- **Real-time Support**: WebSocket subscriptions for agent messaging

## Services

### Policy Service

Manage governance policies:

```typescript
// Create a policy
const policy = await sdk.policies.create({
  name: 'Production Deployment Policy',
  description: 'Requires approval for production deployments',
  rules: [
    {
      condition: 'environment === "production"',
      action: 'require_approval',
    },
  ],
  tags: ['production', 'deployment'],
});

// Activate the policy
await sdk.policies.activate(policy.id);

// Analyze policy impact
const impact = await sdk.policies.analyzeImpact(policy.id);
```

### Agent Service

Manage AI agents and messaging:

```typescript
// Register an agent
const agent = await sdk.agents.register({
  name: 'Deployment Agent',
  type: 'automation',
  capabilities: ['deploy', 'rollback', 'monitor'],
});

// Send a command to another agent
await sdk.agents.sendCommand('target-agent-id', 'deploy', {
  service: 'api-gateway',
  version: '2.0.0',
});

// Subscribe to real-time messages
await sdk.agents.subscribe('wss://api.acgs.io/ws');
sdk.agents.onMessage((message) => {
  console.log('Received:', message);
});
```

### Compliance Service

Validate compliance against policies:

```typescript
// Validate an action
const validation = await sdk.compliance.validateAction(
  'agent-id',
  'deploy',
  {
    service: 'payment-processor',
    environment: 'production',
    changes: ['database-migration'],
  }
);

if (!validation.allowed) {
  console.log('Blocking violations:', validation.blockingViolations);
}

// Generate compliance report
const report = await sdk.compliance.generateReport({
  name: 'Q4 Compliance Report',
  startDate: '2024-10-01T00:00:00Z',
  endDate: '2024-12-31T23:59:59Z',
  format: 'pdf',
});
```

### Audit Service

Record and query audit events:

```typescript
// Record an audit event
await sdk.audit.record({
  category: EventCategory.GOVERNANCE,
  severity: EventSeverity.INFO,
  action: 'policy.activated',
  actor: 'admin@example.com',
  resource: 'policy',
  resourceId: policy.id,
  outcome: 'success',
  details: { previousStatus: 'draft' },
});

// Query audit events
const events = await sdk.audit.queryEvents({
  category: EventCategory.GOVERNANCE,
  startTime: '2024-01-01T00:00:00Z',
  page: 1,
  pageSize: 100,
});

// Verify audit integrity
const integrity = await sdk.audit.verifyIntegrity({
  startDate: '2024-01-01T00:00:00Z',
  endDate: '2024-12-31T23:59:59Z',
});
```

### Governance Service

Handle approvals and governance decisions:

```typescript
// Create an approval request
const approval = await sdk.governance.createApprovalRequest({
  requestType: 'production_deployment',
  payload: {
    service: 'payment-processor',
    version: '3.0.0',
    changes: ['new-payment-methods'],
  },
  riskScore: 75,
  requiredApprovers: 2,
});

// Submit approval decision
await sdk.governance.submitDecision(approval.id, {
  decision: 'approve',
  reasoning: 'Changes reviewed and tested in staging',
});

// Validate constitutional compliance
const constitutional = await sdk.governance.validateConstitutional({
  agentId: 'agent-id',
  action: 'modify_user_data',
  context: {
    dataType: 'personal',
    purpose: 'analytics',
  },
});
```

## Configuration

```typescript
const sdk = createACGS2SDK({
  // Required
  baseUrl: 'https://api.acgs.io',

  // Authentication (choose one)
  apiKey: 'your-api-key',
  accessToken: 'your-jwt-token',

  // Optional
  tenantId: 'your-tenant-id',
  timeout: 30000,
  retryAttempts: 3,
  retryDelay: 1000,
  validateConstitutionalHash: true,

  // Callbacks
  onError: (error) => {
    console.error('API Error:', error);
  },
  onConstitutionalViolation: (expected, received) => {
    console.error('Constitutional hash mismatch!');
  },
});
```

## Error Handling

The SDK provides specific error types for different scenarios:

```typescript
import {
  ACGS2Error,
  AuthenticationError,
  AuthorizationError,
  ValidationError,
  RateLimitError,
  ConstitutionalHashMismatchError,
} from '@acgs/sdk';

try {
  await sdk.policies.create({ /* ... */ });
} catch (error) {
  if (error instanceof AuthenticationError) {
    // Handle authentication failure
  } else if (error instanceof AuthorizationError) {
    // Handle permission denied
  } else if (error instanceof ValidationError) {
    // Handle validation errors
    console.log('Validation errors:', error.validationErrors);
  } else if (error instanceof RateLimitError) {
    // Handle rate limiting
    console.log('Retry after:', error.retryAfter, 'seconds');
  } else if (error instanceof ConstitutionalHashMismatchError) {
    // Handle constitutional violation
  }
}
```

## Constitutional Hash Validation

All responses are validated against the constitutional hash to ensure data integrity:

```typescript
import { validateConstitutionalHash, CONSTITUTIONAL_HASH } from '@acgs/sdk';

// The SDK validates automatically, but you can also validate manually
const isValid = validateConstitutionalHash(response.constitutionalHash);

// Get the expected hash
console.log('Constitutional Hash:', CONSTITUTIONAL_HASH);
// Output: cdd01ef066bc6cf2
```

## Browser Support

The SDK supports modern browsers with ES2022 features. For older browsers, you may need to configure your bundler to transpile the SDK.

## Node.js Support

Requires Node.js 18.0.0 or higher.

## License

Apache-2.0

## Links

- [Documentation](https://acgs.io/docs/sdk)
- [API Reference](https://api.acgs.io/docs)
- [GitHub](https://github.com/acgs/acgs2)
- [Changelog](https://github.com/acgs/acgs2/blob/main/sdk/typescript/CHANGELOG.md)
