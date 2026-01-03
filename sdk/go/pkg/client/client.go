// Package client provides the main ACGS-2 Go SDK client
package client

import (
	"context"
	"crypto/tls"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"go.uber.org/zap"

	"github.com/acgs-project/acgs2-go-sdk/internal/http"
	"github.com/acgs-project/acgs2-go-sdk/pkg/auth"
	"github.com/acgs-project/acgs2-go-sdk/pkg/models"
)

// Client represents the ACGS-2 API client
type Client struct {
	config     *Config
	httpClient *http.Client
	logger     *zap.Logger

	// Services
	Auth   *auth.Service
	Policy *PolicyService
	Audit  *AuditService
	Agent  *AgentService
	Tenant *TenantService
}

// Config holds client configuration
type Config struct {
	// Base configuration
	BaseURL         string        `yaml:"base_url"`
	Timeout         time.Duration `yaml:"timeout"`
	RetryAttempts   int           `yaml:"retry_attempts"`
	RetryDelay      time.Duration `yaml:"retry_delay"`
	ConstitutionalHash string     `yaml:"constitutional_hash"`

	// Authentication
	TenantID string `yaml:"tenant_id"`

	// TLS configuration
	TLSCertFile string `yaml:"tls_cert_file"`
	TLSKeyFile  string `yaml:"tls_key_file"`
	CACertFile  string `yaml:"ca_cert_file"`
	InsecureTLS bool   `yaml:"insecure_tls"`

	// Monitoring
	EnableMetrics bool `yaml:"enable_metrics"`
	EnableTracing bool `yaml:"enable_tracing"`

	// Logging
	LogLevel string `yaml:"log_level"`
}

// NewConfig creates a new client configuration with defaults
func NewConfig(baseURL, tenantID string) *Config {
	return &Config{
		BaseURL:           baseURL,
		TenantID:          tenantID,
		Timeout:           30 * time.Second,
		RetryAttempts:     3,
		RetryDelay:        time.Second,
		ConstitutionalHash: "cdd01ef066bc6cf2",
		EnableMetrics:     true,
		EnableTracing:     true,
		LogLevel:          "info",
		InsecureTLS:       false,
	}
}

// New creates a new ACGS-2 client
func New(config *Config) (*Client, error) {
	// Validate configuration
	if err := validateConfig(config); err != nil {
		return nil, fmt.Errorf("invalid configuration: %w", err)
	}

	// Setup logger
	logger, err := setupLogger(config.LogLevel)
	if err != nil {
		return nil, fmt.Errorf("failed to setup logger: %w", err)
	}

	// Setup HTTP client
	httpClient, err := setupHTTPClient(config)
	if err != nil {
		return nil, fmt.Errorf("failed to setup HTTP client: %w", err)
	}

	// Create internal HTTP client
	internalClient := http.NewClient(httpClient, config.BaseURL, logger)

	// Create client
	client := &Client{
		config:     config,
		httpClient: httpClient,
		logger:     logger,
	}

	// Initialize services
	client.Auth = auth.NewService(internalClient, config.TenantID, logger)
	client.Policy = NewPolicyService(internalClient, config.TenantID, logger)
	client.Audit = NewAuditService(internalClient, config.TenantID, logger)
	client.Agent = NewAgentService(internalClient, config.TenantID, logger)
	client.Tenant = NewTenantService(internalClient, config.TenantID, logger)

	return client, nil
}

// Health performs a health check
func (c *Client) Health(ctx context.Context) (*models.HealthStatus, error) {
	endpoint := "/health"

	var response models.HealthStatus
	if err := c.doRequest(ctx, "GET", endpoint, nil, &response); err != nil {
		return nil, fmt.Errorf("health check failed: %w", err)
	}

	return &response, nil
}

