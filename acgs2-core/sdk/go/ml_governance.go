package sdk

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
)

// MLGovernanceService provides methods for ML model governance and adaptive learning
type MLGovernanceService struct {
	client *ACGS2Client
}

// NewMLGovernanceService creates a new ML governance service
func NewMLGovernanceService(client *ACGS2Client) *MLGovernanceService {
	return &MLGovernanceService{client: client}
}

// CreateModel creates/registers a new ML model
func (s *MLGovernanceService) CreateModel(ctx context.Context, req CreateMLModelRequest) (*MLModel, error) {
	url := fmt.Sprintf("%s/api/v1/ml-governance/models", s.client.config.BaseURL)

	requestData := struct {
		CreateMLModelRequest
		ConstitutionalHash string `json:"constitutionalHash"`
	}{
		CreateMLModelRequest: req,
		ConstitutionalHash:   "cdd01ef066bc6cf2",
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

	var result MLModel
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// GetModel retrieves an ML model by ID
func (s *MLGovernanceService) GetModel(ctx context.Context, modelID string) (*MLModel, error) {
	url := fmt.Sprintf("%s/api/v1/ml-governance/models/%s", s.client.config.BaseURL, modelID)

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

	var result MLModel
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// ListModels lists ML models with optional filtering
func (s *MLGovernanceService) ListModels(ctx context.Context, params map[string]interface{}) (*PaginatedResponse[MLModel], error) {
	url := fmt.Sprintf("%s/api/v1/ml-governance/models", s.client.config.BaseURL)

	// Build query parameters
	query := make(map[string]string)
	if page, ok := params["page"].(int); ok {
		query["page"] = fmt.Sprintf("%d", page)
	}
	if pageSize, ok := params["pageSize"].(int); ok {
		query["pageSize"] = fmt.Sprintf("%d", pageSize)
	}
	if modelType, ok := params["modelType"].(string); ok {
		query["modelType"] = modelType
	}
	if framework, ok := params["framework"].(string); ok {
		query["framework"] = framework
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

	var result PaginatedResponse[MLModel]
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// UpdateModel updates an ML model
func (s *MLGovernanceService) UpdateModel(ctx context.Context, modelID string, req UpdateMLModelRequest) (*MLModel, error) {
	url := fmt.Sprintf("%s/api/v1/ml-governance/models/%s", s.client.config.BaseURL, modelID)

	requestData := struct {
		UpdateMLModelRequest
		ConstitutionalHash string `json:"constitutionalHash"`
	}{
		UpdateMLModelRequest: req,
		ConstitutionalHash:   "cdd01ef066bc6cf2",
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

	var result MLModel
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// DeleteModel deletes an ML model
func (s *MLGovernanceService) DeleteModel(ctx context.Context, modelID string) error {
	url := fmt.Sprintf("%s/api/v1/ml-governance/models/%s", s.client.config.BaseURL, modelID)

	httpReq, err := http.NewRequestWithContext(ctx, "DELETE", url, nil)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	s.client.setHeaders(httpReq)

	resp, err := s.client.httpClient.Do(httpReq)
	if err != nil {
		return fmt.Errorf("failed to execute request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusNoContent {
		return fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	return nil
}

// MakePrediction makes a prediction with an ML model
func (s *MLGovernanceService) MakePrediction(ctx context.Context, req MakePredictionRequest) (*ModelPrediction, error) {
	url := fmt.Sprintf("%s/api/v1/ml-governance/predictions", s.client.config.BaseURL)

	requestData := struct {
		MakePredictionRequest
		ConstitutionalHash string `json:"constitutionalHash"`
	}{
		MakePredictionRequest: req,
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

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	var result ModelPrediction
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// GetPrediction retrieves a prediction by ID
func (s *MLGovernanceService) GetPrediction(ctx context.Context, predictionID string) (*ModelPrediction, error) {
	url := fmt.Sprintf("%s/api/v1/ml-governance/predictions/%s", s.client.config.BaseURL, predictionID)

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

	var result ModelPrediction
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// ListPredictions lists model predictions with optional filtering
func (s *MLGovernanceService) ListPredictions(ctx context.Context, params map[string]interface{}) (*PaginatedResponse[ModelPrediction], error) {
	url := fmt.Sprintf("%s/api/v1/ml-governance/predictions", s.client.config.BaseURL)

	// Build query parameters
	query := make(map[string]string)
	if page, ok := params["page"].(int); ok {
		query["page"] = fmt.Sprintf("%d", page)
	}
	if pageSize, ok := params["pageSize"].(int); ok {
		query["pageSize"] = fmt.Sprintf("%d", pageSize)
	}
	if modelID, ok := params["modelId"].(string); ok {
		query["modelId"] = modelID
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

	var result PaginatedResponse[ModelPrediction]
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// SubmitFeedback submits feedback for model training
func (s *MLGovernanceService) SubmitFeedback(ctx context.Context, req SubmitFeedbackRequest) (*FeedbackSubmission, error) {
	url := fmt.Sprintf("%s/api/v1/ml-governance/feedback", s.client.config.BaseURL)

	requestData := struct {
		SubmitFeedbackRequest
		ConstitutionalHash string `json:"constitutionalHash"`
	}{
		SubmitFeedbackRequest: req,
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

	var result FeedbackSubmission
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// GetFeedback retrieves feedback by ID
func (s *MLGovernanceService) GetFeedback(ctx context.Context, feedbackID string) (*FeedbackSubmission, error) {
	url := fmt.Sprintf("%s/api/v1/ml-governance/feedback/%s", s.client.config.BaseURL, feedbackID)

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

	var result FeedbackSubmission
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// ListFeedback lists feedback submissions with optional filtering
func (s *MLGovernanceService) ListFeedback(ctx context.Context, params map[string]interface{}) (*PaginatedResponse[FeedbackSubmission], error) {
	url := fmt.Sprintf("%s/api/v1/ml-governance/feedback", s.client.config.BaseURL)

	// Build query parameters
	query := make(map[string]string)
	if page, ok := params["page"].(int); ok {
		query["page"] = fmt.Sprintf("%d", page)
	}
	if pageSize, ok := params["pageSize"].(int); ok {
		query["pageSize"] = fmt.Sprintf("%d", pageSize)
	}
	if modelID, ok := params["modelId"].(string); ok {
		query["modelId"] = modelID
	}
	if feedbackType, ok := params["feedbackType"].(string); ok {
		query["feedbackType"] = feedbackType
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

	var result PaginatedResponse[FeedbackSubmission]
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// CheckDrift checks for model drift
func (s *MLGovernanceService) CheckDrift(ctx context.Context, modelID string) (*DriftDetection, error) {
	url := fmt.Sprintf("%s/api/v1/ml-governance/models/%s/drift", s.client.config.BaseURL, modelID)

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

	var result DriftDetection
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// RetrainModel triggers model retraining
func (s *MLGovernanceService) RetrainModel(ctx context.Context, modelID string, feedbackThreshold *int) (map[string]interface{}, error) {
	url := fmt.Sprintf("%s/api/v1/ml-governance/models/%s/retrain", s.client.config.BaseURL, modelID)

	requestData := map[string]interface{}{
		"constitutionalHash": "cdd01ef066bc6cf2",
	}
	if feedbackThreshold != nil {
		requestData["feedbackThreshold"] = *feedbackThreshold
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

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return result, nil
}

// CreateABNTest creates an A/B test
func (s *MLGovernanceService) CreateABNTest(ctx context.Context, req CreateABNTestRequest) (*ABNTest, error) {
	url := fmt.Sprintf("%s/api/v1/ml-governance/ab-tests", s.client.config.BaseURL)

	requestData := struct {
		CreateABNTestRequest
		ConstitutionalHash string `json:"constitutionalHash"`
	}{
		CreateABNTestRequest: req,
		ConstitutionalHash:   "cdd01ef066bc6cf2",
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

	var result ABNTest
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// GetABNTest retrieves an A/B test by ID
func (s *MLGovernanceService) GetABNTest(ctx context.Context, testID string) (*ABNTest, error) {
	url := fmt.Sprintf("%s/api/v1/ml-governance/ab-tests/%s", s.client.config.BaseURL, testID)

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

	var result ABNTest
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// ListABNTests lists A/B tests
func (s *MLGovernanceService) ListABNTests(ctx context.Context, params map[string]interface{}) (*PaginatedResponse[ABNTest], error) {
	url := fmt.Sprintf("%s/api/v1/ml-governance/ab-tests", s.client.config.BaseURL)

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

	var result PaginatedResponse[ABNTest]
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// StopABNTest stops an A/B test
func (s *MLGovernanceService) StopABNTest(ctx context.Context, testID string) (*ABNTest, error) {
	url := fmt.Sprintf("%s/api/v1/ml-governance/ab-tests/%s/stop", s.client.config.BaseURL, testID)

	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, nil)
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

	var result ABNTest
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// GetABNTestResults retrieves A/B test results
func (s *MLGovernanceService) GetABNTestResults(ctx context.Context, testID string) (map[string]interface{}, error) {
	url := fmt.Sprintf("%s/api/v1/ml-governance/ab-tests/%s/results", s.client.config.BaseURL, testID)

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

// GetModelMetrics retrieves model performance metrics
func (s *MLGovernanceService) GetModelMetrics(ctx context.Context, modelID string, startDate, endDate *string) (map[string]interface{}, error) {
	url := fmt.Sprintf("%s/api/v1/ml-governance/models/%s/metrics", s.client.config.BaseURL, modelID)

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

// GetDashboardData retrieves ML governance dashboard data
func (s *MLGovernanceService) GetDashboardData(ctx context.Context) (map[string]interface{}, error) {
	url := fmt.Sprintf("%s/api/v1/ml-governance/dashboard", s.client.config.BaseURL)

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
