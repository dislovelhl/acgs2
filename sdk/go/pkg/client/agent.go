package client

import (
	"context"
	"fmt"
	"net/url"

	"go.uber.org/zap"

	"github.com/acgs-project/acgs2-go-sdk/internal/http"
	"github.com/acgs-project/acgs2-go-sdk/pkg/models"
)

// AgentService provides agent management operations
type AgentService struct {
	client   *http.Client
	tenantID string
	logger   *zap.Logger
}

// NewAgentService creates a new agent service
func NewAgentService(client *http.Client, tenantID string, logger *zap.Logger) *AgentService {
	return &AgentService{
		client:   client,
		tenantID: tenantID,
		logger:   logger,
	}
}

// List retrieves a list of agents
func (s *AgentService) List(ctx context.Context, query *models.AgentQuery) (*models.ListResponse[models.Agent], error) {
	endpoint := "/api/v1/agents"

	if query != nil {
		params := url.Values{}
		if query.Type != nil {
			params.Add("type", string(*query.Type))
		}
		if query.Status != nil {
			params.Add("status", string(*query.Status))
		}
		if query.Name != nil {
			params.Add("name", *query.Name)
		}
		if query.Tag != nil {
			params.Add("tag", *query.Tag)
		}
		if query.Capability != nil {
			params.Add("capability", *query.Capability)
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

	var response models.ListResponse[models.Agent]
	if err := s.client.Do(ctx, "GET", endpoint, nil, &response); err != nil {
		s.logger.Error("failed to list agents", zap.Error(err))
		return nil, fmt.Errorf("failed to list agents: %w", err)
	}

	return &response, nil
}

// Get retrieves an agent by ID
func (s *AgentService) Get(ctx context.Context, id string) (*models.Agent, error) {
	endpoint := fmt.Sprintf("/api/v1/agents/%s", id)

	var agent models.Agent
	if err := s.client.Do(ctx, "GET", endpoint, nil, &agent); err != nil {
		s.logger.Error("failed to get agent", zap.String("agent_id", id), zap.Error(err))
		return nil, fmt.Errorf("failed to get agent %s: %w", id, err)
	}

	return &agent, nil
}

// Register registers a new agent
func (s *AgentService) Register(ctx context.Context, req *models.RegisterAgentRequest) (*models.Agent, error) {
	endpoint := "/api/v1/agents"

	var agent models.Agent
	if err := s.client.Do(ctx, "POST", endpoint, req, &agent); err != nil {
		s.logger.Error("failed to register agent", zap.Error(err))
		return nil, fmt.Errorf("failed to register agent: %w", err)
	}

	s.logger.Info("agent registered", zap.String("agent_id", agent.ID), zap.String("agent_name", agent.Name))
	return &agent, nil
}

// Update updates an existing agent
func (s *AgentService) Update(ctx context.Context, id string, req *models.UpdateAgentRequest) (*models.Agent, error) {
	endpoint := fmt.Sprintf("/api/v1/agents/%s", id)

	var agent models.Agent
	if err := s.client.Do(ctx, "PUT", endpoint, req, &agent); err != nil {
		s.logger.Error("failed to update agent", zap.String("agent_id", id), zap.Error(err))
		return nil, fmt.Errorf("failed to update agent %s: %w", id, err)
	}

	s.logger.Info("agent updated", zap.String("agent_id", agent.ID))
	return &agent, nil
}

// Delete deletes an agent
func (s *AgentService) Delete(ctx context.Context, id string) error {
	endpoint := fmt.Sprintf("/api/v1/agents/%s", id)

	if err := s.client.Do(ctx, "DELETE", endpoint, nil, nil); err != nil {
		s.logger.Error("failed to delete agent", zap.String("agent_id", id), zap.Error(err))
		return fmt.Errorf("failed to delete agent %s: %w", id, err)
	}

	s.logger.Info("agent deleted", zap.String("agent_id", id))
	return nil
}

// SendHeartbeat sends an agent heartbeat
func (s *AgentService) SendHeartbeat(ctx context.Context, id string, heartbeat *models.AgentHeartbeat) error {
	endpoint := fmt.Sprintf("/api/v1/agents/%s/heartbeat", id)

	if err := s.client.Do(ctx, "POST", endpoint, heartbeat, nil); err != nil {
		s.logger.Error("failed to send heartbeat", zap.String("agent_id", id), zap.Error(err))
		return fmt.Errorf("failed to send heartbeat for agent %s: %w", id, err)
	}

	return nil
}

// GetHealth retrieves agent health information
func (s *AgentService) GetHealth(ctx context.Context, id string) (map[string]interface{}, error) {
	endpoint := fmt.Sprintf("/api/v1/agents/%s/health", id)

	var health map[string]interface{}
	if err := s.client.Do(ctx, "GET", endpoint, nil, &health); err != nil {
		s.logger.Error("failed to get agent health", zap.String("agent_id", id), zap.Error(err))
		return nil, fmt.Errorf("failed to get agent health for %s: %w", id, err)
	}

	return health, nil
}

// Health checks the agent service health
func (s *AgentService) Health(ctx context.Context) (bool, error) {
	endpoint := "/health/agents"

	var response map[string]interface{}
	if err := s.client.Do(ctx, "GET", endpoint, nil, &response); err != nil {
		return false, err
	}

	status, ok := response["status"].(string)
	return ok && status == "healthy", nil
}
