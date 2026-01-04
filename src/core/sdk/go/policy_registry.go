package sdk

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
)

const (
	// ConstitutionalHash is the required hash for all ACGS-2 operations
	ConstitutionalHash = "cdd01ef066bc6cf2"
)

// PolicyRegistryService provides methods for managing policies through the Policy Registry API
type PolicyRegistryService struct {
	client *ACGS2Client
}

// NewPolicyRegistryService creates a new PolicyRegistryService instance
func NewPolicyRegistryService(client *ACGS2Client) *PolicyRegistryService {
	return &PolicyRegistryService{
		client: client,
	}
}

// ListPolicies retrieves a list of policies with optional filtering
func (s *PolicyRegistryService) ListPolicies(ctx context.Context, status *PolicyStatus, limit, offset int) ([]Policy, error) {
	url := fmt.Sprintf("%s/api/v1/policies", s.client.config.BaseURL)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Add query parameters
	q := req.URL.Query()
	if status != nil {
		q.Add("status", string(*status))
	}
	if limit > 0 {
		q.Add("limit", fmt.Sprintf("%d", limit))
	}
	if offset > 0 {
		q.Add("offset", fmt.Sprintf("%d", offset))
	}
	req.URL.RawQuery = q.Encode()

	resp, err := s.client.doRequest(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var policies []Policy
	if err := json.NewDecoder(resp.Body).Decode(&policies); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return policies, nil
}

// CreatePolicy creates a new policy
func (s *PolicyRegistryService) CreatePolicy(ctx context.Context, req CreatePolicyRequest) (*Policy, error) {
	url := fmt.Sprintf("%s/api/v1/policies", s.client.config.BaseURL)

	requestData := map[string]interface{}{
		"name":              req.Name,
		"content":           map[string]interface{}{"rules": req.Rules},
		"format":            "json",
		"constitutionalHash": ConstitutionalHash,
	}

	if req.Description != nil {
		requestData["description"] = *req.Description
	}
	if len(req.Tags) > 0 {
		requestData["tags"] = req.Tags
	}
	if len(req.ComplianceTags) > 0 {
		requestData["complianceTags"] = req.ComplianceTags
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

	var policy Policy
	if err := json.NewDecoder(resp.Body).Decode(&policy); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &policy, nil
}

// GetPolicy retrieves a policy by ID
func (s *PolicyRegistryService) GetPolicy(ctx context.Context, policyID string) (*Policy, error) {
	url := fmt.Sprintf("%s/api/v1/policies/%s", s.client.config.BaseURL, policyID)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := s.client.doRequest(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var policy Policy
	if err := json.NewDecoder(resp.Body).Decode(&policy); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &policy, nil
}

// UpdatePolicy updates an existing policy
func (s *PolicyRegistryService) UpdatePolicy(ctx context.Context, policyID string, req UpdatePolicyRequest) (*Policy, error) {
	url := fmt.Sprintf("%s/api/v1/policies/%s", s.client.config.BaseURL, policyID)

	updateData := make(map[string]interface{})
	if req.Name != nil {
		updateData["name"] = *req.Name
	}
	if req.Description != nil {
		updateData["description"] = *req.Description
	}
	if len(req.Rules) > 0 {
		updateData["rules"] = req.Rules
	}
	if req.Status != nil {
		updateData["status"] = string(*req.Status)
	}
	if len(req.Tags) > 0 {
		updateData["tags"] = req.Tags
	}
	if len(req.ComplianceTags) > 0 {
		updateData["complianceTags"] = req.ComplianceTags
	}
	updateData["constitutionalHash"] = ConstitutionalHash

	jsonData, err := json.Marshal(updateData)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, "PATCH", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	httpReq.Header.Set("Content-Type", "application/json")

	resp, err := s.client.doRequest(httpReq)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var policy Policy
	if err := json.NewDecoder(resp.Body).Decode(&policy); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &policy, nil
}

// ActivatePolicy activates a policy
func (s *PolicyRegistryService) ActivatePolicy(ctx context.Context, policyID string) (*Policy, error) {
	url := fmt.Sprintf("%s/api/v1/policies/%s/activate", s.client.config.BaseURL, policyID)

	requestData := map[string]string{
		"constitutionalHash": ConstitutionalHash,
	}

	jsonData, err := json.Marshal(requestData)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, "PUT", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := s.client.doRequest(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var policy Policy
	if err := json.NewDecoder(resp.Body).Decode(&policy); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &policy, nil
}

// VerifyPolicy verifies input against a policy
func (s *PolicyRegistryService) VerifyPolicy(ctx context.Context, policyID string, req PolicyVerificationRequest) (*PolicyVerificationResponse, error) {
	url := fmt.Sprintf("%s/api/v1/policies/%s/verify", s.client.config.BaseURL, policyID)

	jsonData, err := json.Marshal(req)
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

	var result PolicyVerificationResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// GetPolicyContent retrieves raw policy content
func (s *PolicyRegistryService) GetPolicyContent(ctx context.Context, policyID string) (interface{}, error) {
	url := fmt.Sprintf("%s/api/v1/policies/%s/content", s.client.config.BaseURL, policyID)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := s.client.doRequest(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var content interface{}
	if err := json.NewDecoder(resp.Body).Decode(&content); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return content, nil
}

// GetPolicyVersions retrieves policy version history
func (s *PolicyRegistryService) GetPolicyVersions(ctx context.Context, policyID string) ([]PolicyVersion, error) {
	url := fmt.Sprintf("%s/api/v1/policies/%s/versions", s.client.config.BaseURL, policyID)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := s.client.doRequest(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var versions []PolicyVersion
	if err := json.NewDecoder(resp.Body).Decode(&versions); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return versions, nil
}

// CreatePolicyVersion creates a new policy version
func (s *PolicyRegistryService) CreatePolicyVersion(ctx context.Context, policyID string, content interface{}, description *string) (*PolicyVersion, error) {
	url := fmt.Sprintf("%s/api/v1/policies/%s/versions", s.client.config.BaseURL, policyID)

	requestData := map[string]interface{}{
		"content":            content,
		"constitutionalHash": ConstitutionalHash,
	}

	if description != nil {
		requestData["description"] = *description
	}

	jsonData, err := json.Marshal(requestData)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := s.client.doRequest(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var version PolicyVersion
	if err := json.NewDecoder(resp.Body).Decode(&version); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &version, nil
}

// GetPolicyVersion retrieves a specific policy version
func (s *PolicyRegistryService) GetPolicyVersion(ctx context.Context, policyID, version string) (*PolicyVersion, error) {
	url := fmt.Sprintf("%s/api/v1/policies/%s/versions/%s", s.client.config.BaseURL, policyID, version)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := s.client.doRequest(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var policyVersion PolicyVersion
	if err := json.NewDecoder(resp.Body).Decode(&policyVersion); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &policyVersion, nil
}

// Authenticate performs user authentication
func (s *PolicyRegistryService) Authenticate(ctx context.Context, req AuthRequest) (*AuthResponse, error) {
	url := fmt.Sprintf("%s/api/v1/auth/token", s.client.config.BaseURL)

	jsonData, err := json.Marshal(req)
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

	var authResp AuthResponse
	if err := json.NewDecoder(resp.Body).Decode(&authResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &authResp, nil
}

// ListBundles retrieves all policy bundles
func (s *PolicyRegistryService) ListBundles(ctx context.Context) ([]PolicyBundle, error) {
	url := fmt.Sprintf("%s/api/v1/bundles", s.client.config.BaseURL)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := s.client.doRequest(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var bundles []PolicyBundle
	if err := json.NewDecoder(resp.Body).Decode(&bundles); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return bundles, nil
}

// CreateBundle creates a new policy bundle
func (s *PolicyRegistryService) CreateBundle(ctx context.Context, req CreateBundleRequest) (*PolicyBundle, error) {
	url := fmt.Sprintf("%s/api/v1/bundles", s.client.config.BaseURL)

	requestData := map[string]interface{}{
		"name":               req.Name,
		"policies":           req.Policies,
		"constitutionalHash": ConstitutionalHash,
	}

	if req.Description != nil {
		requestData["description"] = *req.Description
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

	var bundle PolicyBundle
	if err := json.NewDecoder(resp.Body).Decode(&bundle); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &bundle, nil
}

// GetBundle retrieves a policy bundle by ID
func (s *PolicyRegistryService) GetBundle(ctx context.Context, bundleID string) (*PolicyBundle, error) {
	url := fmt.Sprintf("%s/api/v1/bundles/%s", s.client.config.BaseURL, bundleID)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := s.client.doRequest(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var bundle PolicyBundle
	if err := json.NewDecoder(resp.Body).Decode(&bundle); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &bundle, nil
}

// GetActiveBundle retrieves the currently active policy bundle
func (s *PolicyRegistryService) GetActiveBundle(ctx context.Context) (*PolicyBundle, error) {
	url := fmt.Sprintf("%s/api/v1/bundles/active", s.client.config.BaseURL)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := s.client.doRequest(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var bundle PolicyBundle
	if err := json.NewDecoder(resp.Body).Decode(&bundle); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &bundle, nil
}

// HealthCheck performs a health check on the policy registry
func (s *PolicyRegistryService) HealthCheck(ctx context.Context) (map[string]interface{}, error) {
	url := fmt.Sprintf("%s/api/v1/health/policies", s.client.config.BaseURL)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := s.client.doRequest(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var health map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&health); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return health, nil
}

// CacheHealth checks cache health
func (s *PolicyRegistryService) CacheHealth(ctx context.Context) (map[string]interface{}, error) {
	url := fmt.Sprintf("%s/api/v1/health/cache", s.client.config.BaseURL)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := s.client.doRequest(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var health map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&health); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return health, nil
}

// ConnectionsHealth checks connections health
func (s *PolicyRegistryService) ConnectionsHealth(ctx context.Context) (map[string]interface{}, error) {
	url := fmt.Sprintf("%s/api/v1/health/connections", s.client.config.BaseURL)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := s.client.doRequest(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var health map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&health); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return health, nil
}
