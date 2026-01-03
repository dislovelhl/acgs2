package sdk

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

// RetryConfig holds retry configuration
type RetryConfig struct {
	MaxAttempts int           // Maximum number of retry attempts
	BaseDelay   time.Duration // Base delay between retries
	MaxDelay    time.Duration // Maximum delay between retries
}

// ClientConfig holds the configuration for the ACGS-2 client
type ClientConfig struct {
	BaseURL    string
	APIKey     string
	TenantID   string
	SVIDToken  string // SPIFFE Verifiable Identity Document (JWT)
	Timeout    time.Duration
	Retry      RetryConfig
}

// ACGS2Client is the main entry point for the Go SDK
type ACGS2Client struct {
	config     ClientConfig
	httpClient *http.Client

	// Services
	policyRegistry *PolicyRegistryService
	apiGateway     *APIGatewayService
}

// NewClient creates a new ACGS-2 client instance
func NewClient(config ClientConfig) *ACGS2Client {
	if config.Timeout == 0 {
		config.Timeout = 30 * time.Second
	}
	if config.Retry.MaxAttempts == 0 {
		config.Retry.MaxAttempts = 3
	}
	if config.Retry.BaseDelay == 0 {
		config.Retry.BaseDelay = 1 * time.Second
	}
	if config.Retry.MaxDelay == 0 {
		config.Retry.MaxDelay = 30 * time.Second
	}

	client := &ACGS2Client{
		config: config,
		httpClient: &http.Client{
			Timeout: config.Timeout,
		},
	}

	// Initialize services
	client.policyRegistry = NewPolicyRegistryService(client)
	client.apiGateway = NewAPIGatewayService(client)

	return client
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

	resp, err := c.doRequest(req)
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

// doRequest performs an HTTP request with retry logic
func (c *ACGS2Client) doRequest(req *http.Request) (*http.Response, error) {
	c.setHeaders(req)

	var lastErr error
	for attempt := 0; attempt < c.config.Retry.MaxAttempts; attempt++ {
		resp, err := c.httpClient.Do(req)
		if err == nil {
			// Check if it's a retryable error
			if resp.StatusCode >= 500 || resp.StatusCode == 429 {
				resp.Body.Close()
				if attempt < c.config.Retry.MaxAttempts-1 {
					// Calculate delay with exponential backoff
					delay := c.config.Retry.BaseDelay * time.Duration(1<<attempt)
					if delay > c.config.Retry.MaxDelay {
						delay = c.config.Retry.MaxDelay
					}

					time.Sleep(delay)
					continue
				}
			} else if resp.StatusCode >= 200 && resp.StatusCode < 300 {
				return resp, nil
			}
		}

		lastErr = err
		if attempt < c.config.Retry.MaxAttempts-1 {
			// Calculate delay with exponential backoff
			delay := c.config.Retry.BaseDelay * time.Duration(1<<attempt)
			if delay > c.config.Retry.MaxDelay {
				delay = c.config.Retry.MaxDelay
			}

			time.Sleep(delay)
		}
	}

	return nil, fmt.Errorf("request failed after %d attempts: %w", c.config.Retry.MaxAttempts, lastErr)
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

// PolicyRegistry returns the policy registry service
func (c *ACGS2Client) PolicyRegistry() *PolicyRegistryService {
	return c.policyRegistry
}

// APIGateway returns the API gateway service
func (c *ACGS2Client) APIGateway() *APIGatewayService {
	return c.apiGateway
}
