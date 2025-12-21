package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/acgs/sdk-go"
)

func main() {
	// 1. Initialize Client
	client := sdk.NewClient(sdk.ClientConfig{
		BaseURL:   "https://api.acgs.internal",
		TenantID:  "enterprise-01",
		SVIDToken: "ey...", // SVID token obtained from bootstrap
	})

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	// 2. Register Agent (Async)
	regCh := client.RegisterAgentAsync(ctx, "agent-007")
	if err := <-regCh; err != nil {
		log.Fatalf("Registration failed: %v", err)
	}
	fmt.Println("Agent registered successfully")

	// 3. Initialize High-Concurrency Dispatcher
	dispatcher := sdk.NewDispatcher(client, 5) // 5 parallel workers
	dispatcher.Start(ctx)

	// 4. Submit Multiple Messages
	messages := []sdk.AgentMessage{
		{
			ID:          "m1",
			FromAgent:   "agent-007",
			TenantID:    "enterprise-01",
			MessageType: sdk.MessageTypeCommand,
			Priority:    sdk.PriorityNormal,
			Content:     "Deploy container-v1",
		},
		{
			ID:          "m2",
			FromAgent:   "agent-007",
			TenantID:    "enterprise-01",
			MessageType: sdk.MessageTypeInquiry,
			Priority:    sdk.PriorityHigh,
			Content:     "Check budget status",
		},
	}

	for _, m := range messages {
		dispatcher.Submit(m)
	}

	// 5. Handle Results and Errors in parallel
	go func() {
		for res := range dispatcher.Results() {
			fmt.Printf("Message Validated: %v (Impact: %.2f)\n", res.IsValid, res.ImpactScore)
		}
	}()

	go func() {
		for err := range dispatcher.Errors() {
			log.Printf("Error: %v", err)
		}
	}()

	// Wait and Stop
	time.Sleep(2 * time.Second)
	dispatcher.Stop()
	fmt.Println("Dispatch complete.")
}
