// Package models contains data structures for the ACGS-2 Go SDK
package models

import "time"

// HealthStatus represents the health status of a service
type HealthStatus struct {
	Status   string            `json:"status"`
	Services map[string]bool   `json:"services"`
	Message  string            `json:"message,omitempty"`
	Version  string            `json:"version,omitempty"`
	Timestamp time.Time        `json:"timestamp"`
}

// ErrorResponse represents an error response
type ErrorResponse struct {
	Error   string                 `json:"error"`
	Message string                 `json:"message"`
	Code    string                 `json:"code,omitempty"`
	Details map[string]interface{} `json:"details,omitempty"`
}

// Pagination represents pagination information
type Pagination struct {
	Page     int `json:"page"`
	Limit    int `json:"limit"`
	Total    int `json:"total"`
	Pages    int `json:"pages"`
}

// ListResponse represents a paginated list response
type ListResponse[T any] struct {
	Data       []T          `json:"data"`
	Pagination *Pagination `json:"pagination,omitempty"`
}

// BaseEntity represents common fields for all entities
type BaseEntity struct {
	ID        string    `json:"id"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// Tenant represents a tenant
type Tenant struct {
	BaseEntity
	Name           string            `json:"name"`
	Description    string            `json:"description,omitempty"`
	Status         TenantStatus      `json:"status"`
	Tier           TenantTier        `json:"tier"`
	ResourceQuota  ResourceQuota     `json:"resource_quota"`
	ComplianceFrameworks []string    `json:"compliance_frameworks,omitempty"`
	DataResidency  string            `json:"data_residency,omitempty"`
	Features       []string          `json:"features,omitempty"`
	Metadata       map[string]string `json:"metadata,omitempty"`
}

// TenantStatus represents tenant status
type TenantStatus string

const (
	TenantStatusActive   TenantStatus = "active"
	TenantStatusSuspended TenantStatus = "suspended"
	TenantStatusInactive TenantStatus = "inactive"
)

// TenantTier represents tenant tier
type TenantTier string

const (
	TenantTierFree       TenantTier = "free"
	TenantTierProfessional TenantTier = "professional"
	TenantTierEnterprise TenantTier = "enterprise"
	TenantTierSovereign  TenantTier = "sovereign"
)

// ResourceQuota represents resource quotas for a tenant
type ResourceQuota struct {
	Users     int `json:"users"`
	Policies  int `json:"policies"`
	Agents    int `json:"agents"`
	APICalls  int `json:"api_calls"`
	Storage   int `json:"storage"`
}

// CreateTenantRequest represents a request to create a tenant
type CreateTenantRequest struct {
	Name                string            `json:"name"`
	Description         string            `json:"description,omitempty"`
	Tier                TenantTier        `json:"tier"`
	ResourceQuota       ResourceQuota     `json:"resource_quota,omitempty"`
	ComplianceFrameworks []string         `json:"compliance_frameworks,omitempty"`
	DataResidency       string            `json:"data_residency,omitempty"`
	Features            []string          `json:"features,omitempty"`
	Metadata            map[string]string `json:"metadata,omitempty"`
}

// UpdateTenantRequest represents a request to update a tenant
type UpdateTenantRequest struct {
	Name                *string            `json:"name,omitempty"`
	Description         *string            `json:"description,omitempty"`
	Status              *TenantStatus      `json:"status,omitempty"`
	Tier                *TenantTier        `json:"tier,omitempty"`
	ResourceQuota       *ResourceQuota     `json:"resource_quota,omitempty"`
	ComplianceFrameworks *[]string          `json:"compliance_frameworks,omitempty"`
	DataResidency       *string            `json:"data_residency,omitempty"`
	Features            *[]string          `json:"features,omitempty"`
	Metadata            *map[string]string `json:"metadata,omitempty"`
}

// TenantQuery represents query parameters for tenant listing
type TenantQuery struct {
	Status      *TenantStatus `json:"status,omitempty"`
	Tier        *TenantTier   `json:"tier,omitempty"`
	Name        *string       `json:"name,omitempty"`
	Limit       int           `json:"limit,omitempty"`
	Offset      int           `json:"offset,omitempty"`
}

// Policy represents a governance policy
type Policy struct {
	BaseEntity
	Name           string         `json:"name"`
	Description    string         `json:"description,omitempty"`
	Version        string         `json:"version"`
	Status         PolicyStatus   `json:"status"`
	Type           PolicyType     `json:"type"`
	Rules          []PolicyRule   `json:"rules"`
	ComplianceFrameworks []string `json:"compliance_frameworks,omitempty"`
	Severity       Severity       `json:"severity"`
	Tags           []string       `json:"tags,omitempty"`
	Metadata       map[string]string `json:"metadata,omitempty"`
}

// PolicyStatus represents policy status
type PolicyStatus string

const (
	PolicyStatusDraft     PolicyStatus = "draft"
	PolicyStatusActive    PolicyStatus = "active"
	PolicyStatusInactive  PolicyStatus = "inactive"
	PolicyStatusArchived  PolicyStatus = "archived"
)

// PolicyType represents policy type
type PolicyType string

const (
	PolicyTypeSecurity    PolicyType = "security"
	PolicyTypeCompliance  PolicyType = "compliance"
	PolicyTypeOperational PolicyType = "operational"
	PolicyTypeGovernance  PolicyType = "governance"
)

// PolicyRule represents a policy rule
type PolicyRule struct {
	ID          string                 `json:"id"`
	Name        string                 `json:"name"`
	Description string                 `json:"description,omitempty"`
	Condition   string                 `json:"condition"`
	Action      string                 `json:"action"`
	Parameters  map[string]interface{} `json:"parameters,omitempty"`
	Severity    Severity               `json:"severity"`
	Enabled     bool                   `json:"enabled"`
}

// Severity represents severity level
type Severity string

const (
	SeverityLow      Severity = "low"
	SeverityMedium   Severity = "medium"
	SeverityHigh     Severity = "high"
	SeverityCritical Severity = "critical"
)

// CreatePolicyRequest represents a request to create a policy
type CreatePolicyRequest struct {
	Name                string         `json:"name"`
	Description         string         `json:"description,omitempty"`
	Type                PolicyType     `json:"type"`
	Rules               []PolicyRule   `json:"rules"`
	ComplianceFrameworks []string      `json:"compliance_frameworks,omitempty"`
	Severity            Severity       `json:"severity,omitempty"`
	Tags                []string       `json:"tags,omitempty"`
	Metadata            map[string]string `json:"metadata,omitempty"`
}

// UpdatePolicyRequest represents a request to update a policy
type UpdatePolicyRequest struct {
	Name                *string         `json:"name,omitempty"`
	Description         *string         `json:"description,omitempty"`
	Status              *PolicyStatus   `json:"status,omitempty"`
	Type                *PolicyType     `json:"type,omitempty"`
	Rules               *[]PolicyRule   `json:"rules,omitempty"`
	ComplianceFrameworks *[]string      `json:"compliance_frameworks,omitempty"`
	Severity            *Severity       `json:"severity,omitempty"`
	Tags                *[]string       `json:"tags,omitempty"`
	Metadata            *map[string]string `json:"metadata,omitempty"`
}

// PolicyQuery represents query parameters for policy listing
type PolicyQuery struct {
	Status      *PolicyStatus `json:"status,omitempty"`
	Type        *PolicyType   `json:"type,omitempty"`
	Severity    *Severity     `json:"severity,omitempty"`
	Name        *string       `json:"name,omitempty"`
	Tag         *string       `json:"tag,omitempty"`
	Limit       int           `json:"limit,omitempty"`
	Offset      int           `json:"offset,omitempty"`
}

// PolicyValidationResult represents policy validation result
type PolicyValidationResult struct {
	Valid       bool     `json:"valid"`
	Errors      []string `json:"errors,omitempty"`
	Warnings    []string `json:"warnings,omitempty"`
	Suggestions []string `json:"suggestions,omitempty"`
}

// AuditEvent represents an audit event
type AuditEvent struct {
	BaseEntity
	EventType      string                 `json:"event_type"`
	EventCategory  string                 `json:"event_category"`
	Severity       Severity               `json:"severity"`
	Message        string                 `json:"message"`
	UserID         string                 `json:"user_id,omitempty"`
	AgentID        string                 `json:"agent_id,omitempty"`
	PolicyID       string                 `json:"policy_id,omitempty"`
	ResourceType   string                 `json:"resource_type,omitempty"`
	ResourceID     string                 `json:"resource_id,omitempty"`
	Action         string                 `json:"action"`
	Result         string                 `json:"result"`
	IPAddress      string                 `json:"ip_address,omitempty"`
	UserAgent      string                 `json:"user_agent,omitempty"`
	TraceID        string                 `json:"trace_id,omitempty"`
	SpanID         string                 `json:"span_id,omitempty"`
	Metadata       map[string]interface{} `json:"metadata,omitempty"`
}

// AuditQuery represents query parameters for audit event listing
type AuditQuery struct {
	EventType     *string    `json:"event_type,omitempty"`
	EventCategory *string    `json:"event_category,omitempty"`
	Severity      *Severity  `json:"severity,omitempty"`
	UserID        *string    `json:"user_id,omitempty"`
	AgentID       *string    `json:"agent_id,omitempty"`
	PolicyID      *string    `json:"policy_id,omitempty"`
	StartTime     *time.Time `json:"start_time,omitempty"`
	EndTime       *time.Time `json:"end_time,omitempty"`
	Limit         int        `json:"limit,omitempty"`
	Offset        int        `json:"offset,omitempty"`
}

// AuditSummary represents audit summary statistics
type AuditSummary struct {
	TotalEvents    int                        `json:"total_events"`
	TimeRange      string                     `json:"time_range"`
	EventsByType   map[string]int             `json:"events_by_type"`
	EventsBySeverity map[Severity]int         `json:"events_by_severity"`
	TopUsers       []UserActivitySummary      `json:"top_users,omitempty"`
	TopResources   []ResourceActivitySummary  `json:"top_resources,omitempty"`
}

// UserActivitySummary represents user activity summary
type UserActivitySummary struct {
	UserID      string `json:"user_id"`
	EventCount  int    `json:"event_count"`
	LastActivity time.Time `json:"last_activity"`
}

// ResourceActivitySummary represents resource activity summary
type ResourceActivitySummary struct {
	ResourceType string `json:"resource_type"`
	ResourceID   string `json:"resource_id"`
	EventCount   int    `json:"event_count"`
	LastActivity time.Time `json:"last_activity"`
}

// ComplianceReport represents a compliance report
type ComplianceReport struct {
	ID             string                 `json:"id"`
	Framework      string                 `json:"framework"`
	Period         string                 `json:"period"`
	GeneratedAt    time.Time              `json:"generated_at"`
	OverallScore   float64                `json:"overall_score"`
	Status         ComplianceStatus       `json:"status"`
	Sections       []ComplianceSection    `json:"sections"`
	Recommendations []string              `json:"recommendations,omitempty"`
	Metadata       map[string]interface{} `json:"metadata,omitempty"`
}

// ComplianceStatus represents compliance status
type ComplianceStatus string

const (
	ComplianceStatusCompliant    ComplianceStatus = "compliant"
	ComplianceStatusNonCompliant ComplianceStatus = "non_compliant"
	ComplianceStatusPartial      ComplianceStatus = "partial"
)

// ComplianceSection represents a section of compliance report
type ComplianceSection struct {
	ID          string  `json:"id"`
	Name        string  `json:"name"`
	Description string  `json:"description,omitempty"`
	Score       float64 `json:"score"`
	Status      ComplianceStatus `json:"status"`
	Findings    []ComplianceFinding `json:"findings,omitempty"`
}

// ComplianceFinding represents a compliance finding
type ComplianceFinding struct {
	ID          string            `json:"id"`
	Rule        string            `json:"rule"`
	Severity    Severity          `json:"severity"`
	Description string            `json:"description"`
	Status      ComplianceStatus  `json:"status"`
	Evidence    map[string]interface{} `json:"evidence,omitempty"`
}

// Agent represents an agent
type Agent struct {
	BaseEntity
	Name           string           `json:"name"`
	Description    string           `json:"description,omitempty"`
	Type           AgentType        `json:"type"`
	Status         AgentStatus      `json:"status"`
	Capabilities   []string         `json:"capabilities,omitempty"`
	Configuration  map[string]interface{} `json:"configuration,omitempty"`
	ResourceRequirements ResourceRequirements `json:"resource_requirements,omitempty"`
	LastHeartbeat  time.Time        `json:"last_heartbeat,omitempty"`
	Tags           []string         `json:"tags,omitempty"`
	Metadata       map[string]string `json:"metadata,omitempty"`
}

// AgentType represents agent type
type AgentType string

const (
	AgentTypeAnalysis     AgentType = "analysis"
	AgentTypeModeration   AgentType = "moderation"
	AgentTypeGeneration   AgentType = "generation"
	AgentTypeTranslation  AgentType = "translation"
	AgentTypeCustom       AgentType = "custom"
)

// AgentStatus represents agent status
type AgentStatus string

const (
	AgentStatusActive     AgentStatus = "active"
	AgentStatusInactive   AgentStatus = "inactive"
	AgentStatusSuspended  AgentStatus = "suspended"
	AgentStatusError      AgentStatus = "error"
)

// ResourceRequirements represents resource requirements for an agent
type ResourceRequirements struct {
	CPU    string `json:"cpu,omitempty"`
	Memory string `json:"memory,omitempty"`
	GPU    string `json:"gpu,omitempty"`
	Disk   string `json:"disk,omitempty"`
}

// AgentHeartbeat represents an agent heartbeat
type AgentHeartbeat struct {
	AgentID     string    `json:"agent_id"`
	Timestamp   time.Time `json:"timestamp"`
	Status      AgentStatus `json:"status"`
	Metrics     map[string]interface{} `json:"metrics,omitempty"`
	HealthScore float64   `json:"health_score,omitempty"`
	Message     string    `json:"message,omitempty"`
}

// RegisterAgentRequest represents a request to register an agent
type RegisterAgentRequest struct {
	Name               string                 `json:"name"`
	Description        string                 `json:"description,omitempty"`
	Type               AgentType              `json:"type"`
	Capabilities       []string               `json:"capabilities,omitempty"`
	Configuration      map[string]interface{} `json:"configuration,omitempty"`
	ResourceRequirements *ResourceRequirements `json:"resource_requirements,omitempty"`
	Tags               []string               `json:"tags,omitempty"`
	Metadata           map[string]string      `json:"metadata,omitempty"`
}

// UpdateAgentRequest represents a request to update an agent
type UpdateAgentRequest struct {
	Name               *string                 `json:"name,omitempty"`
	Description        *string                 `json:"description,omitempty"`
	Type               *AgentType              `json:"type,omitempty"`
	Status             *AgentStatus            `json:"status,omitempty"`
	Capabilities       *[]string               `json:"capabilities,omitempty"`
	Configuration      *map[string]interface{} `json:"configuration,omitempty"`
	ResourceRequirements *ResourceRequirements `json:"resource_requirements,omitempty"`
	Tags               *[]string               `json:"tags,omitempty"`
	Metadata           *map[string]string      `json:"metadata,omitempty"`
}

// AgentQuery represents query parameters for agent listing
type AgentQuery struct {
	Type     *AgentType  `json:"type,omitempty"`
	Status   *AgentStatus `json:"status,omitempty"`
	Name     *string     `json:"name,omitempty"`
	Tag      *string     `json:"tag,omitempty"`
	Capability *string   `json:"capability,omitempty"`
	Limit    int         `json:"limit,omitempty"`
	Offset   int         `json:"offset,omitempty"`
}
