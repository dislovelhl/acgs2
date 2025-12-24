# ACGS-2 TypeScript SDK Guide

Official TypeScript SDK for the AI Constitutional Governance System (ACGS-2).

**Constitutional Hash:** `cdd01ef066bc6cf2`

## Overview

The ACGS-2 TypeScript SDK provides a type-safe, modern interface for building governance-aware applications and agents. It features full TypeScript support, runtime validation with Zod, and built-in constitutional compliance checks.

## Installation

```bash
npm install @acgs/sdk
# or
yarn add @acgs/sdk
```

## Quick Start

```typescript
import { createACGS2SDK } from "@acgs/sdk";

// Initialize the SDK
const sdk = createACGS2SDK({
  baseUrl: "https://api.acgs.io",
  apiKey: "your-api-key",
  tenantId: "your-tenant-id",
});

async function main() {
  // Check API health
  const health = await sdk.healthCheck();
  console.log("API healthy:", health.healthy);

  // List policies
  const policies = await sdk.policies.list();
  console.log("Policies:", policies.data);
}

main();
```

## Core Services

### Policy Service

Manage and analyze governance policies.

```typescript
// Create a policy
const policy = await sdk.policies.create({
  name: "Production Deployment Policy",
  description: "Requires approval for production deployments",
  rules: [
    {
      condition: 'environment === "production"',
      action: "require_approval",
    },
  ],
  tags: ["production", "deployment"],
});

// Activate the policy
await sdk.policies.activate(policy.id);
```

### Agent Service

Handle agent registration and real-time messaging.

```typescript
// Register an agent
const agent = await sdk.agents.register({
  name: "Deployment Agent",
  type: "automation",
  capabilities: ["deploy", "rollback", "monitor"],
});

// Subscribe to real-time messages
await sdk.agents.subscribe("wss://api.acgs.io/ws");
sdk.agents.onMessage((message) => {
  console.log("Received message:", message);
});
```

### Compliance Service

Perform compliance validations.

```typescript
// Validate an action
const validation = await sdk.compliance.validateAction("agent-id", "deploy", {
  service: "payment-processor",
  environment: "production",
});

if (!validation.allowed) {
  console.error("Violations:", validation.blockingViolations);
}
```

### Audit Service

Record and query audit events.

```typescript
import { EventCategory, EventSeverity } from "@acgs/sdk";

// Record an audit event
await sdk.audit.record({
  category: EventCategory.GOVERNANCE,
  severity: EventSeverity.INFO,
  action: "policy.activated",
  actor: "admin@example.com",
  resource: "policy",
  resourceId: "policy-id",
  outcome: "success",
});
```

## Error Handling

The SDK provides specific error classes for robust error management:

```typescript
import {
  AuthenticationError,
  ValidationError,
  ConstitutionalHashMismatchError,
} from "@acgs/sdk";

try {
  await sdk.policies.create({
    /* ... */
  });
} catch (error) {
  if (error instanceof ValidationError) {
    console.error("Validation failed:", error.validationErrors);
  } else if (error instanceof ConstitutionalHashMismatchError) {
    console.error("Constitutional hash mismatch detected!");
  }
}
```

## Constitutional Compliance

Data integrity is guaranteed through automatic constitutional hash validation. Every response from the ACGS-2 platform is verified against the expected hash `cdd01ef066bc6cf2`.

## Requirements

- Node.js 18.0.0 or higher
- Modern browser with ES2022 support
