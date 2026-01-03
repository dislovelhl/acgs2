#!/usr/bin/env node

/**
 * Neural Pattern Training Demo
 *
 * This script demonstrates how to use the ACGS-2 Neural MCP Server
 * for domain analysis and pattern training.
 *
 * The server provides these tools:
 * 1. neural_load_domains - Load domain mappings into neural graph
 * 2. neural_train - Train coordination patterns on loaded domains
 * 3. neural_status - Get current model statistics and training state
 * 4. neural_patterns - Analyze domain cohesion and patterns
 * 5. neural_dependencies - Identify cross-domain dependencies
 * 6. neural_optimize - Get boundary optimization recommendations
 */

const { spawn } = require('child_process');

// Simulated MCP client that demonstrates tool usage
class NeuralTrainingDemo {
  constructor() {
    this.mcpProcess = null;
    this.requestId = 1;
  }

  async start() {
    console.log('🚀 Starting Neural Pattern Training Demo\n');

    // Start the MCP server
    this.mcpProcess = spawn('node', ['dist/index.js'], {
      cwd: __dirname,
      stdio: ['pipe', 'pipe', 'pipe']
    });

    // Wait for server to be ready
    await this.waitForServerReady();

    // Demonstrate the neural training workflow
    await this.runDemoWorkflow();

    // Cleanup
    this.mcpProcess.kill();
    console.log('\n✅ Demo completed successfully');
  }

  async waitForServerReady() {
    return new Promise((resolve) => {
      const readyHandler = (data) => {
        const output = data.toString();
        if (output.includes('running on stdio')) {
          console.log('📡 Neural MCP Server is ready');
          resolve();
        }
      };

      this.mcpProcess.stderr.on('data', readyHandler);
      this.mcpProcess.stdout.on('data', readyHandler);
    });
  }

  async runDemoWorkflow() {
    try {
      // Step 1: Load Enhanced Agent Bus domains
      console.log('\n📥 Step 1: Loading Enhanced Agent Bus domains...');
      const loadResult = await this.callTool('neural_load_domains', {
        preset: 'enhanced_agent_bus'
      });
      console.log('✅ Domains loaded:', JSON.parse(loadResult).status);

      // Step 2: Check initial status
      console.log('\n📊 Step 2: Checking initial model status...');
      const statusResult = await this.callTool('neural_status');
      const status = JSON.parse(statusResult);
      console.log(`📈 Model Status: ${status.graphSize.nodes} nodes, ${status.graphSize.edges} edges`);
      console.log(`🎯 Cohesion Score: ${status.cohesionScore.toFixed(3)}`);

      // Step 3: Train the neural model
      console.log('\n🧠 Step 3: Training neural coordination model (50 epochs)...');
      const trainResult = await this.callTool('neural_train', {
        epochs: 50,
        learningRate: 0.001
      });
      const training = JSON.parse(trainResult);
      console.log(`✅ Training completed: ${training.result.totalEpochs} epochs`);
      console.log(`🎯 Final Accuracy: ${(training.result.finalAccuracy * 100).toFixed(1)}%`);
      console.log(`📉 Final Loss: ${training.result.finalLoss.toFixed(4)}`);

      // Step 4: Analyze domain patterns
      console.log('\n🔍 Step 4: Analyzing domain cohesion patterns...');
      const patternsResult = await this.callTool('neural_patterns');
      const patterns = JSON.parse(patternsResult);
      console.log(`🌟 Overall Cohesion: ${(patterns.overallScore * 100).toFixed(1)}%`);
      console.log(`🏗️  Structural: ${(patterns.factors.structural * 100).toFixed(1)}%`);
      console.log(`⚙️  Functional: ${(patterns.factors.functional * 100).toFixed(1)}%`);
      console.log(`🔄 Behavioral: ${(patterns.factors.behavioral * 100).toFixed(1)}%`);
      console.log(`📝 Semantic: ${(patterns.factors.semantic * 100).toFixed(1)}%`);

      if (patterns.weakPoints.length > 0) {
        console.log(`⚠️  Found ${patterns.weakPoints.length} weak points requiring attention`);
      }

      // Step 5: Check cross-domain dependencies
      console.log('\n🔗 Step 5: Analyzing cross-domain dependencies...');
      const depsResult = await this.callTool('neural_dependencies');
      const dependencies = JSON.parse(depsResult);
      console.log(`📊 Dependency Metrics:`);
      console.log(`   • Average In-degree: ${dependencies.metrics.averageInDegree.toFixed(2)}`);
      console.log(`   • Average Out-degree: ${dependencies.metrics.averageOutDegree.toFixed(2)}`);
      console.log(`   • Maximum Depth: ${dependencies.metrics.maxDepth}`);
      console.log(`   • Cyclomatic Complexity: ${dependencies.metrics.cyclomaticComplexity}`);

      if (dependencies.circularDependencies.length > 0) {
        console.log(`🔄 Found ${dependencies.circularDependencies.length} circular dependencies`);
      }

      if (dependencies.criticalPaths.length > 0) {
        console.log(`🚨 Identified ${dependencies.criticalPaths.length} critical dependency paths`);
      }

      // Step 6: Get optimization recommendations
      console.log('\n🎯 Step 6: Generating boundary optimization recommendations...');
      const optResult = await this.callTool('neural_optimize');
      const optimizations = JSON.parse(optResult);
      console.log(`📈 Optimization Score: ${(optimizations.optimizationScore * 100).toFixed(1)}%`);
      console.log(`🔥 Priority Level: ${optimizations.priority.toUpperCase()}`);

      if (optimizations.proposals.length > 0) {
        console.log(`💡 Generated ${optimizations.proposals.length} optimization proposals:`);
        optimizations.proposals.slice(0, 3).forEach((proposal, i) => {
          console.log(`   ${i + 1}. ${proposal.type.toUpperCase()}: ${proposal.domains.join(', ')}`);
          console.log(`      Confidence: ${(proposal.confidence * 100).toFixed(1)}%`);
        });
      }

    } catch (error) {
      console.error('❌ Demo failed:', error.message);
    }
  }

  async callTool(name, args = {}) {
    return new Promise((resolve, reject) => {
      const request = {
        jsonrpc: '2.0',
        id: this.requestId++,
        method: 'callTool',
        params: { name, arguments: args }
      };

      const requestJson = JSON.stringify(request) + '\n';

      let responseData = '';
      const responseHandler = (data) => {
        responseData += data.toString();

        try {
          const response = JSON.parse(responseData);
          if (response.id === request.id) {
            this.mcpProcess.stdout.off('data', responseHandler);
            if (response.error) {
              reject(new Error(response.error.message));
            } else {
              resolve(JSON.stringify(response.result.content[0].text));
            }
          }
        } catch (e) {
          // Response not complete yet, continue accumulating
        }
      };

      this.mcpProcess.stdout.on('data', responseHandler);
      this.mcpProcess.stdin.write(requestJson);

      // Timeout after 30 seconds
      setTimeout(() => {
        this.mcpProcess.stdout.off('data', responseHandler);
        reject(new Error('Tool call timeout'));
      }, 30000);
    });
  }
}

// Run the demo
if (require.main === module) {
  const demo = new NeuralTrainingDemo();
  demo.start().catch(console.error);
}

module.exports = NeuralTrainingDemo;
