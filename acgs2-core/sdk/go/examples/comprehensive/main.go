package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/acgs/sdk-go"
)

func main() {
	fmt.Println("🚀 ACGS-2 Comprehensive Go SDK Example")
	fmt.Println("Constitutional Hash: cdd01ef066bc6cf2\n")

	// Initialize client
	client := sdk.NewClient(sdk.ClientConfig{
		BaseURL:  "http://localhost:8080", // API Gateway
		TenantID: "acgs-dev",
		Timeout:  30 * time.Second,
	})

	ctx := context.Background()

	// =============================================================================
	// HITL Approvals Example
	// =============================================================================

	fmt.Println("=== HITL Approvals Service ===")

	hitlService := sdk.NewHITLApprovalsService(client)

	// Create approval request
	fmt.Println("📝 Creating approval request...")
	approvalReq := sdk.CreateApprovalRequest{
		RequestType: "model_deployment",
		Payload: map[string]interface{}{
			"model_name":        "fraud_detection_v2",
			"version":           "2.1.0",
			"deployment_env":    "production",
			"risk_assessment": map[string]interface{}{
				"risk_level":     "medium",
				"impact_areas":   []string{"financial", "customer_trust"},
				"rollback_plan":  "Automated rollback to v2.0.1",
			},
			"performance_metrics": map[string]interface{}{
				"accuracy":  0.94,
				"precision": 0.91,
				"recall":    0.89,
			},
		},
		RiskScore:       &[]float64{65.0}[0],
		RequiredApprovers: &[]int{2}[0],
	}

	approval, err := hitlService.CreateApprovalRequest(ctx, approvalReq)
	if err != nil {
		log.Printf("❌ Failed to create approval request: %v", err)
	} else {
		fmt.Printf("✅ Created approval request: %s\n", approval.ID)
		fmt.Printf("   Status: %s\n", approval.Status)
		fmt.Printf("   Required approvers: %d\n\n", approval.RequiredApprovers)

		// Submit approval decision
		fmt.Println("✅ Submitting approval decision...")
		decision := sdk.SubmitApprovalDecision{
			Decision:  "approve",
			Reasoning: "Model performance metrics meet production standards. Risk mitigation plan is comprehensive.",
		}

		updatedApproval, err := hitlService.SubmitDecision(ctx, approval.ID, decision)
		if err != nil {
			log.Printf("❌ Failed to submit decision: %v", err)
		} else {
			fmt.Printf("✅ Decision submitted: %s\n\n", updatedApproval.Status)
		}
	}

	// =============================================================================
	// ML Governance Example
	// =============================================================================

	fmt.Println("=== ML Governance Service ===")

	mlService := sdk.NewMLGovernanceService(client)

	// Create ML model
	fmt.Println("🤖 Creating ML model...")
	modelReq := sdk.CreateMLModelRequest{
		Name:        "fraud_detection_model",
		Description: stringPtr("Random Forest model for credit card fraud detection"),
		ModelType:   "classification",
		Framework:   "scikit-learn",
		InitialAccuracyScore: &[]float64{0.89}[0],
	}

	model, err := mlService.CreateModel(ctx, modelReq)
	if err != nil {
		log.Printf("❌ Failed to create model: %v", err)
	} else {
		fmt.Printf("✅ Created model: %s (%s)\n", model.ID, model.Name)
		fmt.Printf("   Framework: %s\n", model.Framework)
		if model.AccuracyScore != nil {
			fmt.Printf("   Accuracy: %.2f\n", *model.AccuracyScore)
		}
		fmt.Println()

		// Make prediction
		fmt.Println("🔮 Making prediction...")
		predictionReq := sdk.MakePredictionRequest{
			ModelID: model.ID,
			Features: map[string]interface{}{
				"amount":            150.00,
				"merchant_category": "online_retail",
				"card_type":         "credit",
				"transaction_hour":  14,
				"is_international":  false,
				"customer_age":      35,
				"account_balance":   2500.00,
			},
			IncludeConfidence: &[]bool{true}[0],
		}

		prediction, err := mlService.MakePrediction(ctx, predictionReq)
		if err != nil {
			log.Printf("❌ Failed to make prediction: %v", err)
		} else {
			fmt.Printf("🎯 Prediction result: %v\n", prediction.Prediction)
			if prediction.ConfidenceScore != nil {
				fmt.Printf("   Confidence: %.2f\n", *prediction.ConfidenceScore)
			}
			fmt.Printf("   Model Version: %s\n\n", prediction.ModelVersion)
		}

		// Submit feedback
		fmt.Println("💬 Submitting feedback...")
		feedbackReq := sdk.SubmitFeedbackRequest{
			PredictionID: &prediction.ID,
			ModelID:      model.ID,
			FeedbackType: "correction",
			FeedbackValue: false, // Actual fraud status
			UserID:       stringPtr("analyst@example.com"),
			Context: map[string]interface{}{
				"feedback_source":      "manual_review",
				"reviewer_experience":  "senior_analyst",
				"confidence_in_correction": 0.95,
			},
		}

		feedback, err := mlService.SubmitFeedback(ctx, feedbackReq)
		if err != nil {
			log.Printf("❌ Failed to submit feedback: %v", err)
		} else {
			fmt.Printf("✅ Feedback submitted: %s\n", feedback.FeedbackType)
			fmt.Printf("   Feedback ID: %s\n\n", feedback.ID)
		}

		// Check for model drift
		fmt.Println("📈 Checking for model drift...")
		drift, err := mlService.CheckDrift(ctx, model.ID)
		if err != nil {
			log.Printf("❌ Failed to check drift: %v", err)
		} else {
			fmt.Printf("🔍 Drift Score: %.3f\n", drift.DriftScore)
			fmt.Printf("   Direction: %s\n", drift.DriftDirection)
			fmt.Printf("   Baseline Accuracy: %.2f\n", drift.BaselineAccuracy)
			fmt.Printf("   Current Accuracy: %.2f\n\n", drift.CurrentAccuracy)
		}

		// Create A/B test
		fmt.Println("🆚 Creating A/B test...")
		abTestReq := sdk.CreateABNTestRequest{
			Name:        "fraud_model_comparison",
			Description: stringPtr("Comparing Random Forest vs XGBoost for fraud detection"),
			ModelAID:    model.ID,
			ModelBID:    "xgboost-fraud-v1", // Assume another model exists
			TestDurationDays: 14,
			TrafficSplitPercentage: 50.0,
			SuccessMetric:         "precision_at_recall_90",
		}

		abTest, err := mlService.CreateABNTest(ctx, abTestReq)
		if err != nil {
			log.Printf("❌ Failed to create A/B test: %v", err)
		} else {
			fmt.Printf("✅ Created A/B test: %s\n", abTest.ID)
			fmt.Printf("   Status: %s\n", abTest.Status)
			fmt.Printf("   Traffic Split: %.1f%%\n\n", abTest.TrafficSplitPercentage)
		}

		// Get dashboard data
		fmt.Println("📊 Getting dashboard data...")
		dashboard, err := mlService.GetDashboardData(ctx)
		if err != nil {
			log.Printf("❌ Failed to get dashboard data: %v", err)
		} else {
			fmt.Printf("📋 Dashboard sections: %v\n\n", getMapKeys(dashboard))
		}
	}

	fmt.Println("🎉 Comprehensive example completed successfully!")
}

// Helper functions
func stringPtr(s string) *string {
	return &s
}

func getMapKeys(m map[string]interface{}) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	return keys
}
