package client

import (
	"context"
	"fmt"
	"net/url"

	"go.uber.org/zap"

	"github.com/acgs-project/acgs2-go-sdk/internal/http"
	"github.com/acgs-project/acgs2-go-sdk/pkg/models"
)

// TenantService provides tenant management operations
type TenantService struct {
	client   *http.Client
	tenantID string
	logger   *zap.Logger
}

// NewTenantService creates a new tenant service
func NewTenantService(client *http.Client, tenantID string, logger *zap.Logger) *TenantService {
	return &TenantService{
		client:   client,
		tenantID: tenantID,
		logger:   logger,
	}
}

// List retrieves a list of tenants
func (s *TenantService) List(ctx context.Context, query *models.TenantQuery) (*models.ListResponse[models.Tenant], error) {
	endpoint := "/api/v1/tenants"

	if query != nil {
		params := url.Values{}
		if query.Status != nil {
			params.Add("status", string(*query.Status))
		}
		if query.Tier != nil {
			params.Add("tier", string(*query.Tier))
		}
		if query.Name != nil {
			params.Add("name", *query.Name)
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

	var response models.ListResponse[models.Tenant]
	if err := s.client.Do(ctx, "GET", endpoint, nil, &response); err != nil {
		s.logger.Error("failed to list tenants", zap.Error(err))
		return nil, fmt.Errorf("failed to list tenants: %w", err)
	}

	return &response, nil
}

// Get retrieves a tenant by ID
func (s *TenantService) Get(ctx context.Context, id string) (*models.Tenant, error) {
	endpoint := fmt.Sprintf("/api/v1/tenants/%s", id)

	var tenant models.Tenant
	if err := s.client.Do(ctx, "GET", endpoint, nil, &tenant); err != nil {
		s.logger.Error("failed to get tenant", zap.String("tenant_id", id), zap.Error(err))
		return nil, fmt.Errorf("failed to get tenant %s: %w", id, err)
	}

	return &tenant, nil
}

// Create creates a new tenant
func (s *TenantService) Create(ctx context.Context, req *models.CreateTenantRequest) (*models.Tenant, error) {
	endpoint := "/api/v1/tenants"

	var tenant models.Tenant
	if err := s.client.Do(ctx, "POST", endpoint, req, &tenant); err != nil {
		s.logger.Error("failed to create tenant", zap.Error(err))
		return nil, fmt.Errorf("failed to create tenant: %w", err)
	}

	s.logger.Info("tenant created", zap.String("tenant_id", tenant.ID), zap.String("tenant_name", tenant.Name))
	return &tenant, nil
}

// Update updates an existing tenant
func (s *TenantService) Update(ctx context.Context, id string, req *models.UpdateTenantRequest) (*models.Tenant, error) {
	endpoint := fmt.Sprintf("/api/v1/tenants/%s", id)

	var tenant models.Tenant
	if err := s.client.Do(ctx, "PUT", endpoint, req, &tenant); err != nil {
		s.logger.Error("failed to update tenant", zap.String("tenant_id", id), zap.Error(err))
		return nil, fmt.Errorf("failed to update tenant %s: %w", id, err)
	}

	s.logger.Info("tenant updated", zap.String("tenant_id", tenant.ID))
	return &tenant, nil
}

// Delete deletes a tenant
func (s *TenantService) Delete(ctx context.Context, id string) error {
	endpoint := fmt.Sprintf("/api/v1/tenants/%s", id)

	if err := s.client.Do(ctx, "DELETE", endpoint, nil, nil); err != nil {
		s.logger.Error("failed to delete tenant", zap.String("tenant_id", id), zap.Error(err))
		return fmt.Errorf("failed to delete tenant %s: %w", id, err)
	}

	s.logger.Info("tenant deleted", zap.String("tenant_id", id))
	return nil
}

// ValidateTenantAccess validates access to a tenant
func (s *TenantService) ValidateTenantAccess(ctx context.Context, tenantID string) error {
	endpoint := fmt.Sprintf("/api/v1/tenants/%s/validate-access", tenantID)

	if err := s.client.Do(ctx, "GET", endpoint, nil, nil); err != nil {
		s.logger.Error("tenant access validation failed", zap.String("tenant_id", tenantID), zap.Error(err))
		return fmt.Errorf("tenant access validation failed for %s: %w", tenantID, err)
	}

	return nil
}

// GetUsage retrieves tenant usage statistics
func (s *TenantService) GetUsage(ctx context.Context, id string) (map[string]interface{}, error) {
	endpoint := fmt.Sprintf("/api/v1/tenants/%s/usage", id)

	var usage map[string]interface{}
	if err := s.client.Do(ctx, "GET", endpoint, nil, &usage); err != nil {
		s.logger.Error("failed to get tenant usage", zap.String("tenant_id", id), zap.Error(err))
		return nil, fmt.Errorf("failed to get tenant usage for %s: %w", id, err)
	}

	return usage, nil
}

// GetQuota retrieves tenant quota information
func (s *TenantService) GetQuota(ctx context.Context, id string) (*models.ResourceQuota, error) {
	endpoint := fmt.Sprintf("/api/v1/tenants/%s/quota", id)

	var quota models.ResourceQuota
	if err := s.client.Do(ctx, "GET", endpoint, nil, &quota); err != nil {
		s.logger.Error("failed to get tenant quota", zap.String("tenant_id", id), zap.Error(err))
		return nil, fmt.Errorf("failed to get tenant quota for %s: %w", id, err)
	}

	return &quota, nil
}

// UpdateQuota updates tenant quota
func (s *TenantService) UpdateQuota(ctx context.Context, id string, quota *models.ResourceQuota) error {
	endpoint := fmt.Sprintf("/api/v1/tenants/%s/quota", id)

	if err := s.client.Do(ctx, "PUT", endpoint, quota, nil); err != nil {
		s.logger.Error("failed to update tenant quota", zap.String("tenant_id", id), zap.Error(err))
		return fmt.Errorf("failed to update tenant quota for %s: %w", id, err)
	}

	s.logger.Info("tenant quota updated", zap.String("tenant_id", id))
	return nil
}

// Health checks the tenant service health
func (s *TenantService) Health(ctx context.Context) (bool, error) {
	endpoint := "/health/tenants"

	var response map[string]interface{}
	if err := s.client.Do(ctx, "GET", endpoint, nil, &response); err != nil {
		return false, err
	}

	status, ok := response["status"].(string)
	return ok && status == "healthy", nil
}
