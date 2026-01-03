# ACGS-2 Enterprise Go SDK

[![Go Version](https://img.shields.io/badge/go-1.21+-blue.svg)](https://golang.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![GoDoc](https://godoc.org/github.com/acgs-project/acgs2-go-sdk?status.svg)](https://godoc.org/github.com/acgs-project/acgs2-go-sdk)

**Constitutional Hash: cdd01ef066bc6cf2**

The ACGS-2 Enterprise Go SDK provides a comprehensive, production-ready interface for integrating with the ACGS-2 Constitutional AI Governance Platform. Built with enterprise-grade features including multi-tenancy, advanced security, compliance frameworks, and extensive monitoring capabilities.

## 🚀 Features

### Core Capabilities
- **Multi-Tenant Architecture**: Complete tenant isolation with context-aware operations
- **Constitutional Compliance**: Built-in constitutional AI governance enforcement
- **Enterprise Security**: JWT authentication, RBAC, and advanced authorization
- **Real-time Monitoring**: Comprehensive metrics, tracing, and health monitoring
- **Fault Tolerance**: Automatic retry logic, circuit breakers, and graceful degradation
- **Type Safety**: Full Go type safety with comprehensive error handling

### Enterprise Features
- **Identity Federation**: OAuth2/OIDC integration with enterprise providers
- **Compliance Frameworks**: Automated compliance monitoring and reporting
- **Advanced RBAC**: Role-based access control with fine-grained permissions
- **Audit Logging**: Immutable audit trails with real-time monitoring
- **Resource Quotas**: Multi-dimensional quota management and enforcement
- **Structured Logging**: Zap-based logging with configurable levels

### Developer Experience
- **Intuitive API**: Clean, consistent interface across all services
- **Context Support**: Full Go context support for request cancellation and timeouts
- **Comprehensive Error Handling**: Detailed error types with actionable messages
- **Automatic Retries**: Configurable retry logic with exponential backoff
- **TLS Support**: Client certificate authentication and custom CA support
- **Testing Utilities**: Mock clients and testing helpers

## 📦 Installation

```bash
go get github.com/acgs-project/acgs2-go-sdk
```

## 🚀 Quick Start

### Basic Usage

```go
package main

import (
    "context"
    "log"

    "github.com/acgs-project/acgs2-go-sdk/pkg/client"
)

func main() {
    // Create client configuration
    config := client.NewConfig("https://api.acgs2.com", "my-tenant-id")

    // Create and initialize client
    c, err := client.New(config)
    if err != nil {
        log.Fatal("Failed to create client:", err)
    }

    // Use services
    ctx := context.Background()
    policies, err := c.Policy.List(ctx, nil)
    if err != nil {
        log.Fatal("Failed to list policies:", err)
    }

    log.Printf("Found %d policies", len(policies.Data))
}
```

### Authentication

```go
// Login
authResp, err := c.Auth.Login(ctx, "user@example.com", "password")
if err != nil {
    log.Fatal("Login failed:", err)
}

log.Printf("Logged in as: %s", authResp.User.Username)

// Check authentication status
if c.Auth.IsAuthenticated() {
    log.Println("User is authenticated")
}

// Get user info
userInfo, err := c.Auth.GetUserInfo(ctx)
if err != nil {
    log.Fatal("Failed to get user info:", err)
}

// Logout
err = c.Auth.Logout(ctx)
if err != nil {
    log.Fatal("Logout failed:", err)
}
```

### Policy Management

```go
// List policies
policies, err := c.Policy.List(ctx, &models.PolicyQuery{
    Status: &[]models.PolicyStatus{models.PolicyStatusActive}[0],
    Limit:  50,
})
if err != nil {
    log.Fatal("Failed to list policies:", err)
}

// Create a policy
newPolicy, err := c.Policy.Create(ctx, &models.CreatePolicyRequest{
    Name:        "Data Privacy Policy",
    Description: "Ensures data privacy compliance",
    Type:        models.PolicyTypeSecurity,
    Rules: []models.PolicyRule{
        {
            Name:    "Encryption Required",
            Condition: "input.resource.type == 'sensitive_data'",
            Action:  "encrypt",
            Severity: models.SeverityHigh,
            Enabled: true,
        },
    },
    ComplianceFrameworks: []string{"GDPR", "CCPA"},
    Severity:           models.SeverityHigh,
})
if err != nil {
    log.Fatal("Failed to create policy:", err)
}

// Validate policy
validation, err := c.Policy.Validate(ctx, newPolicy)
if err != nil {
    log.Fatal("Policy validation failed:", err)
}

if !validation.Valid {
    log.Printf("Policy validation errors: %v", validation.Errors)
}
```

### Audit & Compliance

```go
// Query audit events
auditEvents, err := c.Audit.Query(ctx, &models.AuditQuery{
    StartTime: &time.Now().Add(-24 * time.Hour),
    EndTime:   &time.Now(),
    Severity:  &[]models.Severity{models.SeverityHigh}[0],
    Limit:     100,
})
if err != nil {
    log.Fatal("Failed to query audit events:", err)
}

// Generate compliance report
report, err := c.Audit.GenerateComplianceReport(ctx, "GDPR", "last_month")
if err != nil {
    log.Fatal("Failed to generate compliance report:", err)
}

log.Printf("Compliance score: %.2f%%", report.OverallScore*100)
```

### Agent Management

```go
// Register a new agent
agent, err := c.Agent.Register(ctx, &models.RegisterAgentRequest{
    Name:        "Content Moderation Agent",
    Description: "AI-powered content moderation",
    Type:        models.AgentTypeModeration,
    Capabilities: []string{"text_analysis", "image_recognition"},
    ResourceRequirements: &models.ResourceRequirements{
        CPU:    "2000m",
        Memory: "4Gi",
        GPU:    "1",
    },
})
if err != nil {
    log.Fatal("Failed to register agent:", err)
}

// Send heartbeat
heartbeat := &models.AgentHeartbeat{
    AgentID:     agent.ID,
    Timestamp:   time.Now(),
    Status:      models.AgentStatusActive,
    HealthScore: 0.95,
    Metrics: map[string]interface{}{
        "requests_processed": 1000,
        "average_latency":    150,
    },
}

err = c.Agent.SendHeartbeat(ctx, agent.ID, heartbeat)
if err != nil {
    log.Fatal("Failed to send heartbeat:", err)
}
```

### Tenant Management

```go
// List tenants (admin only)
tenants, err := c.Tenant.List(ctx, &models.TenantQuery{
    Status: &[]models.TenantStatus{models.TenantStatusActive}[0],
    Tier:   &[]models.TenantTier{models.TenantTierEnterprise}[0],
})
if err != nil {
    log.Fatal("Failed to list tenants:", err)
}

// Get tenant usage
usage, err := c.Tenant.GetUsage(ctx, "tenant-id")
if err != nil {
    log.Fatal("Failed to get tenant usage:", err)
}

log.Printf("Tenant usage: %+v", usage)
```

## ⚙️ Advanced Configuration

### Custom HTTP Client

```go
config := &client.Config{
    BaseURL:             "https://api.acgs2.com",
    TenantID:            "my-tenant-id",
    ConstitutionalHash:  "cdd01ef066bc6cf2",
    Timeout:             45 * time.Second,
    RetryAttempts:       5,
    RetryDelay:          2 * time.Second,
    EnableMetrics:       true,
    EnableTracing:       true,
    LogLevel:            "debug",
    TLSCertFile:         "/path/to/client.crt",
    TLSKeyFile:          "/path/to/client.key",
    CACertFile:          "/path/to/ca.crt",
}

client, err := client.New(config)
if err != nil {
    log.Fatal("Failed to create client:", err)
}
```

### Custom HTTP Transport

```go
config := client.NewConfig("https://api.acgs2.com", "my-tenant-id")

// Create custom HTTP client with proxy
proxyURL, _ := url.Parse("http://proxy.company.com:8080")
transport := &http.Transport{
    Proxy: http.ProxyURL(proxyURL),
    TLSClientConfig: &tls.Config{
        InsecureSkipVerify: false,
    },
}

httpClient := &http.Client{
    Transport: transport,
    Timeout:   config.Timeout,
}

// Use custom HTTP client (this would require internal API access)
// Note: This is a conceptual example
```

## 🔒 Security

### Authentication Methods

- **JWT Tokens**: Secure token-based authentication with automatic refresh
- **OAuth2/OIDC**: Industry-standard identity federation
- **Client Certificates**: Mutual TLS authentication
- **API Keys**: Service-to-service authentication

### Authorization

- **Role-Based Access Control (RBAC)**: Hierarchical permission system
- **Resource-Based Permissions**: Fine-grained access control
- **Multi-Tenant Isolation**: Complete data and operation isolation
- **Audit Logging**: Comprehensive security event logging

### Data Protection

- **End-to-End Encryption**: TLS 1.3 with perfect forward secrecy
- **Client Certificate Authentication**: Mutual TLS for high-security environments
- **Token Security**: Secure token storage and automatic rotation
- **Request Signing**: Optional request signing for additional security

## 📊 Monitoring

### Metrics Collection

The SDK automatically collects comprehensive metrics:

```go
// Get client metrics
metrics := client.Metrics()
log.Printf("Metrics: %+v", metrics)

// Get health status
health, err := client.Health(ctx)
if err != nil {
    log.Fatal("Health check failed:", err)
}

log.Printf("System health: %s", health.Status)
```

### Structured Logging

```go
// Logs are automatically structured with Zap
// Example log output:
{
  "level": "info",
  "ts": "2024-01-15T10:30:00Z",
  "caller": "client/policy.go:45",
  "msg": "policy created",
  "policy_id": "pol_123456",
  "policy_name": "Data Privacy Policy",
  "tenant_id": "my-tenant-id"
}
```

### Tracing

Enable distributed tracing for request correlation:

```go
config := client.NewConfig("https://api.acgs2.com", "my-tenant-id")
config.EnableTracing = true

client, err := client.New(config)
// All requests now include trace headers
```

## 🧪 Testing

### Mock Client

```go
// Create mock client for testing
mockClient := &MockClient{}

// Configure mock responses
mockClient.On("Policy.List", mock.Anything, mock.Anything).Return(mockPolicies, nil)

// Use in tests
policies, err := mockClient.Policy.List(ctx, nil)
assert.NoError(t, err)
assert.Len(t, policies.Data, 2)
```

### Integration Testing

```go
func TestPolicyLifecycle(t *testing.T) {
    config := client.NewConfig("http://localhost:8080", "test-tenant")
    config.EnableMetrics = false // Disable for tests

    c, err := client.New(config)
    require.NoError(t, err)

    // Test policy creation
    policy, err := c.Policy.Create(ctx, &models.CreatePolicyRequest{
        Name: "Test Policy",
        Type: models.PolicyTypeSecurity,
    })
    require.NoError(t, err)
    assert.NotEmpty(t, policy.ID)

    // Test policy retrieval
    retrieved, err := c.Policy.Get(ctx, policy.ID)
    require.NoError(t, err)
    assert.Equal(t, policy.Name, retrieved.Name)

    // Test policy deletion
    err = c.Policy.Delete(ctx, policy.ID)
    assert.NoError(t, err)
}
```

## 📚 API Reference

Complete API documentation is available at [godoc.org/github.com/acgs-project/acgs2-go-sdk](https://godoc.org/github.com/acgs-project/acgs2-go-sdk).

### Key Types

- [`Client`](https://godoc.org/github.com/acgs-project/acgs2-go-sdk/pkg/client#Client) - Main SDK client
- [`PolicyService`](https://godoc.org/github.com/acgs-project/acgs2-go-sdk/pkg/client#PolicyService) - Policy operations
- [`AuditService`](https://godoc.org/github.com/acgs-project/acgs2-go-sdk/pkg/client#AuditService) - Audit operations
- [`AgentService`](https://godoc.org/github.com/acgs-project/acgs2-go-sdk/pkg/client#AgentService) - Agent operations
- [`TenantService`](https://godoc.org/github.com/acgs-project/acgs2-go-sdk/pkg/client#TenantService) - Tenant operations

### Error Types

- `AuthenticationError` - Authentication failures
- `AuthorizationError` - Permission denied
- `ValidationError` - Input validation failures
- `QuotaExceededError` - Resource quota violations
- `RateLimitError` - API rate limit exceeded
- `NetworkError` - Network connectivity issues

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](../CONTRIBUTING.md) for details.

### Development Setup

```bash
git clone https://github.com/ACGS-Project/ACGS-2.git
cd ACGS-2/sdk/go

# Install dependencies
go mod download

# Run tests
go test ./...

# Run linter
golangci-lint run

# Generate documentation
go doc -all .
```

### Testing

```bash
# Run all tests
go test ./...

# Run tests with coverage
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out

# Run specific package tests
go test ./pkg/client/...

# Run benchmarks
go test -bench=. ./...
```

## 📄 License

Licensed under the Apache License 2.0. See [LICENSE](../LICENSE) for details.

## 🏢 Enterprise Support

For enterprise support, custom integrations, or professional services:

- 📧 Email: enterprise@acgs2.com
- 📞 Phone: +1 (555) 123-4567
- 🌐 Web: [acgs2.com/enterprise](https://acgs2.com/enterprise)

## 🔗 Links

- [Documentation](https://docs.acgs2.com/go-sdk)
- [API Reference](https://godoc.org/github.com/acgs-project/acgs2-go-sdk)
- [GitHub Repository](https://github.com/ACGS-Project/ACGS-2)
- [Issue Tracker](https://github.com/ACGS-Project/ACGS-2/issues)
- [Community Forum](https://community.acgs2.com)
- [Blog](https://blog.acgs2.com)

---

**ACGS-2**: Constitutional AI Governance for the Enterprise 🌟

**Constitutional Hash: cdd01ef066bc6cf2** ✅
