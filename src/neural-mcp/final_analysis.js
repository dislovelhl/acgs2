#!/usr/bin/env node

/**
 * ACGS-2 Neural Architecture Analysis - Final Working Version
 *
 * Comprehensive analysis of the current domain architecture using neural pattern training.
 */

const { spawn } = require("child_process");

class NeuralArchitectureAnalyzer {
  constructor() {
    this.mcpProcess = null;
    this.requestId = 1;
    this.results = {};
  }

  async analyze() {
    console.log("🔬 ACGS-2 Neural Architecture Analysis");
    console.log("=====================================\n");

    // Start MCP server
    this.mcpProcess = spawn("node", ["dist/index.js"], {
      cwd: __dirname,
      stdio: ["pipe", "pipe", "pipe"],
    });

    await this.waitForServerReady();

    try {
      await this.performAnalysis();
      this.printResults();
    } catch (error) {
      console.error("❌ Analysis failed:", error.message);
    }

    this.mcpProcess.kill();
  }

  async waitForServerReady() {
    return new Promise((resolve) => {
      const readyHandler = (data) => {
        const output = data.toString();
        if (output.includes("running on stdio")) {
          console.log("📡 Neural MCP Server ready");
          resolve();
        }
      };
      this.mcpProcess.stderr.on("data", readyHandler);
    });
  }

  async performAnalysis() {
    // 1. Load Enhanced Agent Bus domains
    console.log("📥 Loading Enhanced Agent Bus domains...");
    const loadResult = await this.callTool("neural_load_domains", {
      preset: "enhanced_agent_bus",
    });
    const domains = this.parseResponse(loadResult);
    this.results.domains = domains;
    console.log(
      `✅ Loaded ${domains.domains?.length || 0} domains with ${
        domains.graphSize?.edges || 0
      } relationships`
    );

    // 2. Analyze current architecture
    console.log("\n📊 Analyzing current architecture...");
    const statusResult = await this.callTool("neural_status");
    const status = this.parseResponse(statusResult);
    this.results.status = status;
    console.log(
      `📈 Architecture: ${status.graphSize?.nodes || 0} nodes, cohesion ${(
        status.cohesionScore || 0
      ).toFixed(3)}`
    );

    // 3. Train on coordination patterns
    console.log("\n🧠 Training neural coordination model...");
    const trainResult = await this.callTool("neural_train", {
      epochs: 100,
      learningRate: 0.001,
    });
    const training = this.parseResponse(trainResult);
    this.results.training = training;
    console.log(
      `✅ Training: ${(training.result?.finalAccuracy * 100)?.toFixed(
        1
      )}% accuracy, ${training.result?.finalLoss?.toFixed(4)} loss`
    );

    // 4. Analyze domain cohesion patterns
    console.log("\n🔍 Analyzing domain cohesion patterns...");
    const patternsResult = await this.callTool("neural_patterns");
    const patterns = this.parseResponse(patternsResult);
    this.results.patterns = patterns;
    console.log(
      `🌟 Overall cohesion: ${(patterns.overallScore * 100)?.toFixed(1)}%`
    );

    // 5. Analyze cross-domain dependencies
    console.log("\n🔗 Analyzing cross-domain dependencies...");
    const depsResult = await this.callTool("neural_dependencies");
    const dependencies = this.parseResponse(depsResult);
    this.results.dependencies = dependencies;
    console.log(
      `📊 Dependencies: ${
        dependencies.metrics?.cyclomaticComplexity || 0
      } complexity, ${dependencies.criticalPaths?.length || 0} critical paths`
    );

    // 6. Generate optimization recommendations
    console.log("\n🎯 Generating optimization recommendations...");
    const optResult = await this.callTool("neural_optimize");
    const optimizations = this.parseResponse(optResult);
    this.results.optimizations = optimizations;
    console.log(
      `💡 Generated ${
        optimizations.proposals?.length || 0
      } optimization proposals`
    );
  }

  parseResponse(response) {
    if (response.content && response.content[0]) {
      return JSON.parse(response.content[0].text);
    }
    return response;
  }

