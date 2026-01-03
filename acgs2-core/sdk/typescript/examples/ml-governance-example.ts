#!/usr/bin/env tsx
/**
 * ACGS-2 ML Governance SDK Example
 * Demonstrates adaptive ML models with feedback loops
 * Constitutional Hash: cdd01ef066bc6cf2
 */

import { createACGS2SDK } from '../src/index.js';

async function main() {
  console.log('🚀 ACGS-2 ML Governance Example\n');

  // Initialize SDK
  const sdk = createACGS2SDK({
    baseUrl: 'http://localhost:8400', // ML Governance service
    timeout: 30000,
  });

  try {
    // Health check
    console.log('🔍 Checking ML Governance service health...');
    const health = await sdk.healthCheck();
    console.log(`✅ Service healthy: ${health.healthy} (${health.latencyMs}ms)\n`);

    // Example 1: Create/register an ML model
    console.log('🤖 Creating ML model...');
    const model = await sdk.mlGovernance.createModel({
      name: 'fraud_detection_model',
      description: 'Random Forest model for credit card fraud detection',
      modelType: 'classification',
      framework: 'scikit-learn',
      initialAccuracyScore: 0.89,
    });
    console.log(`✅ Created model: ${model.id} (${model.name})`);
    console.log(`   Framework: ${model.framework}`);
    console.log(`   Accuracy: ${model.accuracyScore}\n`);

    // Example 2: List ML models
    console.log('📋 Listing ML models...');
    const models = await sdk.mlGovernance.listModels({
      page: 1,
      pageSize: 10,
    });
    console.log(`📊 Found ${models.total} ML models`);
    models.data.slice(0, 3).forEach((m, i) => {
      console.log(`   ${i + 1}. ${m.id}: ${m.name} - ${m.framework} (${m.accuracyScore})`);
    });
    console.log();

    // Example 3: Make a prediction
    console.log('🔮 Making prediction...');
    const prediction = await sdk.mlGovernance.makePrediction({
      modelId: model.id,
      features: {
        amount: 150.00,
        merchant_category: 'online_retail',
        card_type: 'credit',
        transaction_hour: 14,
        is_international: false,
        customer_age: 35,
        account_balance: 2500.00,
      },
      includeConfidence: true,
    });
    console.log(`🎯 Prediction result: ${prediction.prediction}`);
    console.log(`   Confidence: ${prediction.confidenceScore}`);
    console.log(`   Model Version: ${prediction.modelVersion}\n`);

    // Example 4: Submit feedback for model improvement
    console.log('💬 Submitting feedback...');
    const feedback = await sdk.mlGovernance.submitFeedback({
      predictionId: prediction.id,
      modelId: model.id,
      feedbackType: 'correction',
      feedbackValue: false, // Actual fraud status
      userId: 'analyst@example.com',
      context: {
        feedback_source: 'manual_review',
        reviewer_experience: 'senior_analyst',
        confidence_in_correction: 0.95,
      },
    });
    console.log(`✅ Feedback submitted: ${feedback.feedbackType}`);
    console.log(`   Feedback ID: ${feedback.id}\n`);

    // Example 5: Check for model drift
    console.log('📈 Checking for model drift...');
    const drift = await sdk.mlGovernance.checkDrift(model.id);
    console.log(`🔍 Drift Score: ${drift.driftScore}`);
    console.log(`   Direction: ${drift.driftDirection}`);
    console.log(`   Baseline Accuracy: ${drift.baselineAccuracy}`);
    console.log(`   Current Accuracy: ${drift.currentAccuracy}\n`);

    // Example 6: Create A/B test
    console.log('🆚 Creating A/B test...');
    const abTest = await sdk.mlGovernance.createABNTest({
      name: 'fraud_model_comparison',
      description: 'Comparing Random Forest vs XGBoost for fraud detection',
      modelAId: model.id,
      modelBId: 'xgboost-fraud-v1', // Assume another model exists
      testDurationDays: 14,
      trafficSplitPercentage: 50.0,
      successMetric: 'precision_at_recall_90',
    });
    console.log(`✅ Created A/B test: ${abTest.id}`);
    console.log(`   Status: ${abTest.status}`);
    console.log(`   Traffic Split: ${abTest.trafficSplitPercentage}%\n`);

    // Example 7: List A/B tests
    console.log('📋 Listing A/B tests...');
    const abTests = await sdk.mlGovernance.listABNTests({
      page: 1,
      pageSize: 10,
    });
    console.log(`📊 Found ${abTests.total} A/B tests\n`);

    // Example 8: Get model metrics
    console.log('📊 Getting model metrics...');
    const metrics = await sdk.mlGovernance.getModelMetrics(model.id, {
      startDate: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      endDate: new Date().toISOString().split('T')[0],
    });
    console.log(`📈 Available metrics: ${Object.keys(metrics).join(', ')}\n`);

    // Example 9: Trigger model retraining
    console.log('🔄 Triggering model retraining...');
    const retrainResult = await sdk.mlGovernance.retrainModel(model.id, {
      feedbackThreshold: 100, // Retrain when 100 feedback samples available
    });
    console.log(`🔄 Retraining initiated: ${Object.keys(retrainResult).join(', ')}\n`);

    // Example 10: Get dashboard data
    console.log('📊 Getting dashboard data...');
    const dashboard = await sdk.mlGovernance.getDashboardData();
    console.log(`📋 Dashboard sections: ${Object.keys(dashboard).join(', ')}\n`);

    console.log('🎉 ML Governance example completed successfully!');

  } catch (error) {
    console.error('❌ Error:', error);
    process.exit(1);
  }
}

// Run the example
main().catch(console.error);
