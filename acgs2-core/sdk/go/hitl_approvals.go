package sdk

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

// HITLApprovalsService provides methods for human-in-the-loop approval workflows
type HITLApprovalsService struct {
	client *ACGS2Client
}

// NewHITLApprovalsService creates a new HITL approvals service
func NewHITLApprovalsService(client *ACGS2Client) *HITLApprovalsService {
	return &HITLApprovalsService{client: client}
}

// CreateApprovalRequest creates a new approval request
func (s *HITLApprovalsService) CreateApprovalRequest(ctx context.Context, req CreateApprovalRequest) (*ApprovalRequest, error) {
	url := fmt.Sprintf("%s/api/v1/hitl-approvals/approvals", s.client.config.BaseURL)

	// Add constitutional hash
	requestData := struct {
		CreateApprovalRequest
		ConstitutionalHash string `json:"constitutionalHash"`
	}{
		CreateApprovalRequest: req,
		ConstitutionalHash:    "cdd01ef066bc6cf2",
	}

	jsonData, err := json.Marshal(requestData)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	s.client.setHeaders(httpReq)

	resp, err := s.client.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to execute request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusCreated {
		return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	var result ApprovalRequest
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// GetApprovalRequest retrieves an approval request by ID
func (s *HITLApprovalsService) GetApprovalRequest(ctx context.Context, requestID string) (*ApprovalRequest, error) {
	url := fmt.Sprintf("%s/api/v1/hitl-approvals/approvals/%s", s.client.config.BaseURL, requestID)

	httpReq, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	s.client.setHeaders(httpReq)

	resp, err := s.client.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to execute request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	var result ApprovalRequest
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// ListApprovalRequests lists approval requests with optional filtering
func (s *HITLApprovalsService) ListApprovalRequests(ctx context.Context, params map[string]interface{}) (*PaginatedResponse[ApprovalRequest], error) {
	url := fmt.Sprintf("%s/api/v1/hitl-approvals/approvals", s.client.config.BaseURL)

	// Build query parameters
	query := make(map[string]string)
	if page, ok := params["page"].(int); ok {
		query["page"] = fmt.Sprintf("%d", page)
	}
	if pageSize, ok := params["pageSize"].(int); ok {
		query["pageSize"] = fmt.Sprintf("%d", pageSize)
	}
	if status, ok := params["status"].(ApprovalStatus); ok {
		query["status"] = string(status)
	}
	if requesterID, ok := params["requesterId"].(string); ok {
		query["requesterId"] = requesterID
	}
	if pendingFor, ok := params["pendingFor"].(string); ok {
		query["pendingFor"] = pendingFor
	}

	// Add query parameters to URL
	if len(query) > 0 {
		url += "?"
		for key, value := range query {
			url += fmt.Sprintf("%s=%s&", key, value)
		}
		url = url[:len(url)-1] // Remove trailing &
	}

	httpReq, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	s.client.setHeaders(httpReq)

	resp, err := s.client.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to execute request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	var result PaginatedResponse[ApprovalRequest]
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// SubmitDecision submits an approval decision
func (s *HITLApprovalsService) SubmitDecision(ctx context.Context, requestID string, decision SubmitApprovalDecision) (*ApprovalRequest, error) {
	url := fmt.Sprintf("%s/api/v1/hitl-approvals/approvals/%s/decisions", s.client.config.BaseURL, requestID)

	requestData := struct {
		SubmitApprovalDecision
		Timestamp          string `json:"timestamp"`
		ConstitutionalHash string `json:"constitutionalHash"`
	}{
		SubmitApprovalDecision: decision,
		Timestamp:              time.Now().Format(time.RFC3339),
		ConstitutionalHash:     "cdd01ef066bc6cf2",
	}

	jsonData, err := json.Marshal(requestData)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	s.client.setHeaders(httpReq)

	resp, err := s.client.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to execute request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	var result ApprovalRequest
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// EscalateApprovalRequest escalates an approval request
func (s *HITLApprovalsService) EscalateApprovalRequest(ctx context.Context, requestID, reason string) (*ApprovalRequest, error) {
	url := fmt.Sprintf("%s/api/v1/hitl-approvals/approvals/%s/escalate", s.client.config.BaseURL, requestID)

	requestData := map[string]string{
		"reason": reason,
	}

	jsonData, err := json.Marshal(requestData)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	s.client.setHeaders(httpReq)

	resp, err := s.client.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to execute request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	var result ApprovalRequest
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// CancelApprovalRequest cancels an approval request
func (s *HITLApprovalsService) CancelApprovalRequest(ctx context.Context, requestID string, reason *string) error {
	url := fmt.Sprintf("%s/api/v1/hitl-approvals/approvals/%s/cancel", s.client.config.BaseURL, requestID)

	requestData := make(map[string]interface{})
	if reason != nil {
		requestData["reason"] = *reason
	}

	jsonData, err := json.Marshal(requestData)
	if err != nil {
		return fmt.Errorf("failed to marshal request: %w", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	s.client.setHeaders(httpReq)

	resp, err := s.client.httpClient.Do(httpReq)
	if err != nil {
		return fmt.Errorf("failed to execute request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	return nil
}

// GetPendingApprovals retrieves pending approvals for a user
func (s *HITLApprovalsService) GetPendingApprovals(ctx context.Context, userID string, params map[string]interface{}) (*PaginatedResponse[ApprovalRequest], error) {
	url := fmt.Sprintf("%s/api/v1/hitl-approvals/approvals/pending/%s", s.client.config.BaseURL, userID)

	// Build query parameters
	query := make(map[string]string)
	if page, ok := params["page"].(int); ok {
		query["page"] = fmt.Sprintf("%d", page)
	}
	if pageSize, ok := params["pageSize"].(int); ok {
		query["pageSize"] = fmt.Sprintf("%d", pageSize)
	}

	// Add query parameters to URL
	if len(query) > 0 {
		url += "?"
		for key, value := range query {
			url += fmt.Sprintf("%s=%s&", key, value)
		}
		url = url[:len(url)-1] // Remove trailing &
	}

	httpReq, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	s.client.setHeaders(httpReq)

	resp, err := s.client.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to execute request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	var result PaginatedResponse[ApprovalRequest]
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// GetApprovalWorkflowConfig retrieves approval workflow configuration
func (s *HITLApprovalsService) GetApprovalWorkflowConfig(ctx context.Context) (map[string]interface{}, error) {
	url := fmt.Sprintf("%s/api/v1/hitl-approvals/config", s.client.config.BaseURL)

	httpReq, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	s.client.setHeaders(httpReq)

	resp, err := s.client.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to execute request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return result, nil
}

// UpdateApprovalWorkflowConfig updates approval workflow configuration
func (s *HITLApprovalsService) UpdateApprovalWorkflowConfig(ctx context.Context, config map[string]interface{}) (map[string]interface{}, error) {
	url := fmt.Sprintf("%s/api/v1/hitl-approvals/config", s.client.config.BaseURL)

	requestData := map[string]interface{}{
		"config":             config,
		"constitutionalHash": "cdd01ef066bc6cf2",
	}

	jsonData, err := json.Marshal(requestData)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, "PUT", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	s.client.setHeaders(httpReq)

	resp, err := s.client.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to execute request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return result, nil
}

// GetApprovalMetrics retrieves approval workflow metrics
func (s *HITLApprovalsService) GetApprovalMetrics(ctx context.Context, startDate, endDate *string) (map[string]interface{}, error) {
	url := fmt.Sprintf("%s/api/v1/hitl-approvals/metrics", s.client.config.BaseURL)

	// Build query parameters
	query := make(map[string]string)
	if startDate != nil {
		query["startDate"] = *startDate
	}
	if endDate != nil {
		query["endDate"] = *endDate
	}

	// Add query parameters to URL
	if len(query) > 0 {
		url += "?"
		for key, value := range query {
			url += fmt.Sprintf("%s=%s&", key, value)
		}
		url = url[:len(url)-1] // Remove trailing &
	}

	httpReq, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	s.client.setHeaders(httpReq)

	resp, err := s.client.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to execute request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return result, nil
}
