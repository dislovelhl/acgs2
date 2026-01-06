#!/usr/bin/env node

/**
 * ACGS-2 Architecture Analysis using Neural Pattern Training
 *
 * This script performs comprehensive analysis of the current domain architecture:
 * 1. Load and analyze domain mappings
 * 2. Train on successful coordination patterns
 * 3. Generate optimization recommendations
 * 4. Identify weak points in domain boundaries
 */

const { spawn } = require("child_process");

// MCP client for neural pattern training
class ArchitectureAnalyzer {
  constructor() {
    this.mcpProcess = null;
    this.requestId = 1;
    this.results = {};
  }

  async start() {
    console.log("🔬 ACGS-2 Neural Architecture Analysis\n");
    console.log("=".repeat(50));

    // Start the MCP server
    this.mcpProcess = spawn("node", ["dist/index.js"], {
      cwd: __dirname,
      stdio: ["pipe", "pipe", "pipe"],
    });

    // Wait for server to be ready
    await this.waitForServerReady();

    // Perform comprehensive analysis
    await this.performFullAnalysis();

    // Cleanup
    this.mcpProcess.kill();
    console.log("\n✅ Architecture analysis completed successfully");
    this.printSummary();
  }

  async waitForServerReady() {
    return new Promise((resolve) => {
      const readyHandler = (data) => {
        const output = data.toString();
        if (output.includes("running on stdio")) {
          console.log("📡 Neural MCP Server is ready for analysis");
          resolve();
        }
      };

      this.mcpProcess.stderr.on("data", readyHandler);
      this.mcpProcess.stdout.on("data", readyHandler);
    });
  }

