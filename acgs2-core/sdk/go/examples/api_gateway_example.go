package main

import (
	"context"
	"fmt"
	"log"
	"time"

	sdk "acgs2-sdk-go"
)

func main() {
	fmt.Println("🌐 ACGS-2 API Gateway Example")
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

	// Get API Gateway service
	gatewayService := client.APIGateway()

	// 1. Health Check
	fmt.Println("\n1. Health Check")
	health, err := gatewayService.HealthCheck(ctx)
	if err != nil {
		log.Printf("Health check failed: %v", err)
	} else {
		status := "Unhealthy"
		if health.Healthy {
			status = "Healthy"
		}
		fmt.Printf("   Status: %s\n", status)
		if health.Healthy {
			if health.Version != nil {
				fmt.Printf("   Version: %s\n", *health.Version)
			}
			fmt.Printf("   Constitutional Hash: %s\n", health.ConstitutionalHash)
		}
	}

	// 2. Submit Feedback
	fmt.Println("\n2. Submit Feedback")
	feedback, err := gatewayService.SubmitFeedback(ctx, sdk.FeedbackRequest{
		UserID:    "example-user-123",
		Category:  "feature",
		Rating:    5,
		Title:     "Excellent SDK Experience",
		Description: stringPtr("The new SDK makes integration much easier with comprehensive type safety and retry logic."),
		Metadata: map[string]interface{}{
			"sdk_version": "2.0.0",
			"language":    "go",
			"use_case":    "policy_management",
		},
	})
	if err != nil {
		log.Printf("Failed to submit feedback: %v", err)
	} else {
		fmt.Printf("   Feedback submitted with ID: %s\n", feedback.ID)
		fmt.Printf("   Status: %s\n", feedback.Status)
	}

	// 3. Get Feedback Statistics
	fmt.Println("\n3. Get Feedback Statistics")
	stats, err := gatewayService.GetFeedbackStats(ctx)
	if err != nil {
		log.Printf("Failed to get feedback stats: %v", err)
	} else {
		fmt.Printf("   Total feedback: %d\n", stats.TotalFeedback)
		fmt.Printf("   Average rating: %.1f/5.0\n", stats.AverageRating)

		if len(stats.CategoryBreakdown) > 0 {
			fmt.Println("   Category breakdown:")
			for category, count := range stats.CategoryBreakdown {
				fmt.Printf("     %s: %d\n", category, count)
			}
		}

		if len(stats.RecentFeedback) > 0 {
			fmt.Println("   Recent feedback:")
			// Show first 3 feedback items
			maxItems := 3
			if len(stats.RecentFeedback) < maxItems {
				maxItems = len(stats.RecentFeedback)
			}
			for i := 0; i < maxItems; i++ {
				fb := stats.RecentFeedback[i]
				fmt.Printf("     %d⭐ '%s' by %s\n", fb.Rating, fb.Title, fb.UserID)
			}
		}
	}

	// 4. List Available Services
	fmt.Println("\n4. Service Discovery")
	servicesResponse, err := gatewayService.ListServices(ctx)
	if err != nil {
		log.Printf("Failed to list services: %v", err)
	} else {
		fmt.Printf("   Gateway Version: %s\n", servicesResponse.Gateway.Version)
		fmt.Printf("   Uptime: %d seconds\n", servicesResponse.Gateway.Uptime)
		fmt.Printf("   Active Connections: %d\n", servicesResponse.Gateway.ActiveConnections)

		fmt.Printf("\n   Available Services (%d):\n", len(servicesResponse.Services))
		for _, service := range servicesResponse.Services {
			statusIcon := "✅"
			if service.Status == "degraded" {
				statusIcon = "⚠️"
			} else if service.Status == "unhealthy" {
				statusIcon = "❌"
			}

			fmt.Printf("     %s %s\n", statusIcon, service.Name)
			fmt.Printf("         Status: %s\n", service.Status)
			fmt.Printf("         Version: %s\n", service.Version)
			if service.Description != nil {
				fmt.Printf("         Description: %s\n", *service.Description)
			}
			if len(service.Endpoints) > 0 {
				endpointList := ""
				maxEndpoints := 3
				if len(service.Endpoints) < maxEndpoints {
					maxEndpoints = len(service.Endpoints)
				}
				for i := 0; i < maxEndpoints; i++ {
					if i > 0 {
						endpointList += ", "
					}
					endpointList += service.Endpoints[i]
				}
				if len(service.Endpoints) > maxEndpoints {
					endpointList += "..."
				}
				fmt.Printf("         Endpoints: %s\n", endpointList)
			}
		}
	}

	fmt.Println("\n✅ API Gateway example completed successfully!")
}

// Helper function to create string pointer
func stringPtr(s string) *string {
	return &s
}
