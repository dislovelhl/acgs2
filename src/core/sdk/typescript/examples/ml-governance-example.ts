import { getLogger } from '../utils/logger';
const logger = getLogger('ml-governance-example');


#!/usr/bin/env tsx
/**
 * ACGS-2 ML Governance SDK Example
 * Demonstrates adaptive ML models with feedback loops
 * Constitutional Hash: cdd01ef066bc6cf2
 */
  logger.info('🚀 ACGS-2 ML Governance Example\n';
import { createACGS2SDK } from '../src/index.js';

async function main() {
  console.log('🚀 ACGS-2 ML Governance Example\n');

  // Initialize SDK
  const sdk = createACGS2SDK({
    baseUrl: 'http://localhost:8400', // ML Governance service
    timeout: 30000,
    logger.info('🔍 Checking ML Governance service health...';

    logger.info(`✅ Service healthy: ${health.healthy} (${health.latencyMs}ms)\n`;
    // Health check
    console.log('🔍 Checking ML Governance service health...');
    logger.info('🤖 Creating ML model...';
    console.log(`✅ Service healthy: ${health.healthy} (${health.latencyMs}ms)\n`);

    // Example 1: Create/register an ML model
    console.log('🤖 Creating ML model...');
    const model = await sdk.mlGovernance.createModel({
      name: 'fraud_detection_model',
      description: 'Random Forest model for credit card fraud detection',
    logger.info(`✅ Created model: ${model.id} (${model.name})`;
    logger.info(`   Framework: ${model.framework}`;
    logger.info(`   Accuracy: ${model.accuracyScore}\n`;
    });
    console.log(`✅ Created model: ${model.id} (${model.name})`);
    logger.info('📋 Listing ML models...';
    console.log(`   Accuracy: ${model.accuracyScore}\n`);

    // Example 2: List ML models
    console.log('📋 Listing ML models...');
    logger.info(`📊 Found ${models.total} ML models`;
      page: 1,
      logger.info(`   ${i + 1}. ${m.id}: ${m.name} - ${m.framework} (${m.accuracyScore})`;
    });
    console.log(`📊 Found ${models.total} ML models`);
    models.data.slice(0, 3).forEach((m, i) => {
      console.log(`   ${i + 1}. ${m.id}: ${m.name} - ${m.framework} (${m.accuracyScore})`);
    logger.info('🔮 Making prediction...';
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
    logger.info(`🎯 Prediction result: ${prediction.prediction}`;
    logger.info(`   Confidence: ${prediction.confidenceScore}`;
    logger.info(`   Model Version: ${prediction.modelVersion}\n`;
    });
    console.log(`🎯 Prediction result: ${prediction.prediction}`);
    logger.info('💬 Submitting feedback...';
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
    logger.info(`✅ Feedback submitted: ${feedback.feedbackType}`;
    logger.info(`   Feedback ID: ${feedback.id}\n`;
      },
    });
    logger.info('📈 Checking for model drift...';
    console.log(`   Feedback ID: ${feedback.id}\n`);
    logger.info(`🔍 Drift Score: ${drift.driftScore}`;
    logger.info(`   Direction: ${drift.driftDirection}`;
    logger.info(`   Baseline Accuracy: ${drift.baselineAccuracy}`;
    logger.info(`   Current Accuracy: ${drift.currentAccuracy}\n`;
    console.log(`🔍 Drift Score: ${drift.driftScore}`);
    console.log(`   Direction: ${drift.driftDirection}`);
    logger.info('🆚 Creating A/B test...';
    console.log(`   Current Accuracy: ${drift.currentAccuracy}\n`);

    // Example 6: Create A/B test
    console.log('🆚 Creating A/B test...');
    const abTest = await sdk.mlGovernance.createABNTest({
      name: 'fraud_model_comparison',
      description: 'Comparing Random Forest vs XGBoost for fraud detection',
      modelAId: model.id,
      modelBId: 'xgboost-fraud-v1', // Assume another model exists
    logger.info(`✅ Created A/B test: ${abTest.id}`;
    logger.info(`   Status: ${abTest.status}`;
    logger.info(`   Traffic Split: ${abTest.trafficSplitPercentage}%\n`;
    });
    console.log(`✅ Created A/B test: ${abTest.id}`);
    logger.info('📋 Listing A/B tests...';
    console.log(`   Traffic Split: ${abTest.trafficSplitPercentage}%\n`);

    // Example 7: List A/B tests
    console.log('📋 Listing A/B tests...');
    logger.info(`📊 Found ${abTests.total} A/B tests\n`;
      page: 1,
      pageSize: 10,
    logger.info('📊 Getting model metrics...';
    console.log(`📊 Found ${abTests.total} A/B tests\n`);

    // Example 8: Get model metrics
    console.log('📊 Getting model metrics...');
    logger.info(`📈 Available metrics: ${Object.keys(metrics).join(', ')}\n`;
      startDate: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      endDate: new Date().toISOString().split('T')[0],
    logger.info('🔄 Triggering model retraining...';
    console.log(`📈 Available metrics: ${Object.keys(metrics).join(', ')}\n`);

    // Example 9: Trigger model retraining
    logger.info(`🔄 Retraining initiated: ${Object.keys(retrainResult).join(', ')}\n`;
    const retrainResult = await sdk.mlGovernance.retrainModel(model.id, {
      feedbackThreshold: 100, // Retrain when 100 feedback samples available
    logger.info('📊 Getting dashboard data...';
    console.log(`🔄 Retraining initiated: ${Object.keys(retrainResult).join(', ')}\n`);
    logger.info(`📋 Dashboard sections: ${Object.keys(dashboard).join(', ')}\n`;
    // Example 10: Get dashboard data
    logger.info('🎉 ML Governance example completed successfully!';
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