  async performFullAnalysis() {
    try {
      // Step 1: Load Enhanced Agent Bus domains
      console.log("\n📥 Step 1: Loading Enhanced Agent Bus domains...");
      const loadResult = await this.callTool("neural_load_domains", {
        preset: "enhanced_agent_bus",
      });
      const loadData = JSON.parse(loadResult.content[0].text);
      this.results.domains = loadData;
      console.log(
        `✅ Domains loaded: ${loadData.domains?.length || 0} domains`
      );

      // Step 2: Analyze initial architecture status
      console.log("\n📊 Step 2: Analyzing current domain architecture...");
      const statusResult = await this.callTool("neural_status");
      const status = JSON.parse(statusResult.content[0].text);
      this.results.initialStatus = status;
      console.log(`📈 Architecture Metrics:`);
      console.log(
        `   • Graph Size: ${status.graphSize?.nodes || 0} nodes, ${
          status.graphSize?.edges || 0
        } edges`
      );
      console.log(
        `   • Cohesion Score: ${(status.cohesionScore || 0).toFixed(3)}`
      );
      console.log(
        `   • Training State: ${
          status.trainingState ? "Trained" : "Not trained"
        }`
      );

      // Step 3: Train on successful coordination patterns
      console.log(
        "\n🧠 Step 3: Training on successful coordination patterns (100 epochs)..."
      );
      const trainResult = await this.callTool("neural_train", {
        epochs: 100,
        learningRate: 0.001,
      });
      const training = JSON.parse(trainResult.content[0].text);
      this.results.training = training.result;
      console.log(`✅ Training completed:`);
      console.log(`   • Epochs: ${training.result?.totalEpochs || 0}`);
      console.log(
        `   • Final Accuracy: ${
          (training.result?.finalAccuracy * 100)?.toFixed(1) || 0
        }%`
      );
      console.log(
        `   • Final Loss: ${training.result?.finalLoss?.toFixed(4) || 0}`
      );
      console.log(
        `   • Convergence: ${
          training.result?.finalAccuracy > 0.5 ? "Yes" : "No"
        }`
      );

      // Step 4: Analyze domain cohesion patterns
      console.log("\n🔍 Step 4: Analyzing domain cohesion patterns...");
      const patternsResult = await this.callTool("neural_patterns");
      const patterns = JSON.parse(patternsResult.content[0].text);
      this.results.patterns = patterns;
      console.log(`🌟 Domain Cohesion Analysis:`);
      console.log(
        `   • Overall Cohesion: ${
          (patterns.overallScore * 100)?.toFixed(1) || 0
        }%`
      );
      console.log(
        `   • Structural: ${
          (patterns.factors?.structural * 100)?.toFixed(1) || 0
        }%`
      );
      console.log(
        `   • Functional: ${
          (patterns.factors?.functional * 100)?.toFixed(1) || 0
        }%`
      );
      console.log(
        `   • Behavioral: ${
          (patterns.factors?.behavioral * 100)?.toFixed(1) || 0
        }%`
      );
      console.log(
        `   • Semantic: ${(patterns.factors?.semantic * 100)?.toFixed(1) || 0}%`
      );

      if (patterns.weakPoints?.length > 0) {
        console.log(
          `⚠️  Weak Points Identified: ${patterns.weakPoints.length}`
        );
        patterns.weakPoints.slice(0, 3).forEach((point, i) => {
          console.log(
            `   ${i + 1}. ${point.domain || "Unknown"}: ${point.issue || "N/A"}`
          );
        });
      }

      // Step 5: Analyze cross-domain dependencies
      console.log("\n🔗 Step 5: Analyzing cross-domain dependencies...");
      const depsResult = await this.callTool("neural_dependencies");
      const dependencies = JSON.parse(depsResult.content[0].text);
      this.results.dependencies = dependencies;
      console.log(`📊 Dependency Analysis:`);
      console.log(
        `   • Average In-degree: ${
          dependencies.metrics?.averageInDegree?.toFixed(2) || 0
        }`
      );
      console.log(
        `   • Average Out-degree: ${
          dependencies.metrics?.averageOutDegree?.toFixed(2) || 0
        }`
      );
      console.log(`   • Maximum Depth: ${dependencies.metrics?.maxDepth || 0}`);
      console.log(
        `   • Cyclomatic Complexity: ${
          dependencies.metrics?.cyclomaticComplexity || 0
        }`
      );

      if (dependencies.circularDependencies?.length > 0) {
        console.log(
          `🔄 Circular Dependencies: ${dependencies.circularDependencies.length}`
        );
      }

      if (dependencies.criticalPaths?.length > 0) {
        console.log(`🚨 Critical Paths: ${dependencies.criticalPaths.length}`);
        dependencies.criticalPaths.slice(0, 2).forEach((path, i) => {
          console.log(
            `   ${i + 1}. ${path.description || "Critical path identified"}`
          );
        });
      }

      // Step 6: Generate optimization recommendations
      console.log(
        "\n🎯 Step 6: Generating boundary optimization recommendations..."
      );
      const optResult = await this.callTool("neural_optimize");
      const optimizations = JSON.parse(optResult.content[0].text);
      this.results.optimizations = optimizations;
      console.log(`📈 Optimization Analysis:`);
      console.log(
        `   • Optimization Score: ${
          (optimizations.optimizationScore * 100)?.toFixed(1) || 0
        }%`
      );
      console.log(
        `   • Priority Level: ${
          optimizations.priority?.toUpperCase() || "UNKNOWN"
        }`
      );

      if (optimizations.proposals?.length > 0) {
        console.log(
          `💡 Optimization Proposals: ${optimizations.proposals.length}`
        );
        optimizations.proposals.slice(0, 5).forEach((proposal, i) => {
          console.log(
            `   ${i + 1}. ${proposal.type?.toUpperCase() || "UNKNOWN"}: ${
              proposal.domains?.join(", ") || "N/A"
            }`
          );
          console.log(
            `      Confidence: ${
              (proposal.confidence * 100)?.toFixed(1) || "N/A"
            }%`
          );
          console.log(`      Impact: ${proposal.impact || "N/A"}`);
        });
      }
    } catch (error) {
      console.error("❌ Analysis failed:", error.message);
    }
  }

