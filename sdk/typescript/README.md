# ACGS-2 Enterprise TypeScript SDK

[![Version](https://img.shields.io/badge/version-3.0.0-blue.svg)](https://github.com/ACGS-Project/ACGS-2)
[![Node.js](https://img.shields.io/badge/node-%3E%3D18.0.0-brightgreen)](https://nodejs.org/)
[![TypeScript](https://img.shields.io/badge/typescript-5.3.0-blue)](https://www.typescriptlang.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)

**Constitutional Hash: cdd01ef066bc6cf2**

The ACGS-2 Enterprise TypeScript SDK provides a comprehensive, production-ready interface for integrating with the ACGS-2 Constitutional AI Governance Platform. Built with enterprise-grade features including multi-tenancy, advanced security, compliance frameworks, and extensive monitoring capabilities.

## 🚀 Features

### Core Capabilities
- **Multi-Tenant Architecture**: Complete tenant isolation with context-aware operations
- **Constitutional Compliance**: Built-in constitutional AI governance enforcement
- **Enterprise Security**: JWT authentication, RBAC, and advanced authorization
- **Real-time Monitoring**: Comprehensive metrics, tracing, and health monitoring
- **Fault Tolerance**: Automatic retry logic, circuit breakers, and graceful degradation
- **Type Safety**: Full TypeScript support with runtime validation using Zod

### Enterprise Features
- **Identity Federation**: Okta OIDC, Azure AD, and SAML integration
- **Compliance Frameworks**: EU AI Act, NIST RMF, SOC2, GDPR support
- **Advanced RBAC**: Attribute-based access control and policy delegation
- **Audit Logging**: Immutable audit trails with real-time monitoring
- **Resource Quotas**: Multi-dimensional quota management and enforcement
- **Chaos Engineering**: Built-in resilience testing and failure injection

### Developer Experience
- **Intuitive API**: Clean, consistent interface across all services
- **Event-Driven**: Reactive programming with RxJS integration
- **Auto-Generated Docs**: Comprehensive API documentation
- **Testing Utilities**: Mock clients and testing helpers
- **Migration Tools**: Version compatibility and migration assistance

## 📦 Installation

```bash
npm install @acgs2/sdk
# or
yarn add @acgs2/sdk
# or
pnpm add @acgs2/sdk
```

## 🚀 Quick Start

### Basic Usage

```typescript
import { createACGS2Client, createDefaultConfig } from '@acgs2/sdk';

// Create client configuration
const config = createDefaultConfig('https://api.acgs2.com', 'my-tenant-id');

// Create and initialize client
const client = createACGS2Client(config);

// Handle events
client.on('ready', () => {
  console.log('ACGS-2 SDK ready!');
});

client.on('error', (error) => {
  console.error('SDK error:', error);
});

// Initialize
await client.initialize();

// Use services
const policies = await client.policies.list();
const agents = await client.agents.list();

// Clean up when done
await client.dispose();
```

### Advanced Configuration

```typescript
import { ACGS2Client } from '@acgs2/sdk';

const client = new ACGS2Client({
  baseURL: 'https://api.acgs2.com',
  tenantId: 'my-tenant-id',
  constitutionalHash: 'cdd01ef066bc6cf2',
  timeout: 15000,
  retryAttempts: 5,
  enableMetrics: true,
  enableTracing: true,
  environment: 'production',
});

await client.initialize();
```

### Authentication

```typescript
// Login
const authResponse = await client.auth.login({
  username: 'user@example.com',
  password: 'password',
  tenantId: 'my-tenant-id' // optional, uses context default
});

// Get current user
const user = client.auth.getCurrentUser();

// Check permissions
if (client.auth.isAuthenticated()) {
  const hasPermission = client.auth.getCurrentUser()?.permissions.includes('admin');
}
```

### Multi-Tenant Operations

```typescript
// Switch tenant context
await client.switchTenant('another-tenant-id');

// All subsequent operations use the new tenant context
const tenantPolicies = await client.policies.list();
```

### Policy Management

```typescript
// Create a policy
const policy = await client.policies.create({
  name: 'Data Privacy Policy',
  description: 'Ensures data privacy compliance',
  rules: [
    {
      condition: 'resource.type == "user_data"',
      action: 'encrypt',
      effect: 'allow'
    }
  ],
  complianceFrameworks: ['GDPR', 'CCPA'],
  severity: 'high'
});

// Validate policy
const validation = await client.policies.validate(policy.id);

// List policies with filtering
const policies = await client.policies.list({
  complianceFramework: 'GDPR',
  status: 'active',
  limit: 50
});
```

### Agent Management

```typescript
// Register a new agent
const agent = await client.agents.register({
  name: 'Content Moderation Agent',
  type: 'moderation',
  capabilities: ['text_analysis', 'image_recognition'],
  maxConcurrency: 10,
  resourceRequirements: {
    cpu: '2',
    memory: '4Gi'
  }
});

// Update agent configuration
await client.agents.update(agent.id, {
  maxConcurrency: 20,
  capabilities: ['text_analysis', 'image_recognition', 'video_analysis']
});

// Monitor agent health
const health = await client.agents.getHealth(agent.id);
```

### Audit & Compliance

```typescript
// Query audit events
const auditEvents = await client.audit.query({
  startDate: new Date('2024-01-01'),
  endDate: new Date(),
  eventType: 'policy_violation',
  tenantId: 'my-tenant-id',
  limit: 100
});

// Generate compliance report
const report = await client.audit.generateComplianceReport({
  framework: 'EU_AI_ACT',
  period: 'last_month',
  includeRecommendations: true
});

// Real-time audit monitoring
client.audit.on('violation', (event) => {
  console.log('Policy violation detected:', event);
});
```

### Monitoring & Metrics

```typescript
// Get SDK metrics
const metrics = client.getMetrics();
console.log('Request count:', metrics.services.policy.totalRequests);
console.log('Error rate:', metrics.services.audit.errorRate);

// Get HTTP client stats
const httpStats = (client.httpClient as any).getStats();
console.log('Success rate:', httpStats.successRate);
console.log('Average response time:', httpStats.averageResponseTime);
```

## 🏗️ Architecture

### Core Components

- **ACGS2Client**: Main SDK client with service orchestration
- **TenantContext**: Multi-tenant context management
- **EnterpriseHttpClient**: HTTP client with retry logic and metrics
- **AuthManager**: Authentication and authorization management
- **PolicyService**: Policy lifecycle management
- **AuditService**: Audit logging and compliance reporting
- **AgentService**: Agent registration and monitoring
- **TenantService**: Tenant management and quota enforcement

### Event System

The SDK uses an event-driven architecture for real-time updates:

```typescript
client.on('ready', () => console.log('SDK initialized'));
client.on('tenantSwitched', (tenantId) => console.log('Switched to tenant:', tenantId));
client.on('rateLimited', (retryAfter) => console.log('Rate limited, retry after:', retryAfter));
client.on('quotaExceeded', (resource, limit) => console.log('Quota exceeded for:', resource, limit));

client.auth.on('authenticated', (userId) => console.log('User authenticated:', userId));
client.auth.on('tokenExpired', () => console.log('Token expired'));

client.policies.on('created', (policy) => console.log('Policy created:', policy.name));
client.audit.on('violation', (event) => console.log('Audit violation:', event));
```

## 🔒 Security

### Authentication Methods

- **JWT Tokens**: Secure token-based authentication
- **OAuth 2.0 / OIDC**: Industry-standard identity federation
- **SAML 2.0**: Enterprise SSO integration
- **API Keys**: Service-to-service authentication

### Authorization

- **Role-Based Access Control (RBAC)**: Hierarchical permission system
- **Attribute-Based Access Control (ABAC)**: Fine-grained policy-based authorization
- **Multi-Tenant Isolation**: Complete data and operation isolation
- **Resource Quotas**: Prevent resource exhaustion attacks

### Compliance

- **EU AI Act**: Automated risk assessment and reporting
- **NIST RMF**: Security control implementation and monitoring
- **SOC 2**: Trust principles and criteria compliance
- **GDPR**: Data protection and privacy compliance

## 📊 Monitoring

### Metrics Collection

The SDK automatically collects comprehensive metrics:

- Request/response times and success rates
- Error rates and types
- Authentication and authorization events
- Resource usage and quotas
- Policy evaluations and violations
- Audit event volumes

### Tracing

Distributed tracing support with:

- Request correlation IDs
- Service mesh integration
- Performance bottleneck identification
- End-to-end transaction tracking

### Health Checks

```typescript
const health = await client.healthCheck();
console.log('Overall status:', health.status);
console.log('Service health:', health.services);
```

## 🧪 Testing

```typescript
import { createMockClient } from '@acgs2/sdk/testing';

const mockClient = createMockClient({
  tenantId: 'test-tenant',
  mockResponses: {
    policies: { list: [{ id: '1', name: 'Test Policy' }] },
    agents: { list: [] }
  }
});

// Use mock client for testing
```

## 📚 API Reference

Complete API documentation is available at [docs.acgs2.com/sdk](https://docs.acgs2.com/sdk).

### Key Classes

- [`ACGS2Client`](./docs/classes/ACGS2Client.md) - Main SDK client
- [`TenantContext`](./docs/classes/TenantContext.md) - Tenant context management
- [`AuthManager`](./docs/classes/AuthManager.md) - Authentication management
- [`PolicyService`](./docs/classes/PolicyService.md) - Policy operations
- [`AuditService`](./docs/classes/AuditService.md) - Audit operations
- [`AgentService`](./docs/classes/AgentService.md) - Agent operations

### Error Types

- `AuthenticationError` - Authentication failures
- `AuthorizationError` - Permission denied
- `ValidationError` - Input validation failures
- `QuotaExceededError` - Resource quota violations
- `TenantIsolationError` - Multi-tenant isolation violations
- `ComplianceError` - Compliance requirement violations

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](../CONTRIBUTING.md) for details.

### Development Setup

```bash
git clone https://github.com/ACGS-Project/ACGS-2.git
cd ACGS-2/sdk/typescript
npm install
npm run dev
```

### Testing

```bash
npm run test
npm run test:coverage
npm run lint
npm run type-check
```

## 📄 License

Licensed under the Apache License 2.0. See [LICENSE](../LICENSE) for details.

## 🏢 Enterprise Support

For enterprise support, custom integrations, or professional services:

- 📧 Email: enterprise@acgs2.com
- 📞 Phone: +1 (555) 123-4567
- 🌐 Web: [acgs2.com/enterprise](https://acgs2.com/enterprise)

## 🔗 Links

- [Documentation](https://docs.acgs2.com)
- [API Reference](https://docs.acgs2.com/sdk)
- [GitHub Repository](https://github.com/ACGS-Project/ACGS-2)
- [Issue Tracker](https://github.com/ACGS-Project/ACGS-2/issues)
- [Community Forum](https://community.acgs2.com)
- [Blog](https://blog.acgs2.com)

---

**ACGS-2**: Constitutional AI Governance for the Enterprise 🌟
