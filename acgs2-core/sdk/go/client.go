package sdk

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

// ClientConfig holds the configuration for the ACGS-2 client
type ClientConfig struct {
	BaseURL    string
	APIKey     string
	TenantID   string
	SVIDToken  string // SPIFFE Verifiable Identity Document (JWT)
	Timeout    time.Duration
}

// ACGS2Client is the main entry point for the Go SDK
type ACGS2Client struct {
	config     ClientConfig
	httpClient *http.Client
}

// NewClient creates a new ACGS-2 client instance
func NewClient(config ClientConfig) *ACGS2Client {
	if config.Timeout == 0 {
		config.Timeout = 30 * time.Second
	}
	return &ACGS2Client{
		config: config,
		httpClient: &http.Client{
			Timeout: config.Timeout,
		},
	}
}

// SendMessage sends a message to the agent bus
func (c *ACGS2Client) SendMessage(ctx context.Context, msg AgentMessage) (*ValidationResult, error) {
	url := fmt.Sprintf("%s/v1/messages", c.config.BaseURL)

	jsonData, err := json.Marshal(msg)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal message: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	c.setHeaders(req)

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to execute request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusAccepted {
		return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	var result ValidationResult
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// setHeaders adds authentication and tenant headers to the request
func (c *ACGS2Client) setHeaders(req *http.Request) {
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Constitutional-Hash", "cdd01ef066bc6cf2")
	req.Header.Set("X-SDK-Version", "2.0.0")
	req.Header.Set("X-SDK-Language", "go")
	if c.config.APIKey != "" {
		req.Header.Set("X-API-Key", c.config.APIKey)
	}
	if c.config.SVIDToken != "" {
		req.Header.Set("Authorization", "Bearer "+c.config.SVIDToken)
	}
	if c.config.TenantID != "" {
		req.Header.Set("X-Tenant-ID", c.config.TenantID)
	}
}

// RegisterAgent async helper for non-blocking registration
func (c *ACGS2Client) RegisterAgentAsync(ctx context.Context, agentID string) <-chan error {
	errCh := make(chan error, 1)
	go func() {
		defer close(errCh)
		url := fmt.Sprintf("%s/v1/agents/register", c.config.BaseURL)

		reg := map[string]string{
			"agent_id":  agentID,
			"tenant_id": c.config.TenantID,
		}

		jsonData, _ := json.Marshal(reg)
		req, _ := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(jsonData))
		c.setHeaders(req)

		resp, err := c.httpClient.Do(req)
		if err != nil {
			errCh <- err
			return
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			errCh <- fmt.Errorf("registration failed with status: %d", resp.StatusCode)
		}
	}()
	return errCh
}