// Metrics returns client metrics
func (c *Client) Metrics() map[string]interface{} {
	return map[string]interface{}{
		"tenant_id":          c.config.TenantID,
		"base_url":           c.config.BaseURL,
		"timeout":            c.config.Timeout.String(),
		"retry_attempts":     c.config.RetryAttempts,
		"enable_metrics":     c.config.EnableMetrics,
		"enable_tracing":     c.config.EnableTracing,
		"timestamp":          time.Now().UTC().Format(time.RFC3339),
	}
}

// Close closes the client and cleans up resources
func (c *Client) Close() error {
	if c.httpClient != nil {
		c.httpClient.CloseIdleConnections()
	}
	return nil
}

// doRequest performs an HTTP request
func (c *Client) doRequest(ctx context.Context, method, endpoint string, body interface{}, response interface{}) error {
	req, err := http.NewRequest(ctx, method, endpoint, body)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	// Add tenant headers
	req.Header.Set("X-Tenant-ID", c.config.TenantID)
	req.Header.Set("X-Constitutional-Hash", c.config.ConstitutionalHash)
	req.Header.Set("Content-Type", "application/json")

	// Add tracing headers if enabled
	if c.config.EnableTracing {
		req.Header.Set("X-Trace-ID", generateTraceID())
		req.Header.Set("X-Span-ID", generateSpanID())
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		return fmt.Errorf("request failed with status %d", resp.StatusCode)
	}

	if response != nil {
		if err := json.NewDecoder(resp.Body).Decode(response); err != nil {
			return fmt.Errorf("failed to decode response: %w", err)
		}
	}

	return nil
}

// validateConfig validates the client configuration
func validateConfig(config *Config) error {
	if config.BaseURL == "" {
		return fmt.Errorf("base URL is required")
	}
	if config.TenantID == "" {
		return fmt.Errorf("tenant ID is required")
	}
	if config.ConstitutionalHash != "cdd01ef066bc6cf2" {
		return fmt.Errorf("invalid constitutional hash")
	}
	return nil
}

// setupLogger creates a configured logger
func setupLogger(level string) (*zap.Logger, error) {
	config := zap.NewProductionConfig()
	config.Level = zap.NewAtomicLevelAt(parseLogLevel(level))

	return config.Build()
}

// setupHTTPClient creates a configured HTTP client
func setupHTTPClient(config *Config) (*http.Client, error) {
	transport := &http.Transport{
		TLSClientConfig: &tls.Config{
			InsecureSkipVerify: config.InsecureTLS,
		},
	}

	// Load client certificates if provided
	if config.TLSCertFile != "" && config.TLSKeyFile != "" {
		cert, err := tls.LoadX509KeyPair(config.TLSCertFile, config.TLSKeyFile)
		if err != nil {
			return nil, fmt.Errorf("failed to load client certificate: %w", err)
		}
		transport.TLSClientConfig.Certificates = []tls.Certificate{cert}
	}

	return &http.Client{
		Timeout:   config.Timeout,
		Transport: transport,
	}, nil
}

// parseLogLevel parses log level string
func parseLogLevel(level string) zap.AtomicLevel {
	switch level {
	case "debug":
		return zap.NewAtomicLevelAt(zap.DebugLevel)
	case "info":
		return zap.NewAtomicLevelAt(zap.InfoLevel)
	case "warn", "warning":
		return zap.NewAtomicLevelAt(zap.WarnLevel)
	case "error":
		return zap.NewAtomicLevelAt(zap.ErrorLevel)
	case "fatal":
		return zap.NewAtomicLevelAt(zap.FatalLevel)
	default:
		return zap.NewAtomicLevelAt(zap.InfoLevel)
	}
}

// generateTraceID generates a random trace ID
func generateTraceID() string {
	return fmt.Sprintf("%x", time.Now().UnixNano())
}

// generateSpanID generates a random span ID
func generateSpanID() string {
	return fmt.Sprintf("%x", time.Now().UnixNano()&0xFFFFFFFF)
}
