package client

import (
	"context"
	"fmt"
	"net/url"

	"go.uber.org/zap"

	"github.com/acgs-project/acgs2-go-sdk/internal/http"
	"github.com/acgs-project/acgs2-go-sdk/pkg/models"
)

// AuditService provides audit operations
type AuditService struct {
	client   *http.Client
	tenantID string
	logger   *zap.Logger
}

// NewAuditService creates a new audit service
func NewAuditService(client *http.Client, tenantID string, logger *zap.Logger) *AuditService {
	return &AuditService{
		client:   client,
		tenantID: tenantID,
		logger:   logger,
	}
}

// Query retrieves audit events
func (s *AuditService) Query(ctx context.Context, query *models.AuditQuery) (*models.ListResponse[models.AuditEvent], error) {
	endpoint := "/api/v1/audit/events"

	if query != nil {
		params := url.Values{}
		if query.EventType != nil {
			params.Add("event_type", *query.EventType)
		}
		if query.EventCategory != nil {
			params.Add("event_category", *query.EventCategory)
		}
		if query.Severity != nil {
			params.Add("severity", string(*query.Severity))
		}
		if query.UserID != nil {
			params.Add("user_id", *query.UserID)
		}
		if query.AgentID != nil {
			params.Add("agent_id", *query.AgentID)
		}
		if query.PolicyID != nil {
			params.Add("policy_id", *query.PolicyID)
		}
		if query.StartTime != nil {
			params.Add("start_time", query.StartTime.Format("2006-01-02T15:04:05Z"))
		}
		if query.EndTime != nil {
			params.Add("end_time", query.EndTime.Format("2006-01-02T15:04:05Z"))
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

	var response models.ListResponse[models.AuditEvent]
	if err := s.client.Do(ctx, "GET", endpoint, nil, &response); err != nil {
		s.logger.Error("failed to query audit events", zap.Error(err))
		return nil, fmt.Errorf("failed to query audit events: %w", err)
	}

	return &response, nil
}

// Get retrieves a specific audit event
func (s *AuditService) Get(ctx context.Context, id string) (*models.AuditEvent, error) {
	endpoint := fmt.Sprintf("/api/v1/audit/events/%s", id)

	var event models.AuditEvent
	if err := s.client.Do(ctx, "GET", endpoint, nil, &event); err != nil {
		s.logger.Error("failed to get audit event", zap.String("event_id", id), zap.Error(err))
		return nil, fmt.Errorf("failed to get audit event %s: %w", id, err)
	}

	return &event, nil
}

// GetSummary retrieves audit summary statistics
func (s *AuditService) GetSummary(ctx context.Context, period string) (*models.AuditSummary, error) {
	endpoint := fmt.Sprintf("/api/v1/audit/summary?period=%s", period)

	var summary models.AuditSummary
	if err := s.client.Do(ctx, "GET", endpoint, nil, &summary); err != nil {
		s.logger.Error("failed to get audit summary", zap.String("period", period), zap.Error(err))
		return nil, fmt.Errorf("failed to get audit summary: %w", err)
	}

	return &summary, nil
}

// GenerateComplianceReport generates a compliance report
func (s *AuditService) GenerateComplianceReport(ctx context.Context, framework, period string) (*models.ComplianceReport, error) {
	endpoint := fmt.Sprintf("/api/v1/audit/compliance/%s?period=%s", framework, period)

	var report models.ComplianceReport
	if err := s.client.Do(ctx, "POST", endpoint, nil, &report); err != nil {
		s.logger.Error("failed to generate compliance report",
			zap.String("framework", framework),
			zap.String("period", period),
			zap.Error(err))
		return nil, fmt.Errorf("failed to generate compliance report: %w", err)
	}

	return &report, nil
}

// Health checks the audit service health
func (s *AuditService) Health(ctx context.Context) (bool, error) {
	endpoint := "/health/audit"

	var response map[string]interface{}
	if err := s.client.Do(ctx, "GET", endpoint, nil, &response); err != nil {
		return false, err
	}

	status, ok := response["status"].(string)
	return ok && status == "healthy", nil
}