  printResults() {
    console.log("\n📋 ANALYSIS RESULTS");
    console.log("==================\n");

    const { results } = this;

    // Architecture Overview
    console.log("🏗️  ARCHITECTURE OVERVIEW");
    console.log(`   • Total Domains: ${results.domains?.domains?.length || 0}`);
    console.log(
      `   • Relationships: ${results.domains?.graphSize?.edges || 0}`
    );
    console.log(
      `   • Graph Complexity: ${results.status?.graphSize?.nodes || 0} nodes`
    );
    console.log(
      `   • Current Cohesion: ${(results.status?.cohesionScore || 0).toFixed(
        3
      )}`
    );
    console.log();

    // Training Performance
    console.log("🎯 TRAINING PERFORMANCE");
    console.log(
      `   • Epochs Completed: ${results.training?.result?.totalEpochs || 0}`
    );
    console.log(
      `   • Final Accuracy: ${
        (results.training?.result?.finalAccuracy * 100)?.toFixed(1) || 0
      }%`
    );
    console.log(
      `   • Final Loss: ${results.training?.result?.finalLoss?.toFixed(4) || 0}`
    );
    console.log(
      `   • Training Time: ${
        results.training?.result?.trainingHistory?.length || 0
      } checkpoints`
    );
    console.log();

    // Domain Cohesion Analysis
    console.log("🌟 DOMAIN COHESION ANALYSIS");
    const p = results.patterns;
    if (p) {
      console.log(
        `   • Overall Cohesion: ${(p.overallScore * 100)?.toFixed(1)}%`
      );
      console.log(
        `   • Structural: ${(p.factors?.structural * 100)?.toFixed(1)}%`
      );
      console.log(
        `   • Functional: ${(p.factors?.functional * 100)?.toFixed(1)}%`
      );
      console.log(
        `   • Behavioral: ${(p.factors?.behavioral * 100)?.toFixed(1)}%`
      );
      console.log(`   • Semantic: ${(p.factors?.semantic * 100)?.toFixed(1)}%`);

      if (p.weakPoints?.length > 0) {
        console.log(
          `   • Weak Points: ${p.weakPoints.length} domains need attention`
        );
        p.weakPoints.slice(0, 3).forEach((point, i) => {
          console.log(
            `     ${i + 1}. ${point.domain || "Unknown"}: ${
              point.issue || "Issue identified"
            }`
          );
        });
      }
    }
    console.log();

    // Dependency Analysis
    console.log("🔗 DEPENDENCY ANALYSIS");
    const d = results.dependencies;
    if (d?.metrics) {
      console.log(
        `   • Average In-degree: ${d.metrics.averageInDegree?.toFixed(2) || 0}`
      );
      console.log(
        `   • Average Out-degree: ${
          d.metrics.averageOutDegree?.toFixed(2) || 0
        }`
      );
      console.log(`   • Maximum Depth: ${d.metrics.maxDepth || 0}`);
      console.log(
        `   • Cyclomatic Complexity: ${d.metrics.cyclomaticComplexity || 0}`
      );

      if (d.circularDependencies?.length > 0) {
        console.log(
          `   • Circular Dependencies: ${d.circularDependencies.length} ⚠️`
        );
      }

      if (d.criticalPaths?.length > 0) {
        console.log(`   • Critical Paths: ${d.criticalPaths.length}`);
        d.criticalPaths.slice(0, 2).forEach((path, i) => {
          console.log(
            `     ${i + 1}. ${path.description || "Critical dependency path"}`
          );
        });
      }
    }
    console.log();

    // Optimization Recommendations
    console.log("🎯 OPTIMIZATION RECOMMENDATIONS");
    const o = results.optimizations;
    if (o) {
      console.log(
        `   • Optimization Score: ${(o.optimizationScore * 100)?.toFixed(1)}%`
      );
      console.log(
        `   • Priority Level: ${o.priority?.toUpperCase() || "UNKNOWN"}`
      );

      if (o.proposals?.length > 0) {
        console.log(`   • Total Proposals: ${o.proposals.length}`);
        o.proposals.slice(0, 5).forEach((proposal, i) => {
          console.log(
            `     ${
              i + 1
            }. ${proposal.type?.toUpperCase()}: ${proposal.domains?.join(
              ", "
            )} (${(proposal.confidence * 100)?.toFixed(0)}% confidence)`
          );
          console.log(`        Impact: ${proposal.impact || "Not specified"}`);
        });
      }
    }
    console.log();

    // Key Insights
    console.log("💡 KEY INSIGHTS");
    console.log("   • Architecture Health: " + this.getHealthAssessment());
    console.log("   • Critical Issues: " + this.getCriticalIssues());
    console.log("   • Next Priority: " + this.getNextPriority());
    console.log();

    console.log("🔄 RECOMMENDED ACTIONS");
    this.getRecommendedActions().forEach((action) => {
      console.log(`   • ${action}`);
    });
  }

