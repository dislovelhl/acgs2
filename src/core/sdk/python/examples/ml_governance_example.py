#!/usr/bin/env python3
"""
ACGS-2 ML Governance SDK Example
Demonstrates adaptive ML models with feedback loops
Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import logging
from datetime import datetime, timedelta

from acgs2_sdk import (
    ACGS2Config,
    MLGovernanceService,
    create_client,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Demonstrate ML governance functionality."""

    # Configure client
    config = ACGS2Config(
        base_url="http://localhost:8400",  # ML Governance service
        timeout=30.0,
    )

    async with create_client(config) as client:
        ml_service = MLGovernanceService(client)

        try:
            # Health check
            logger.info("🔍 Checking ML Governance service health...")
            health = await client.health_check()
            logger.info(f"✅ Service healthy: {health}")

            # Example 1: Create/register an ML model
            logger.info("\n🤖 Creating ML model...")
            model = await ml_service.create_model(
                name="fraud_detection_model",
                description="Random Forest model for credit card fraud detection",
                model_type="classification",
                framework="scikit-learn",
                initial_accuracy_score=0.89,
            )
            logger.info(f"✅ Created model: {model.id} ({model.name})")
            logger.info(f"   Framework: {model.framework}")
            logger.info(f"   Accuracy: {model.accuracy_score}")

            # Example 2: List ML models
            logger.info("\n📋 Listing ML models...")
            models = await ml_service.list_models(page=1, page_size=10)
            logger.info(f"📊 Found {models.total} ML models")
            for m in models.data[:3]:  # Show first 3
                logger.info(f"   • {m.id}: {m.name} - {m.framework} ({m.accuracy_score})")

            # Example 3: Make a prediction
            logger.info("\n🔮 Making prediction...")
            prediction = await ml_service.make_prediction(
                model_id=model.id,
                features={
                    "amount": 150.00,
                    "merchant_category": "online_retail",
                    "card_type": "credit",
                    "transaction_hour": 14,
                    "is_international": False,
                    "customer_age": 35,
                    "account_balance": 2500.00,
                },
                include_confidence=True,
            )
            logger.info(f"🎯 Prediction result: {prediction.prediction}")
            logger.info(f"   Confidence: {prediction.confidence_score}")
            logger.info(f"   Model Version: {prediction.model_version}")

            # Example 4: Submit feedback for model improvement
            logger.info("\n💬 Submitting feedback...")
            feedback = await ml_service.submit_feedback(
                prediction_id=prediction.id,
                model_id=model.id,
                feedback_type="correction",
                feedback_value=False,  # Actual fraud status
                user_id="analyst@example.com",
                context={
                    "feedback_source": "manual_review",
                    "reviewer_experience": "senior_analyst",
                    "confidence_in_correction": 0.95,
                },
            )
            logger.info(f"✅ Feedback submitted: {feedback.feedback_type}")
            logger.info(f"   Feedback ID: {feedback.id}")

            # Example 5: Check for model drift
            logger.info("\n📈 Checking for model drift...")
            drift = await ml_service.check_drift(model.id)
            logger.info(f"🔍 Drift Score: {drift.drift_score}")
            logger.info(f"   Direction: {drift.drift_direction}")
            logger.info(f"   Baseline Accuracy: {drift.baseline_accuracy}")
            logger.info(f"   Current Accuracy: {drift.current_accuracy}")

            # Example 6: Create A/B test
            logger.info("\n🆚 Creating A/B test...")
            ab_test = await ml_service.create_ab_test(
                name="fraud_model_comparison",
                description="Comparing Random Forest vs XGBoost for fraud detection",
                model_a_id=model.id,
                model_b_id="xgboost-fraud-v1",  # Assume another model exists
                test_duration_days=14,
                traffic_split_percentage=50.0,
                success_metric="precision_at_recall_90",
            )
            logger.info(f"✅ Created A/B test: {ab_test.id}")
            logger.info(f"   Status: {ab_test.status}")
            logger.info(f"   Traffic Split: {ab_test.traffic_split_percentage}%")

            # Example 7: List A/B tests
            logger.info("\n📋 Listing A/B tests...")
            ab_tests = await ml_service.list_ab_tests(page=1, page_size=10)
            logger.info(f"📊 Found {ab_tests.total} A/B tests")

            # Example 8: Get model metrics
            logger.info("\n📊 Getting model metrics...")
            metrics = await ml_service.get_model_metrics(
                model_id=model.id,
                start_date=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                end_date=datetime.now().strftime("%Y-%m-%d"),
            )
            logger.info(f"📈 Available metrics: {list(metrics.keys())}")

            # Example 9: Trigger model retraining
            logger.info("\n🔄 Triggering model retraining...")
            retrain_result = await ml_service.retrain_model(
                model_id=model.id,
                feedback_threshold=100,  # Retrain when 100 feedback samples available
            )
            logger.info(f"🔄 Retraining initiated: {retrain_result}")

            # Example 10: Get dashboard data
            logger.info("\n📊 Getting dashboard data...")
            dashboard = await ml_service.get_dashboard_data()
            logger.info(f"📋 Dashboard sections: {list(dashboard.keys())}")

        except Exception as e:
            logger.error(f"❌ Error: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
