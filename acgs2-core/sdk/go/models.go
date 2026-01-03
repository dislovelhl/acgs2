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

// =============================================================================
// HITL Approvals Models
// =============================================================================

// ApprovalStatus represents the status of an approval request
type ApprovalStatus string

const (
	ApprovalStatusPending   ApprovalStatus = "pending"
	ApprovalStatusApproved  ApprovalStatus = "approved"
	ApprovalStatusRejected  ApprovalStatus = "rejected"
	ApprovalStatusEscalated ApprovalStatus = "escalated"
	ApprovalStatusExpired   ApprovalStatus = "expired"
)

// ApprovalDecision represents an individual approval decision
type ApprovalDecision struct {
	ApproverID  string    `json:"approverId"`
	Decision    ApprovalStatus `json:"decision"`
	Reasoning   *string   `json:"reasoning,omitempty"`
	Timestamp   string    `json:"timestamp"`
}

// ApprovalRequest represents a human-in-the-loop approval request
type ApprovalRequest struct {
	ID                 string             `json:"id"`
	RequestType        string             `json:"requestType"`
	RequesterID        string             `json:"requesterId"`
	Status             ApprovalStatus     `json:"status"`
	RiskScore          float64            `json:"riskScore"`
	RequiredApprovers  int                `json:"requiredApprovers"`
	CurrentApprovals   int                `json:"currentApprovals"`
	Decisions          []ApprovalDecision `json:"decisions"`
	Payload            map[string]interface{} `json:"payload"`
	CreatedAt          string             `json:"createdAt"`
	ExpiresAt          *string            `json:"expiresAt,omitempty"`
	ConstitutionalHash string             `json:"constitutionalHash"`
}

// CreateApprovalRequest represents a request to create an approval
type CreateApprovalRequest struct {
	RequestType       string                 `json:"requestType"`
	Payload           map[string]interface{} `json:"payload"`
	RiskScore         *float64               `json:"riskScore,omitempty"`
	RequiredApprovers *int                   `json:"requiredApprovers,omitempty"`
}

// SubmitApprovalDecision represents a decision on an approval request
type SubmitApprovalDecision struct {
	Decision  string  `json:"decision"` // "approve" | "reject"
	Reasoning string  `json:"reasoning"`
}

// =============================================================================
// ML Governance Models
// =============================================================================

// ModelTrainingStatus represents the training status of an ML model
type ModelTrainingStatus string

const (
	ModelTrainingStatusTraining ModelTrainingStatus = "training"
	ModelTrainingStatusCompleted ModelTrainingStatus = "completed"
	ModelTrainingStatusFailed    ModelTrainingStatus = "failed"
	ModelTrainingStatusStopped   ModelTrainingStatus = "stopped"
)

// DriftDirection represents the direction of model drift
type DriftDirection string

const (
	DriftDirectionNone     DriftDirection = "none"
	DriftDirectionIncrease DriftDirection = "increase"
	DriftDirectionDecrease DriftDirection = "decrease"
)

// ABNTestStatus represents the status of an A/B test
type ABNTestStatus string

const (
	ABNTestStatusActive     ABNTestStatus = "active"
	ABNTestStatusCompleted  ABNTestStatus = "completed"
	ABNTestStatusPaused     ABNTestStatus = "paused"
	ABNTestStatusCancelled  ABNTestStatus = "cancelled"
)

// MLModel represents an ML model in the governance system
type MLModel struct {
	ID                string              `json:"id"`
	Name              string              `json:"name"`
	Version           string              `json:"version"`
	Description       *string             `json:"description,omitempty"`
	ModelType         string              `json:"modelType"`
	Framework         string              `json:"framework"`
	AccuracyScore     *float64            `json:"accuracyScore,omitempty"`
	TrainingStatus    ModelTrainingStatus `json:"trainingStatus"`
	LastTrainedAt     *string             `json:"lastTrainedAt,omitempty"`
	CreatedAt         string              `json:"createdAt"`
	UpdatedAt         string              `json:"updatedAt"`
	ConstitutionalHash string              `json:"constitutionalHash"`
}

// ModelPrediction represents a prediction made by an ML model
type ModelPrediction struct {
	ID                  string                 `json:"id"`
	ModelID             string                 `json:"modelId"`
	ModelVersion        string                 `json:"modelVersion"`
	InputFeatures       map[string]interface{} `json:"inputFeatures"`
	Prediction          interface{}            `json:"prediction"`
	ConfidenceScore     *float64               `json:"confidenceScore,omitempty"`
	PredictionMetadata  map[string]interface{} `json:"predictionMetadata,omitempty"`
	Timestamp           string                 `json:"timestamp"`
	ConstitutionalHash  string                 `json:"constitutionalHash"`
}

