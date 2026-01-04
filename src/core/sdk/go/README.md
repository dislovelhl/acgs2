# ACGS-2 Go SDK

Official Go SDK for the AI Constitutional Governance System (ACGS-2).

**Constitutional Hash:** `cdd01ef066bc6cf2`

## Installation

```bash
go get github.com/acgs2/sdk/go
```

## Quick Start

```go
package main

import (
    "context"
    "log"
    "time"

    sdk "github.com/acgs2/sdk/go"
)

func main() {
    // Configure client
    config := sdk.ClientConfig{
        BaseURL:   "https://api.acgs.io",
        APIKey:    "your-api-key",
        TenantID:  "your-tenant-id",
        Timeout:   30 * time.Second,
        Retry: sdk.RetryConfig{
            MaxAttempts: 3,
            BaseDelay:   1 * time.Second,
            MaxDelay:    10 * time.Second,
        },
    }

    client := sdk.NewClient(config)
    defer client.Close()

    ctx := context.Background()

    // Health check
    health := client.APIGateway().HealthCheck(ctx)
    log.Printf("API healthy: %v", health.Healthy)

    // Use Policy Registry service
    policyService := client.PolicyRegistry()

    // List policies
    policies, err := policyService.ListPolicies(ctx, nil, 10, 0)
    if err != nil {
        log.Fatal(err)
    }

    log.Printf("Found %d policies", len(policies))
}
```

## Features

- **Type-Safe**: Full Go struct definitions with proper JSON tags
- **Constitutional Compliance**: Built-in constitutional hash validation
- **Comprehensive Services**: Policy Registry, API Gateway, Agent, Compliance, Audit, Governance
- **Retry Logic**: Configurable exponential backoff retry mechanisms
- **Context Support**: Full context.Context integration for cancellation
- **Connection Pooling**: Efficient HTTP connection reuse

## Services

### Policy Registry Service

```go
policyService := client.PolicyRegistry()

// Create a policy
policy, err := policyService.CreatePolicy(ctx, sdk.CreatePolicyRequest{
    Name: "security-policy",
    Rules: []map[string]interface{}{
        {"effect": "allow", "principal": "user:*", "action": "read"},
    },
    Description: stringPtr("Basic security policy"),
})

// Verify policy compliance
result, err := policyService.VerifyPolicy(ctx, policy.ID, sdk.PolicyVerificationRequest{
    Input: map[string]interface{}{
        "principal": "user:alice",
        "action": "read",
    },
})
```

### API Gateway Service

```go
gatewayService := client.APIGateway()

// Health check
health, err := gatewayService.HealthCheck(ctx)

// Submit feedback
feedback, err := gatewayService.SubmitFeedback(ctx, sdk.FeedbackRequest{
    UserID:    "user123",
    Category:  "feature",
    Rating:    5,
    Title:     "Great SDK!",
    Description: stringPtr("Easy to use and well-documented"),
})

// Service discovery
services, err := gatewayService.ListServices(ctx)
```

## Configuration

```go
config := sdk.ClientConfig{
    BaseURL:   "https://api.acgs.io",
    APIKey:    "your-api-key",
    TenantID:  "your-tenant-id",
    SVIDToken: "your-spiffe-token", // Optional
    Timeout:   30 * time.Second,
    Retry: sdk.RetryConfig{
        MaxAttempts: 3,        // Maximum retry attempts
        BaseDelay:   1 * time.Second,  // Base delay between retries
        MaxDelay:    30 * time.Second, // Maximum delay
    },
}

client := sdk.NewClient(config)
```

## Error Handling

```go
policies, err := policyService.ListPolicies(ctx, nil, 10, 0)
if err != nil {
    log.Printf("Failed to list policies: %v", err)
    return
}
```

## Constitutional Hash Validation

All responses are validated against the constitutional hash:

```go
const ConstitutionalHash = "cdd01ef066bc6cf2"
// The SDK validates automatically
```

## Requirements

- Go 1.21+

## License

Apache-2.0

## Links

- [Documentation](https://docs.acgs.io/sdk/go)
- [API Reference](https://api.acgs.io/docs)
- [GitHub](https://github.com/acgs/acgs2)
- [Go Reference](https://pkg.go.dev/github.com/acgs2/sdk/go)
