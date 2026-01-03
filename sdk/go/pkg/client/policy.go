package client

import (
	"context"
	"fmt"
	"net/url"

	"go.uber.org/zap"

	"github.com/acgs-project/acgs2-go-sdk/internal/http"
	"github.com/acgs-project/acgs2-go-sdk/pkg/models"
)

// PolicyService provides policy management operations
type PolicyService struct {
	client   *http.Client
	tenantID string
	logger   *zap.Logger
}

// NewPolicyService creates a new policy service
func NewPolicyService(client *http.Client, tenantID string, logger *zap.Logger) *PolicyService {
	return &PolicyService{
		client:   client,
		tenantID: tenantID,
		logger:   logger,
	}
}

// List retrieves a list of policies
func (s *PolicyService) List(ctx context.Context, query *models.PolicyQuery) (*models.ListResponse[models.Policy], error) {
	endpoint := "/api/v1/policies"

	if query != nil {
		params := url.Values{}
		if query.Status != nil {
			params.Add("status", string(*query.Status))
		}
		if query.Type != nil {
			params.Add("type", string(*query.Type))
		}
		if query.Severity != nil {
			params.Add("severity", string(*query.Severity))
		}
		if query.Name != nil {
			params.Add("name", *query.Name)
		}
		if query.Tag != nil {
			params.Add("tag", *query.Tag)
		}
		if query.Limit > 0 {
			params.Add("limit", fmt.Sprintf("%d", query.Limit))
		}
		if query.Offset > 0 {
			params.Add("offset", fmt.Sprintf("%d", query.Offset))
		}

		if len(params) > 0 {
			endpoint += "?" + params.Encode()
		}
	}

	var response models.ListResponse[models.Policy]
	if err := s.client.Do(ctx, "GET", endpoint, nil, &response); err != nil {
		s.logger.Error("failed to list policies", zap.Error(err))
		return nil, fmt.Errorf("failed to list policies: %w", err)
	}

	return &response, nil
}

// Get retrieves a policy by ID
func (s *PolicyService) Get(ctx context.Context, id string) (*models.Policy, error) {
	endpoint := fmt.Sprintf("/api/v1/policies/%s", id)

	var policy models.Policy
	if err := s.client.Do(ctx, "GET", endpoint, nil, &policy); err != nil {
		s.logger.Error("failed to get policy", zap.String("policy_id", id), zap.Error(err))
		return nil, fmt.Errorf("failed to get policy %s: %w", id, err)
	}

	return &policy, nil
}

// Create creates a new policy
func (s *PolicyService) Create(ctx context.Context, req *models.CreatePolicyRequest) (*models.Policy, error) {
	endpoint := "/api/v1/policies"

	var policy models.Policy
	if err := s.client.Do(ctx, "POST", endpoint, req, &policy); err != nil {
		s.logger.Error("failed to create policy", zap.Error(err))
		return nil, fmt.Errorf("failed to create policy: %w", err)
	}

	s.logger.Info("policy created", zap.String("policy_id", policy.ID), zap.String("policy_name", policy.Name))
	return &policy, nil
}

// Update updates an existing policy
func (s *PolicyService) Update(ctx context.Context, id string, req *models.UpdatePolicyRequest) (*models.Policy, error) {
	endpoint := fmt.Sprintf("/api/v1/policies/%s", id)

	var policy models.Policy
	if err := s.client.Do(ctx, "PUT", endpoint, req, &policy); err != nil {
		s.logger.Error("failed to update policy", zap.String("policy_id", id), zap.Error(err))
		return nil, fmt.Errorf("failed to update policy %s: %w", id, err)
	}

	s.logger.Info("policy updated", zap.String("policy_id", policy.ID))
	return &policy, nil
}

// Delete deletes a policy
func (s *PolicyService) Delete(ctx context.Context, id string) error {
	endpoint := fmt.Sprintf("/api/v1/policies/%s", id)

	if err := s.client.Do(ctx, "DELETE", endpoint, nil, nil); err != nil {
		s.logger.Error("failed to delete policy", zap.String("policy_id", id), zap.Error(err))
		return fmt.Errorf("failed to delete policy %s: %w", id, err)
	}

	s.logger.Info("policy deleted", zap.String("policy_id", id))
	return nil
}

// Validate validates a policy
func (s *PolicyService) Validate(ctx context.Context, policy *models.Policy) (*models.PolicyValidationResult, error) {
	endpoint := "/api/v1/policies/validate"

	var result models.PolicyValidationResult
	if err := s.client.Do(ctx, "POST", endpoint, policy, &result); err != nil {
		s.logger.Error("failed to validate policy", zap.Error(err))
		return nil, fmt.Errorf("failed to validate policy: %w", err)
	}

	return &result, nil
}

// Activate activates a policy
func (s *PolicyService) Activate(ctx context.Context, id string) error {
	endpoint := fmt.Sprintf("/api/v1/policies/%s/activate", id)

	if err := s.client.Do(ctx, "POST", endpoint, nil, nil); err != nil {
		s.logger.Error("failed to activate policy", zap.String("policy_id", id), zap.Error(err))
		return fmt.Errorf("failed to activate policy %s: %w", id, err)
	}

	s.logger.Info("policy activated", zap.String("policy_id", id))
	return nil
}

// Deactivate deactivates a policy
func (s *PolicyService) Deactivate(ctx context.Context, id string) error {
	endpoint := fmt.Sprintf("/api/v1/policies/%s/deactivate", id)

	if err := s.client.Do(ctx, "POST", endpoint, nil, nil); err != nil {
		s.logger.Error("failed to deactivate policy", zap.String("policy_id", id), zap.Error(err))
		return fmt.Errorf("failed to deactivate policy %s: %w", id, err)
	}

	s.logger.Info("policy deactivated", zap.String("policy_id", id))
	return nil
}

// GetVersions retrieves policy version history
func (s *PolicyService) GetVersions(ctx context.Context, id string) ([]models.Policy, error) {
	endpoint := fmt.Sprintf("/api/v1/policies/%s/versions", id)

	var versions []models.Policy
	if err := s.client.Do(ctx, "GET", endpoint, nil, &versions); err != nil {
		s.logger.Error("failed to get policy versions", zap.String("policy_id", id), zap.Error(err))
		return nil, fmt.Errorf("failed to get policy versions for %s: %w", id, err)
	}

	return versions, nil
}

// Clone creates a copy of a policy
func (s *PolicyService) Clone(ctx context.Context, id string, name string) (*models.Policy, error) {
	endpoint := fmt.Sprintf("/api/v1/policies/%s/clone", id)

	req := map[string]string{"name": name}
	var policy models.Policy
	if err := s.client.Do(ctx, "POST", endpoint, req, &policy); err != nil {
		s.logger.Error("failed to clone policy", zap.String("policy_id", id), zap.Error(err))
		return nil, fmt.Errorf("failed to clone policy %s: %w", id, err)
	}

	s.logger.Info("policy cloned", zap.String("original_id", id), zap.String("new_id", policy.ID))
	return &policy, nil
}

// Health checks the policy service health
func (s *PolicyService) Health(ctx context.Context) (bool, error) {
	endpoint := "/health/policy"

	var response map[string]interface{}
	if err := s.client.Do(ctx, "GET", endpoint, nil, &response); err != nil {
		s.logger.Error("policy service health check failed", zap.Error(err))
		return false, err
	}

	status, ok := response["status"].(string)
	return ok && status == "healthy", nil
}