// DriftDetection represents model drift detection results
type DriftDetection struct {
	ModelID            string          `json:"modelId"`
	DriftScore         float64         `json:"driftScore"`
	DriftDirection     DriftDirection  `json:"driftDirection"`
	BaselineAccuracy   float64         `json:"baselineAccuracy"`
	CurrentAccuracy    float64         `json:"currentAccuracy"`
	FeaturesAffected   []string        `json:"featuresAffected"`
	DetectedAt         string          `json:"detectedAt"`
	Recommendations    []string        `json:"recommendations"`
	ConstitutionalHash string          `json:"constitutionalHash"`
}

// ABNTest represents an A/B test configuration
type ABNTest struct {
	ID                     string        `json:"id"`
	Name                   string        `json:"name"`
	Description            *string       `json:"description,omitempty"`
	ModelAID               string        `json:"modelAId"`
	ModelBID               string        `json:"modelBId"`
	Status                 ABNTestStatus `json:"status"`
	TestDurationDays       int           `json:"testDurationDays"`
	TrafficSplitPercentage float64       `json:"trafficSplitPercentage"`
	SuccessMetric          string        `json:"successMetric"`
	CreatedAt              string        `json:"createdAt"`
	CompletedAt            *string       `json:"completedAt,omitempty"`
	ConstitutionalHash     string        `json:"constitutionalHash"`
}

// FeedbackSubmission represents user feedback for model training
type FeedbackSubmission struct {
	ID                 string                 `json:"id"`
	PredictionID       *string                `json:"predictionId,omitempty"`
	ModelID            string                 `json:"modelId"`
	FeedbackType       string                 `json:"feedbackType"`
	FeedbackValue      interface{}            `json:"feedbackValue"`
	UserID             *string                `json:"userId,omitempty"`
	Context            map[string]interface{} `json:"context,omitempty"`
	SubmittedAt        string                 `json:"submittedAt"`
	ConstitutionalHash string                 `json:"constitutionalHash"`
}

// CreateMLModelRequest represents a request to create/register an ML model
type CreateMLModelRequest struct {
	Name               string   `json:"name"`
	Description        *string  `json:"description,omitempty"`
	ModelType          string   `json:"modelType"`
	Framework          string   `json:"framework"`
	InitialAccuracyScore *float64 `json:"initialAccuracyScore,omitempty"`
}

// UpdateMLModelRequest represents a request to update an ML model
type UpdateMLModelRequest struct {
	Name           *string   `json:"name,omitempty"`
	Description    *string   `json:"description,omitempty"`
	AccuracyScore  *float64  `json:"accuracyScore,omitempty"`
}

// MakePredictionRequest represents a request to make a prediction
type MakePredictionRequest struct {
	ModelID          string                 `json:"modelId"`
	Features         map[string]interface{} `json:"features"`
	IncludeConfidence *bool                  `json:"includeConfidence,omitempty"`
}

// SubmitFeedbackRequest represents a request to submit feedback
type SubmitFeedbackRequest struct {
	PredictionID   *string                `json:"predictionId,omitempty"`
	ModelID        string                 `json:"modelId"`
	FeedbackType   string                 `json:"feedbackType"`
	FeedbackValue  interface{}            `json:"feedbackValue"`
	UserID         *string                `json:"userId,omitempty"`
	Context        map[string]interface{} `json:"context,omitempty"`
}

// CreateABNTestRequest represents a request to create an A/B test
type CreateABNTestRequest struct {
	Name                   string   `json:"name"`
	Description            *string  `json:"description,omitempty"`
	ModelAID               string   `json:"modelAId"`
	ModelBID               string   `json:"modelBId"`
	TestDurationDays       int      `json:"testDurationDays"`
	TrafficSplitPercentage float64  `json:"trafficSplitPercentage"`
	SuccessMetric          string   `json:"successMetric"`
}

// =============================================================================
// Common Types
// =============================================================================

// PaginatedResponse represents a paginated API response
type PaginatedResponse[T any] struct {
	Data        []T     `json:"data"`
	Total       int     `json:"total"`
	Page        int     `json:"page"`
	PageSize    int     `json:"pageSize"`
	TotalPages  int     `json:"totalPages"`
}

// =============================================================================
// Policy Registry Models
// =============================================================================

// PolicyStatus represents the lifecycle status of a policy
type PolicyStatus string

const (
	PolicyStatusDraft         PolicyStatus = "draft"
	PolicyStatusPendingReview PolicyStatus = "pending_review"
	PolicyStatusApproved      PolicyStatus = "approved"
	PolicyStatusActive        PolicyStatus = "active"
	PolicyStatusDeprecated    PolicyStatus = "deprecated"
	PolicyStatusArchived      PolicyStatus = "archived"
)

// Policy represents a governance policy
type Policy struct {
	ID               string                 `json:"id"`
	Name             string                 `json:"name"`
	Version          string                 `json:"version"`
	Description      *string                `json:"description,omitempty"`
	Status           PolicyStatus           `json:"status"`
	Rules            []map[string]interface{} `json:"rules"`
	TenantID         *string                `json:"tenantId,omitempty"`
	CreatedAt        string                 `json:"createdAt"`
	UpdatedAt        string                 `json:"updatedAt"`
	ConstitutionalHash string               `json:"constitutionalHash"`
}

