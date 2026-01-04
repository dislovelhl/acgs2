package sdk

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
)

// APIGatewayService provides methods for interacting with the API Gateway
type APIGatewayService struct {
	client *ACGS2Client
}

// NewAPIGatewayService creates a new APIGatewayService instance
func NewAPIGatewayService(client *ACGS2Client) *APIGatewayService {
	return &APIGatewayService{
		client: client,
	}
}

// HealthCheck performs a health check on the API gateway
func (s *APIGatewayService) HealthCheck(ctx context.Context) (*HealthCheckResponse, error) {
	url := fmt.Sprintf("%s/health", s.client.config.BaseURL)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := s.client.doRequest(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var health HealthCheckResponse
	if err := json.NewDecoder(resp.Body).Decode(&health); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &health, nil
}

// SubmitFeedback submits user feedback
func (s *APIGatewayService) SubmitFeedback(ctx context.Context, req FeedbackRequest) (*FeedbackResponse, error) {
	url := fmt.Sprintf("%s/feedback", s.client.config.BaseURL)

	requestData := map[string]interface{}{
		"userId":             req.UserID,
		"category":           req.Category,
		"rating":             req.Rating,
		"title":              req.Title,
		"constitutionalHash": ConstitutionalHash,
	}

	if req.Description != nil {
		requestData["description"] = *req.Description
	}
	if req.Metadata != nil {
		requestData["metadata"] = req.Metadata
	}

	jsonData, err := json.Marshal(requestData)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	httpReq.Header.Set("Content-Type", "application/json")

	resp, err := s.client.doRequest(httpReq)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var feedbackResp FeedbackResponse
	if err := json.NewDecoder(resp.Body).Decode(&feedbackResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &feedbackResp, nil
}

// GetFeedbackStats retrieves feedback statistics
func (s *APIGatewayService) GetFeedbackStats(ctx context.Context) (*FeedbackStats, error) {
	url := fmt.Sprintf("%s/feedback/stats", s.client.config.BaseURL)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := s.client.doRequest(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var stats FeedbackStats
	if err := json.NewDecoder(resp.Body).Decode(&stats); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &stats, nil
}

// ListServices retrieves available services information
func (s *APIGatewayService) ListServices(ctx context.Context) (*ServicesResponse, error) {
	url := fmt.Sprintf("%s/services", s.client.config.BaseURL)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := s.client.doRequest(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var servicesResp ServicesResponse
	if err := json.NewDecoder(resp.Body).Decode(&servicesResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &servicesResp, nil
}