  printSummary() {
    console.log("\n📋 ANALYSIS SUMMARY");
    console.log("=".repeat(50));

    const { results } = this;

    // Architecture Overview
    console.log("\n🏗️  ARCHITECTURE OVERVIEW:");
    console.log(`   • Total Domains: ${results.domains?.domains?.length || 0}`);
    console.log(
      `   • Graph Complexity: ${
        results.initialStatus?.graphSize?.edges || 0
      } relationships`
    );
    console.log(
      `   • Overall Cohesion: ${
        (results.patterns?.overallScore * 100)?.toFixed(1) || "N/A"
      }%`
    );

    // Training Performance
    console.log("\n🎯 TRAINING PERFORMANCE:");
    console.log(
      `   • Model Accuracy: ${
        (results.training?.finalAccuracy * 100)?.toFixed(1) || "N/A"
      }%`
    );
    console.log(
      `   • Convergence Achieved: ${results.training?.converged ? "Yes" : "No"}`
    );

    // Critical Issues
    console.log("\n⚠️  CRITICAL ISSUES:");
    const weakPoints = results.patterns?.weakPoints?.length || 0;
    const circularDeps =
      results.dependencies?.circularDependencies?.length || 0;
    const criticalPaths = results.dependencies?.criticalPaths?.length || 0;

    console.log(`   • Weak Domain Boundaries: ${weakPoints}`);
    console.log(`   • Circular Dependencies: ${circularDeps}`);
    console.log(`   • Critical Dependency Paths: ${criticalPaths}`);

    // Optimization Priority
    console.log("\n🎯 OPTIMIZATION PRIORITY:");
    const priority = results.optimizations?.priority || "unknown";
    const score =
      (results.optimizations?.optimizationScore * 100)?.toFixed(1) || "N/A";
    console.log(`   • Priority Level: ${priority.toUpperCase()}`);
    console.log(`   • Optimization Score: ${score}%`);

    // Recommendations
    console.log("\n💡 KEY RECOMMENDATIONS:");
    if (results.optimizations?.proposals?.length > 0) {
      const topProposal = results.optimizations.proposals[0];
      console.log(
        `   • Top Priority: ${
          topProposal.type?.toUpperCase() || "UNKNOWN"
        } operation`
      );
      console.log(`     Domains: ${topProposal.domains?.join(", ") || "N/A"}`);
      console.log(`     Expected Impact: ${topProposal.impact || "N/A"}`);
    }

    console.log("\n🔄 Next Steps:");
    console.log("   1. Review weak points in domain boundaries");
    console.log("   2. Address circular dependencies");
    console.log("   3. Implement high-confidence optimization proposals");
    console.log("   4. Retrain model after architectural changes");
  }

  async callTool(name, args = {}) {
    return new Promise((resolve, reject) => {
      const request = {
        jsonrpc: "2.0",
        id: this.requestId++,
        method: "tools/call",
        params: { name, arguments: args },
      };

      const requestJson = JSON.stringify(request) + "\n";

      let responseData = "";
      const responseHandler = (data) => {
        responseData += data.toString();

        try {
          const response = JSON.parse(responseData);
          if (response.id === request.id) {
            this.mcpProcess.stdout.off("data", responseHandler);
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

      this.mcpProcess.stdout.on("data", responseHandler);
      this.mcpProcess.stdin.write(requestJson);

      // Timeout after 60 seconds for complex operations
      setTimeout(() => {
        this.mcpProcess.stdout.off("data", responseHandler);
        reject(new Error("Tool call timeout"));
      }, 60000);
    });
  }
}

// Run the architecture analysis
if (require.main === module) {
  const analyzer = new ArchitectureAnalyzer();
  analyzer.start().catch(console.error);
}

module.exports = ArchitectureAnalyzer;