  getHealthAssessment() {
    const cohesion = this.results.patterns?.overallScore || 0;
    const complexity =
      this.results.dependencies?.metrics?.cyclomaticComplexity || 0;

    if (cohesion > 0.8 && complexity < 10)
      return "Excellent - Well-structured architecture";
    if (cohesion > 0.6 && complexity < 20)
      return "Good - Minor optimization opportunities";
    if (cohesion > 0.4) return "Fair - Some structural improvements needed";
    return "Poor - Significant refactoring required";
  }

  getCriticalIssues() {
    const issues = [];
    if (this.results.dependencies?.circularDependencies?.length > 0) {
      issues.push(
        `${this.results.dependencies.circularDependencies.length} circular dependencies`
      );
    }
    if (this.results.patterns?.weakPoints?.length > 0) {
      issues.push(
        `${this.results.patterns.weakPoints.length} weak domain boundaries`
      );
    }
    if (this.results.dependencies?.criticalPaths?.length > 3) {
      issues.push("High dependency complexity");
    }
    return issues.length > 0 ? issues.join(", ") : "None identified";
  }

  getNextPriority() {
    const proposals = this.results.optimizations?.proposals || [];
    if (proposals.length > 0) {
      const topProposal = proposals[0];
      return `${topProposal.type} operation (${(
        topProposal.confidence * 100
      )?.toFixed(0)}% confidence)`;
    }
    return "Architecture stabilization";
  }

  getRecommendedActions() {
    const actions = [];

    // Address critical issues first
    if (this.results.dependencies?.circularDependencies?.length > 0) {
      actions.push("Resolve circular dependencies in dependency graph");
    }

    if (this.results.patterns?.weakPoints?.length > 0) {
      actions.push(
        "Strengthen weak domain boundaries identified in cohesion analysis"
      );
    }

    // Apply optimizations
    const proposals = this.results.optimizations?.proposals || [];
    if (proposals.length > 0) {
      proposals.slice(0, 3).forEach((proposal) => {
        actions.push(
          `Consider ${
            proposal.type
          } operation for domains: ${proposal.domains?.join(", ")}`
        );
      });
    }

    // Training improvements
    const accuracy = this.results.training?.result?.finalAccuracy || 0;
    if (accuracy < 0.5) {
      actions.push("Improve training data quality or increase training epochs");
    }

    actions.push(
      "Retrain neural model after implementing architectural changes"
    );
    actions.push("Monitor cohesion metrics during development");

    return actions;
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
              resolve(response.result);
            }
          }
        } catch (e) {
          // Response not complete yet
        }
      };

      this.mcpProcess.stdout.on("data", responseHandler);
      this.mcpProcess.stdin.write(requestJson);

      setTimeout(() => {
        this.mcpProcess.stdout.off("data", responseHandler);
        reject(new Error("Tool call timeout"));
      }, 60000);
    });
  }
}

// Run the analysis
if (require.main === module) {
  const analyzer = new NeuralArchitectureAnalyzer();
  analyzer.analyze().catch(console.error);
}

module.exports = NeuralArchitectureAnalyzer;
