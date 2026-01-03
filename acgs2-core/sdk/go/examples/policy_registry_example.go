package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"time"

	sdk "acgs2-sdk-go"
)

func main() {
	fmt.Println("🛡️  ACGS-2 Policy Registry Example")
	fmt.Println("=====================================")

	// Configuration
	config := sdk.ClientConfig{
		BaseURL:   "http://localhost:8080", // API Gateway URL
		TenantID:  "example-tenant",
		Timeout:   30 * time.Second,
		Retry: sdk.RetryConfig{
			MaxAttempts: 3,
			BaseDelay:   1 * time.Second,
			MaxDelay:    10 * time.Second,
		},
		// Add authentication as needed
		// APIKey: "your-api-key",
		// SVIDToken: "your-svid-token",
	}

	client := sdk.NewClient(config)
	defer client.Close()

	ctx := context.Background()

	// Get Policy Registry service
	policyService := client.PolicyRegistry()

	// 1. Health Check
	fmt.Println("\n1. Health Check")
	health, err := policyService.HealthCheck(ctx)
	if err != nil {
		log.Printf("Health check failed: %v", err)
	} else {
		fmt.Printf("   Status: %v\n", health)
	}

	// 2. List Policies
	fmt.Println("\n2. List Policies")
	policies, err := policyService.ListPolicies(ctx, nil, 5, 0)
	if err != nil {
		log.Printf("Failed to list policies: %v", err)
	} else {
		fmt.Printf("   Found %d policies\n", len(policies))
		if len(policies) > 0 {
			policy := policies[0]
			fmt.Printf("   Example: %s (Status: %s)\n", policy.Name, policy.Status)
		}
	}

	// 3. Create a Policy
	fmt.Println("\n3. Create Policy")
	newPolicy, err := policyService.CreatePolicy(ctx, sdk.CreatePolicyRequest{
		Name: "example-security-policy",
		Rules: []map[string]interface{}{
			{
				"effect":    "allow",
				"principal": "user:*",
				"action":    "read",
				"resource":  "document:*",
				"conditions": map[string]interface{}{
					"ip_address": map[string]interface{}{
						"type":  "CIDR",
						"value": "192.168.1.0/24",
					},
				},
			},
		},
		Description:   stringPtr("Example security policy with IP restrictions"),
		Tags:          []string{"security", "example"},
		ComplianceTags: []string{"gdpr", "sox"},
	})
	if err != nil {
		log.Printf("Failed to create policy: %v", err)
	} else {
		fmt.Printf("   Created policy: %s (ID: %s)\n", newPolicy.Name, newPolicy.ID)
		policyID := newPolicy.ID
		// Continue with other operations using this policy ID
		continueWithPolicyOperations(ctx, policyService, policyID)
	}

	fmt.Println("\n✅ Policy Registry example completed successfully!")
}

