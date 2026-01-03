package http

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"time"

	"github.com/hashicorp/go-retryablehttp"
	"go.uber.org/zap"
)

// Client represents an HTTP client with retry logic
type Client struct {
	client   *retryablehttp.Client
	baseURL  string
	logger   *zap.Logger
}

// NewClient creates a new HTTP client
func NewClient(httpClient *http.Client, baseURL string, logger *zap.Logger) *Client {
	retryClient := retryablehttp.NewClient()
	retryClient.HTTPClient = httpClient
	retryClient.RetryMax = 3
	retryClient.RetryWaitMin = time.Second
	retryClient.RetryWaitMax = 30 * time.Second
	retryClient.Logger = &retryLogger{logger: logger}

	return &Client{
		client:  retryClient,
		baseURL: baseURL,
		logger:  logger,
	}
}

// Do performs an HTTP request
func (c *Client) Do(ctx context.Context, method, endpoint string, body interface{}, response interface{}) error {
	var bodyReader io.Reader
	if body != nil {
		bodyBytes, err := json.Marshal(body)
		if err != nil {
			return fmt.Errorf("failed to marshal request body: %w", err)
		}
		bodyReader = bytes.NewReader(bodyBytes)
	}

	fullURL := c.buildURL(endpoint)
	req, err := retryablehttp.NewRequestWithContext(ctx, method, fullURL, bodyReader)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")

	resp, err := c.client.Do(req)
	if err != nil {
		c.logger.Error("HTTP request failed",
			zap.String("method", method),
			zap.String("url", fullURL),
			zap.Error(err))
		return fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	// Read response body
	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("failed to read response body: %w", err)
	}

	// Check status code
	if resp.StatusCode >= 400 {
		var errorResp struct {
			Error   string                 `json:"error"`
			Message string                 `json:"message"`
			Code    string                 `json:"code,omitempty"`
			Details map[string]interface{} `json:"details,omitempty"`
		}

		if err := json.Unmarshal(respBody, &errorResp); err != nil {
			return fmt.Errorf("request failed with status %d: %s", resp.StatusCode, string(respBody))
		}

		c.logger.Error("API error response",
			zap.Int("status_code", resp.StatusCode),
			zap.String("error", errorResp.Error),
			zap.String("message", errorResp.Message),
			zap.String("code", errorResp.Code))

		return fmt.Errorf("API error [%s]: %s", errorResp.Error, errorResp.Message)
	}

	// Parse response if expected
	if response != nil {
		if err := json.Unmarshal(respBody, response); err != nil {
			return fmt.Errorf("failed to unmarshal response: %w", err)
		}
	}

	c.logger.Debug("HTTP request successful",
		zap.String("method", method),
		zap.String("url", fullURL),
		zap.Int("status_code", resp.StatusCode))

	return nil
}

// buildURL builds the full URL for the request
func (c *Client) buildURL(endpoint string) string {
	baseURL, _ := url.Parse(c.baseURL)
	endpointURL, _ := url.Parse(endpoint)

	return baseURL.ResolveReference(endpointURL).String()
}

// retryLogger implements retryablehttp.Logger
type retryLogger struct {
	logger *zap.Logger
}

func (l *retryLogger) Printf(format string, args ...interface{}) {
	l.logger.Debug(fmt.Sprintf(format, args...))
}

// SetRetryMax sets the maximum number of retries
func (c *Client) SetRetryMax(max int) {
	c.client.RetryMax = max
}

// SetRetryWaitMin sets the minimum retry wait time
func (c *Client) SetRetryWaitMin(wait time.Duration) {
	c.client.RetryWaitMin = wait
}

// SetRetryWaitMax sets the maximum retry wait time
func (c *Client) SetRetryWaitMax(wait time.Duration) {
	c.client.RetryWaitMax = wait
}
