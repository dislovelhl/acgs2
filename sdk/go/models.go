package sdk

// MessageType defines the category of agent messages
type MessageType string

const (
	MessageTypeCommand                 MessageType = "command"
	MessageTypeInquiry                 MessageType = "inquiry"
	MessageTypeTaskRequest             MessageType = "task_request"
	MessageTypeGovernanceRequest       MessageType = "governance_request"
	MessageTypeConstitutionalValidation MessageType = "constitutional_validation"
)

// Priority defines the importance of a message
type Priority int

const (
	PriorityLow      Priority = 0
	PriorityNormal   Priority = 1
	PriorityMedium   Priority = 2
	PriorityHigh     Priority = 3
	PriorityCritical Priority = 4
)

// AgentMessage represents a structured message in the ACGS-2 system
type AgentMessage struct {
	ID                 string                 `json:"id"`
	FromAgent          string                 `json:"from_agent"`
	ToAgent            string                 `json:"to_agent,omitempty"`
	TenantID           string                 `json:"tenant_id"`
	MessageType        MessageType            `json:"message_type"`
	Priority           Priority               `json:"priority"`
	Content            string                 `json:"content"`
	Payload            map[string]interface{} `json:"payload,omitempty"`
	ConstitutionalHash string                 `json:"constitutional_hash"`
	TraceID            string                 `json:"trace_id,omitempty"`
}

// ValidationResult represents the output of a governance check
type ValidationResult struct {
	IsValid            bool     `json:"is_valid"`
	Decision           string   `json:"decision"`
	Errors             []string `json:"errors,omitempty"`
	ImpactScore        float64  `json:"impact_score"`
	ConstitutionalHash string   `json:"constitutional_hash"`
}