func continueWithPolicyOperations(ctx context.Context, policyService *sdk.PolicyRegistryService, policyID string) {
	// 4. Get Policy Details
	fmt.Println("\n4. Get Policy Details")
	policyDetails, err := policyService.GetPolicy(ctx, policyID)
	if err != nil {
		log.Printf("Failed to get policy details: %v", err)
	} else {
		fmt.Printf("   Policy: %s\n", policyDetails.Name)
		fmt.Printf("   Rules: %d\n", len(policyDetails.Rules))
		fmt.Printf("   Status: %s\n", policyDetails.Status)
	}

	// 5. Verify Policy
	fmt.Println("\n5. Verify Policy")
	verification, err := policyService.VerifyPolicy(ctx, policyID, sdk.PolicyVerificationRequest{
		Input: map[string]interface{}{
			"principal": "user:alice",
			"action":    "read",
			"resource":  "document:confidential",
			"context": map[string]interface{}{
				"ip_address": "192.168.1.100",
				"time":       "2024-01-15T10:00:00Z",
			},
		},
	})
	if err != nil {
		log.Printf("Failed to verify policy: %v", err)
	} else {
		status := "ALLOWED"
		if !verification.Allowed {
			status = "DENIED"
		}
		fmt.Printf("   Verification: %s\n", status)
	}

	// 6. Get Policy Versions
	fmt.Println("\n6. Get Policy Versions")
	versions, err := policyService.GetPolicyVersions(ctx, policyID)
	if err != nil {
		log.Printf("Failed to get policy versions: %v", err)
	} else {
		fmt.Printf("   Policy has %d versions\n", len(versions))
	}

	// 7. Create Policy Version
	fmt.Println("\n7. Create Policy Version")
	newVersion, err := policyService.CreatePolicyVersion(ctx, policyID, map[string]interface{}{
		"rules": []map[string]interface{}{
			{
				"effect":    "allow",
				"principal": "user:*",
				"action":    []string{"read", "write"},
				"resource":  "document:*",
				"conditions": map[string]interface{}{
					"ip_address": map[string]interface{}{
						"type":  "CIDR",
						"value": "192.168.1.0/24",
					},
					"department": map[string]interface{}{
						"type":  "StringEquals",
						"value": "engineering",
					},
				},
			},
		},
	}, stringPtr("Enhanced policy with write permissions and department restrictions"))
	if err != nil {
		log.Printf("Failed to create policy version: %v", err)
	} else {
		fmt.Printf("   Created version: %s\n", newVersion.Version)
	}

	// 8. List Policy Bundles
	fmt.Println("\n8. List Policy Bundles")
	bundles, err := policyService.ListBundles(ctx)
	if err != nil {
		log.Printf("Failed to list bundles: %v", err)
	} else {
		fmt.Printf("   Found %d bundles\n", len(bundles))
	}

	// 9. Create Policy Bundle
	fmt.Println("\n9. Create Policy Bundle")
	bundle, err := policyService.CreateBundle(ctx, sdk.CreateBundleRequest{
		Name:        "security-bundle",
		Policies:    []string{policyID},
		Description: stringPtr("Bundle containing security policies"),
	})
	if err != nil {
		log.Printf("Failed to create bundle: %v", err)
	} else {
		fmt.Printf("   Created bundle: %s (ID: %s)\n", bundle.Name, bundle.ID)

		// 10. Get Bundle Details
		fmt.Println("\n10. Get Bundle Details")
		bundleDetails, err := policyService.GetBundle(ctx, bundle.ID)
		if err != nil {
			log.Printf("Failed to get bundle details: %v", err)
		} else {
			fmt.Printf("   Bundle: %s\n", bundleDetails.Name)
			fmt.Printf("   Policies: %d\n", len(bundleDetails.Policies))
		}

		// 11. Get Active Bundle
		fmt.Println("\n11. Get Active Bundle")
		activeBundle, err := policyService.GetActiveBundle(ctx)
		if err != nil {
			log.Printf("Failed to get active bundle: %v", err)
		} else {
			fmt.Printf("   Active bundle: %s\n", activeBundle.Name)
		}
	}

	// 12. Authentication (if credentials provided)
	username := os.Getenv("ACGS2_USERNAME")
	password := os.Getenv("ACGS2_PASSWORD")

	if username != "" && password != "" {
		fmt.Println("\n12. Authentication")
		authResult, err := policyService.Authenticate(ctx, sdk.AuthRequest{
			Username: username,
			Password: password,
		})
		if err != nil {
			log.Printf("Authentication failed: %v", err)
		} else {
			fmt.Printf("   Authenticated as: %s\n", authResult.User.Username)
			fmt.Printf("   Roles: %s\n", fmt.Sprintf("%v", authResult.User.Roles))
		}
	}

	// 13. Cache Health Check
	fmt.Println("\n13. Cache Health Check")
	cacheHealth, err := policyService.CacheHealth(ctx)
	if err != nil {
		log.Printf("Cache health check failed: %v", err)
	} else {
		fmt.Printf("   Cache health: %v\n", cacheHealth)
	}
}

// Helper function to create string pointer
func stringPtr(s string) *string {
	return &s
}