// CreatePolicyRequest represents a request to create a new policy
type CreatePolicyRequest struct {
	Name        string                   `json:"name"`
	Description *string                  `json:"description,omitempty"`
	Rules       []map[string]interface{} `json:"rules"`
	Tags        []string                 `json:"tags,omitempty"`
	ComplianceTags []string              `json:"complianceTags,omitempty"`
}

// UpdatePolicyRequest represents a request to update a policy
type UpdatePolicyRequest struct {
	Name        *string                  `json:"name,omitempty"`
	Description *string                  `json:"description,omitempty"`
	Rules       []map[string]interface{} `json:"rules,omitempty"`
	Status      *PolicyStatus            `json:"status,omitempty"`
	Tags        []string                 `json:"tags,omitempty"`
	ComplianceTags []string              `json:"complianceTags,omitempty"`
}

// PolicyVersion represents a version of a policy
type PolicyVersion struct {
	ID          string      `json:"id"`
	PolicyID    string      `json:"policyId"`
	Version     string      `json:"version"`
	Content     interface{} `json:"content"`
	Description *string     `json:"description,omitempty"`
	CreatedAt   string      `json:"createdAt"`
	CreatedBy   string      `json:"createdBy"`
}

// PolicyBundle represents a collection of policies
type PolicyBundle struct {
	ID          string   `json:"id"`
	Name        string   `json:"name"`
	Description *string  `json:"description,omitempty"`
	Policies    []string `json:"policies"`
	TenantID    *string  `json:"tenantId,omitempty"`
	CreatedAt   string   `json:"createdAt"`
	UpdatedAt   string   `json:"updatedAt"`
}

// CreateBundleRequest represents a request to create a policy bundle
type CreateBundleRequest struct {
	Name        string   `json:"name"`
	Policies    []string `json:"policies"`
	Description *string  `json:"description,omitempty"`
}

// AuthRequest represents an authentication request
type AuthRequest struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

// AuthResponse represents an authentication response
type AuthResponse struct {
	AccessToken string `json:"accessToken"`
	TokenType   string `json:"tokenType"`
	ExpiresIn   int    `json:"expiresIn"`
	User        struct {
		ID       string   `json:"id"`
		Username string   `json:"username"`
		Roles    []string `json:"roles"`
		TenantID *string  `json:"tenantId,omitempty"`
	} `json:"user"`
}

// PolicyVerificationRequest represents a policy verification request
type PolicyVerificationRequest struct {
	Input interface{} `json:"input"`
}

// PolicyVerificationResponse represents a policy verification response
type PolicyVerificationResponse struct {
	Allowed    bool     `json:"allowed"`
	Reason     *string  `json:"reason,omitempty"`
	Violations []string `json:"violations,omitempty"`
}

// =============================================================================
// API Gateway Models
// =============================================================================

// HealthCheckResponse represents a health check response
type HealthCheckResponse struct {
	Status             string  `json:"status"`
	Version            *string `json:"version,omitempty"`
	Timestamp          string  `json:"timestamp"`
	ConstitutionalHash string  `json:"constitutionalHash"`
}

// FeedbackRequest represents a user feedback request
type FeedbackRequest struct {
	UserID    string                 `json:"userId"`
	Category  string                 `json:"category"`
	Rating    int                    `json:"rating"`
	Title     string                 `json:"title"`
	Description *string               `json:"description,omitempty"`
	Metadata  map[string]interface{} `json:"metadata,omitempty"`
}

// FeedbackResponse represents a feedback submission response
type FeedbackResponse struct {
	ID        string `json:"id"`
	Status    string `json:"status"`
	Timestamp string `json:"timestamp"`
}

// FeedbackStats represents feedback statistics
type FeedbackStats struct {
	TotalFeedback     int                        `json:"totalFeedback"`
	AverageRating     float64                    `json:"averageRating"`
	CategoryBreakdown map[string]int             `json:"categoryBreakdown"`
	RecentFeedback    []FeedbackSummary          `json:"recentFeedback"`
}

// FeedbackSummary represents a summary of feedback
type FeedbackSummary struct {
	ID        string `json:"id"`
	UserID    string `json:"userId"`
	Category  string `json:"category"`
	Rating    int    `json:"rating"`
	Title     string `json:"title"`
	Timestamp string `json:"timestamp"`
}

// ServiceInfo represents information about a service
type ServiceInfo struct {
	Name        string   `json:"name"`
	Version     string   `json:"version"`
	Status      string   `json:"status"`
	Endpoints   []string `json:"endpoints"`
	Description *string  `json:"description,omitempty"`
}

// ServicesResponse represents the services listing response
type ServicesResponse struct {
	Services []ServiceInfo `json:"services"`
	Gateway  struct {
		Version           string `json:"version"`
		Uptime            int    `json:"uptime"`
		ActiveConnections int    `json:"activeConnections"`
	} `json:"gateway"`
}
