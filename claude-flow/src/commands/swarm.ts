import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import { initializeSwarm, getSwarmStatus } from '../services/swarmService';

export const swarmCommand = new Command('swarm')
  .description('Manage agent swarms');

// Valid topologies and strategies
const VALID_TOPOLOGIES = ['mesh', 'hierarchical', 'ring', 'star'] as const;
const VALID_STRATEGIES = ['balanced', 'parallel', 'sequential'] as const;

type Topology = typeof VALID_TOPOLOGIES[number];
type Strategy = typeof VALID_STRATEGIES[number];

function validateTopology(topology: string): topology is Topology {
  return VALID_TOPOLOGIES.includes(topology as Topology);
}

function validateStrategy(strategy: string): strategy is Strategy {
  return VALID_STRATEGIES.includes(strategy as Strategy);
}

function validateMaxAgents(maxAgents: string): number {
  const num = parseInt(maxAgents, 10);
  if (isNaN(num) || num < 1 || num > 100) {
    throw new Error('Maximum agents must be a number between 1 and 100');
  }
  return num;
}

const initCommand = new Command('init')
  .description('Initialize a Claude Flow swarm with specified topology and configuration')
  .option('-t, --topology <type>', `Swarm topology (${VALID_TOPOLOGIES.join(', ')})`, 'hierarchical')
  .option('-m, --max-agents <number>', 'Maximum number of agents', '8')
  .option('-s, --strategy <type>', `Execution strategy (${VALID_STRATEGIES.join(', ')})`, 'parallel')
  .option('--auto-spawn', 'Automatically spawn agents based on task complexity', false)
  .option('--memory', 'Enable cross-session memory persistence', false)
  .option('--github', 'Enable GitHub integration features', false)
  .action(async (options) => {
    const spinner = ora('Initializing swarm...').start();

    try {
      // Validate topology
      if (!validateTopology(options.topology)) {
        spinner.fail(chalk.red(`❌ Invalid topology: ${options.topology}`));
        console.log(chalk.yellow(`\n📋 Valid topologies: ${VALID_TOPOLOGIES.join(', ')}`));
        console.log(chalk.gray(`\n💡 Choose based on your use case:`));
        console.log(chalk.gray(`   • mesh: Research, exploration, brainstorming`));
        console.log(chalk.gray(`   • hierarchical: Development, structured tasks`));
        console.log(chalk.gray(`   • ring: Pipeline processing, sequential workflows`));
        console.log(chalk.gray(`   • star: Simple tasks, centralized control`));
        process.exit(1);
      }

      // Validate strategy
      if (!validateStrategy(options.strategy)) {
        spinner.fail(chalk.red(`❌ Invalid strategy: ${options.strategy}`));
        console.log(chalk.yellow(`\n📋 Valid strategies: ${VALID_STRATEGIES.join(', ')}`));
        process.exit(1);
      }

      // Validate max agents
      let maxAgents: number;
      try {
        maxAgents = validateMaxAgents(options.maxAgents);
      } catch (error) {
        spinner.fail(chalk.red(`❌ ${error instanceof Error ? error.message : 'Invalid max agents'}`));
        console.log(chalk.yellow(`\n💡 Maximum agents should be between 1 and 100`));
        process.exit(1);
      }

      spinner.text = `Initializing ${options.topology} swarm with ${maxAgents} max agents...`;

      // Initialize the swarm
      const result = await initializeSwarm({
        topology: options.topology,
        maxAgents,
        strategy: options.strategy,
        autoSpawn: options.autoSpawn,
        memory: options.memory,
        github: options.github
      });

      if (result.success) {
        spinner.succeed(chalk.green(`✅ Swarm initialized successfully!`));

        console.log(chalk.blue(`\n🐝 Swarm Configuration:`));
        console.log(chalk.gray(`   Topology: ${options.topology}`));
        console.log(chalk.gray(`   Max Agents: ${maxAgents}`));
        console.log(chalk.gray(`   Strategy: ${options.strategy}`));
        console.log(chalk.gray(`   Auto-spawn: ${options.autoSpawn ? 'enabled' : 'disabled'}`));
        console.log(chalk.gray(`   Memory: ${options.memory ? 'enabled' : 'disabled'}`));
        console.log(chalk.gray(`   GitHub: ${options.github ? 'enabled' : 'disabled'}`));

        if (result.swarmId) {
          console.log(chalk.gray(`   Swarm ID: ${result.swarmId}`));
        }

        console.log(chalk.green(`\n🚀 Swarm is ready for agent spawning and task orchestration!`));

        // Show next steps
        console.log(chalk.cyan(`\n📝 Next steps:`));
        console.log(chalk.gray(`   • Spawn agents: npx claude-flow agent spawn --type coder`));
        console.log(chalk.gray(`   • Check status: npx claude-flow swarm status`));
        console.log(chalk.gray(`   • Start monitoring: npx claude-flow swarm monitor`));

      } else {
        spinner.fail(chalk.red(`❌ Failed to initialize swarm`));
        console.log(chalk.red(`\nError: ${result.error}`));
        process.exit(1);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      spinner.fail(chalk.red(`❌ Error initializing swarm: ${errorMessage}`));

      // Provide helpful error context
      if (errorMessage.includes('python3')) {
        console.log(chalk.yellow(`\n💡 Make sure Python 3 is installed and available in PATH`));
      } else if (errorMessage.includes('EnhancedAgentBus')) {
        console.log(chalk.yellow(`\n💡 Make sure the ACGS-2 core is properly installed`));
      }

      process.exit(1);
    }
  });

const statusCommand = new Command('status')
  .description('Check the current status of the swarm')
  .option('-v, --verbose', 'Show detailed status information', false)
  .action(async (options) => {
    const spinner = ora('Checking swarm status...').start();

    try {
      const status = await getSwarmStatus();

      if (!status || Object.keys(status).length === 0) {
        spinner.warn(chalk.yellow(`⚠️  No active swarm found`));
        console.log(chalk.gray(`\n💡 Initialize a swarm first: npx claude-flow swarm init`));
        return;
      }

      spinner.succeed(chalk.green(`✅ Swarm status retrieved!`));

      console.log(chalk.blue(`\n🐝 Swarm Status:`));

      // Show basic information
      if (status.swarm_id) {
        console.log(chalk.gray(`   Swarm ID: ${status.swarm_id}`));
      }
      if (status.topology) {
        console.log(chalk.gray(`   Topology: ${status.topology}`));
      }
      if (status.max_agents) {
        console.log(chalk.gray(`   Max Agents: ${status.max_agents}`));
      }
      if (status.active_agents !== undefined) {
        console.log(chalk.gray(`   Active Agents: ${status.active_agents}`));
      }
      if (status.strategy) {
        console.log(chalk.gray(`   Strategy: ${status.strategy}`));
      }

      // Show feature flags
      const features = [];
      if (status.auto_spawn) features.push('Auto-spawn');
      if (status.memory_enabled) features.push('Memory');
      if (status.github_enabled) features.push('GitHub');
      if (features.length > 0) {
        console.log(chalk.gray(`   Features: ${features.join(', ')}`));
      }

      if (status.created_at) {
        const created = new Date(status.created_at * 1000);
        console.log(chalk.gray(`   Created: ${created.toLocaleString()}`));
      }

      if (status.coordinator_agent) {
        console.log(chalk.gray(`   Coordinator: ${status.coordinator_agent}`));
      }

      if (options.verbose) {
        console.log(chalk.blue(`\n📊 Detailed Information:`));
        if (status.tenant_id) {
          console.log(chalk.gray(`   Tenant: ${status.tenant_id}`));
        }
        if (status.memory_backend) {
          console.log(chalk.gray(`   Memory Backend: ${status.memory_backend}`));
        }
        if (status.github_webhook_url) {
          console.log(chalk.gray(`   GitHub Webhook: ${status.github_webhook_url}`));
        }
        console.log(chalk.gray(`   Constitutional Hash: ${status.constitutional_hash || 'cdd01ef066bc6cf2'}`));
      }

      // Show health indicators
      const activeAgents = status.active_agents || 0;
      const maxAgents = status.max_agents || 8;
      const utilization = maxAgents > 0 ? Math.round((activeAgents / maxAgents) * 100) : 0;

      console.log(chalk.blue(`\n🏥 Health Status:`));
      console.log(chalk.gray(`   Agent Utilization: ${activeAgents}/${maxAgents} (${utilization}%)`));

      if (utilization === 0) {
        console.log(chalk.yellow(`   Status: Swarm initialized but no agents active`));
      } else if (utilization < 50) {
        console.log(chalk.green(`   Status: Swarm healthy with available capacity`));
      } else if (utilization < 90) {
        console.log(chalk.yellow(`   Status: Swarm busy, consider scaling`));
      } else {
        console.log(chalk.red(`   Status: Swarm at capacity, monitor closely`));
      }

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      spinner.fail(chalk.red(`❌ Failed to get swarm status: ${errorMessage}`));

      if (errorMessage.includes('python3')) {
        console.log(chalk.yellow(`\n💡 Make sure Python 3 is installed and available in PATH`));
      } else if (errorMessage.includes('EnhancedAgentBus')) {
        console.log(chalk.yellow(`\n💡 Make sure the ACGS-2 core is properly installed`));
      }
    }
  });

const monitorCommand = new Command('monitor')
  .description('Monitor swarm activity in real-time')
  .option('-i, --interval <seconds>', 'Monitoring interval in seconds', '5')
  .option('-l, --limit <count>', 'Maximum number of updates to show', '10')
  .option('--metrics', 'Show detailed metrics instead of summary', false)
  .action(async (options) => {
    const interval = parseInt(options.interval, 10);
    const limit = parseInt(options.limit, 10);

    if (isNaN(interval) || interval < 1) {
      console.log(chalk.red(`❌ Invalid interval: ${options.interval}. Must be a positive number.`));
      process.exit(1);
    }

    if (isNaN(limit) || limit < 1) {
      console.log(chalk.red(`❌ Invalid limit: ${options.limit}. Must be a positive number.`));
      process.exit(1);
    }

    console.log(chalk.blue(`🐝 Starting swarm monitoring...`));
    console.log(chalk.gray(`   Interval: ${interval}s | Updates: ${limit}`));
    console.log(chalk.gray(`   Press Ctrl+C to stop monitoring`));
    console.log();

    let updateCount = 0;

    const monitor = async () => {
      try {
        const status = await getSwarmStatus();

        if (!status || Object.keys(status).length === 0) {
          console.log(chalk.yellow(`⚠️  No active swarm detected`));
          return;
        }

        updateCount++;

        if (options.metrics) {
          // Detailed metrics view
          console.log(chalk.blue(`📊 Update ${updateCount} - ${new Date().toLocaleTimeString()}`));
          console.log(chalk.gray(`   Active Agents: ${status.active_agents || 0}/${status.max_agents || 8}`));
          console.log(chalk.gray(`   Utilization: ${Math.round(status.utilization_percent || 0)}%`));
          console.log(chalk.gray(`   Topology: ${status.topology || 'unknown'}`));
          console.log(chalk.gray(`   Strategy: ${status.strategy || 'unknown'}`));
          console.log();
        } else {
          // Summary view
          const utilization = Math.round(status.utilization_percent || 0);
          const activeAgents = status.active_agents || 0;
          const maxAgents = status.max_agents || 8;
          const statusEmoji = utilization < 50 ? '🟢' : utilization < 90 ? '🟡' : '🔴';

          console.log(`${statusEmoji} ${new Date().toLocaleTimeString()} - ${activeAgents}/${maxAgents} agents (${utilization}%)`);
        }

        if (updateCount >= limit) {
          console.log(chalk.green(`\n✅ Monitoring complete - ${limit} updates shown`));
          process.exit(0);
        }

      } catch (error) {
        console.log(chalk.red(`❌ Monitoring error: ${error instanceof Error ? error.message : String(error)}`));
      }
    };

    // Initial monitoring
    await monitor();

    // Set up interval monitoring
    const monitoringInterval = setInterval(monitor, interval * 1000);

    // Handle graceful shutdown
    process.on('SIGINT', () => {
      console.log(chalk.green(`\n🛑 Monitoring stopped by user`));
      clearInterval(monitoringInterval);
      process.exit(0);
    });

    process.on('SIGTERM', () => {
      console.log(chalk.green(`\n🛑 Monitoring stopped`));
      clearInterval(monitoringInterval);
      process.exit(0);
    });
  });

swarmCommand.addCommand(initCommand);
swarmCommand.addCommand(statusCommand);
swarmCommand.addCommand(monitorCommand);
