import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import { initializeSwarm, getSwarmStatus } from '../services/swarmService';
import { getLogger, cliOutput } from '../utils/logging_config';

// Initialize logger for this module
const logger = getLogger('commands/swarm');

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
        logger.warn('invalid_topology', { topology: options.topology });
        cliOutput(chalk.yellow(`\n📋 Valid topologies: ${VALID_TOPOLOGIES.join(', ')}`));
        cliOutput(chalk.gray(`\n💡 Choose based on your use case:`));
        cliOutput(chalk.gray(`   • mesh: Research, exploration, brainstorming`));
        cliOutput(chalk.gray(`   • hierarchical: Development, structured tasks`));
        cliOutput(chalk.gray(`   • ring: Pipeline processing, sequential workflows`));
        cliOutput(chalk.gray(`   • star: Simple tasks, centralized control`));
        process.exit(1);
      }
        logger.info(chalk.yellow(`\n📋 Valid strategies: ${VALID_STRATEGIES.join(', ')}`);
      // Validate strategy
      if (!validateStrategy(options.strategy)) {
        spinner.fail(chalk.red(`❌ Invalid strategy: ${options.strategy}`));
        logger.warn('invalid_strategy', { strategy: options.strategy });
        cliOutput(chalk.yellow(`\n📋 Valid strategies: ${VALID_STRATEGIES.join(', ')}`));
        process.exit(1);
      }

      // Validate max agents
      let maxAgents: number;
        logger.info(chalk.yellow(`\n💡 Maximum agents should be between 1 and 100`);
        maxAgents = validateMaxAgents(options.maxAgents);
      } catch (error) {
        spinner.fail(chalk.red(`❌ ${error instanceof Error ? error.message : 'Invalid max agents'}`));
        logger.warn('invalid_max_agents', { maxAgents: options.maxAgents });
        cliOutput(chalk.yellow(`\n💡 Maximum agents should be between 1 and 100`));
        process.exit(1);
      }

      spinner.text = `Initializing ${options.topology} swarm with ${maxAgents} max agents...`;
      logger.info('swarm_init_started', { topology: options.topology, maxAgents, strategy: options.strategy });

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
        logger.info('swarm_initialized', { swarmId: result.swarmId, topology: options.topology });

        cliOutput(chalk.blue(`\n🐝 Swarm Configuration:`));
        cliOutput(chalk.gray(`   Topology: ${options.topology}`));
        cliOutput(chalk.gray(`   Max Agents: ${maxAgents}`));
        cliOutput(chalk.gray(`   Strategy: ${options.strategy}`));
        cliOutput(chalk.gray(`   Auto-spawn: ${options.autoSpawn ? 'enabled' : 'disabled'}`));
        cliOutput(chalk.gray(`   Memory: ${options.memory ? 'enabled' : 'disabled'}`));
        cliOutput(chalk.gray(`   GitHub: ${options.github ? 'enabled' : 'disabled'}`));

        if (result.swarmId) {
          cliOutput(chalk.gray(`   Swarm ID: ${result.swarmId}`));
        }

        cliOutput(chalk.green(`\n🚀 Swarm is ready for agent spawning and task orchestration!`));

        // Show next steps
        cliOutput(chalk.cyan(`\n📝 Next steps:`));
        cliOutput(chalk.gray(`   • Spawn agents: npx claude-flow agent spawn --type coder`));
        cliOutput(chalk.gray(`   • Check status: npx claude-flow swarm status`));
        cliOutput(chalk.gray(`   • Start monitoring: npx claude-flow swarm monitor`));

      } else {
        spinner.fail(chalk.red(`❌ Failed to initialize swarm`));
        logger.error('swarm_init_failed', { error: result.error });
        cliOutput(chalk.red(`\nError: ${result.error}`));
        process.exit(1);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      spinner.fail(chalk.red(`❌ Error initializing swarm: ${errorMessage}`));
      logger.error('swarm_init_exception', { error: errorMessage });

        logger.info(chalk.yellow(`\n💡 Make sure the ACGS-2 core is properly installed`);
      if (errorMessage.includes('python3')) {
        cliOutput(chalk.yellow(`\n💡 Make sure Python 3 is installed and available in PATH`));
      } else if (errorMessage.includes('EnhancedAgentBus')) {
        cliOutput(chalk.yellow(`\n💡 Make sure the ACGS-2 core is properly installed`));
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
      logger.info('swarm_status_check_started');

      const status = await getSwarmStatus();

      if (!status || Object.keys(status).length === 0) {
        spinner.warn(chalk.yellow(`⚠️  No active swarm found`));
        logger.info('no_active_swarm');
        cliOutput(chalk.gray(`\n💡 Initialize a swarm first: npx claude-flow swarm init`));
        return;
      logger.info(chalk.blue(`\n🐝 Swarm Status:`);

      spinner.succeed(chalk.green(`✅ Swarm status retrieved!`));
      logger.info('swarm_status_retrieved', { swarmId: status.swarm_id });

      cliOutput(chalk.blue(`\n🐝 Swarm Status:`));

      // Show basic information
      if (status.swarm_id) {
        cliOutput(chalk.gray(`   Swarm ID: ${status.swarm_id}`));
      }
      if (status.topology) {
        cliOutput(chalk.gray(`   Topology: ${status.topology}`));
      }
      if (status.max_agents) {
        cliOutput(chalk.gray(`   Max Agents: ${status.max_agents}`));
      }
      if (status.active_agents !== undefined) {
        cliOutput(chalk.gray(`   Active Agents: ${status.active_agents}`));
      }
      if (status.strategy) {
        cliOutput(chalk.gray(`   Strategy: ${status.strategy}`));
      }

      // Show feature flags
      const features = [];
        logger.info(chalk.gray(`   Features: ${features.join(', ')}`);
      if (status.memory_enabled) features.push('Memory');
      if (status.github_enabled) features.push('GitHub');
      if (features.length > 0) {
        cliOutput(chalk.gray(`   Features: ${features.join(', ')}`));
      }

      if (status.created_at) {
        const created = new Date(status.created_at * 1000);
        cliOutput(chalk.gray(`   Created: ${created.toLocaleString()}`));
      }

      if (status.coordinator_agent) {
        cliOutput(chalk.gray(`   Coordinator: ${status.coordinator_agent}`));
      }
          logger.info(chalk.gray(`   Tenant: ${status.tenant_id}`);
      if (options.verbose) {
        cliOutput(chalk.blue(`\n📊 Detailed Information:`));
        if (status.tenant_id) {
          cliOutput(chalk.gray(`   Tenant: ${status.tenant_id}`));
        }
        if (status.memory_backend) {
          cliOutput(chalk.gray(`   Memory Backend: ${status.memory_backend}`));
        }
        if (status.github_webhook_url) {
          cliOutput(chalk.gray(`   GitHub Webhook: ${status.github_webhook_url}`));
        }
        cliOutput(chalk.gray(`   Constitutional Hash: ${status.constitutional_hash || 'cdd01ef066bc6cf2'}`));
      }

      // Show health indicators
      logger.info(chalk.blue(`\n🏥 Health Status:`);
      logger.info(chalk.gray(`   Agent Utilization: ${activeAgents}/${maxAgents} (${utilization}%)`);
      const utilization = maxAgents > 0 ? Math.round((activeAgents / maxAgents) * 100) : 0;

      cliOutput(chalk.blue(`\n🏥 Health Status:`));
      cliOutput(chalk.gray(`   Agent Utilization: ${activeAgents}/${maxAgents} (${utilization}%)`));

      if (utilization === 0) {
        cliOutput(chalk.yellow(`   Status: Swarm initialized but no agents active`));
      } else if (utilization < 50) {
        cliOutput(chalk.green(`   Status: Swarm healthy with available capacity`));
      } else if (utilization < 90) {
        cliOutput(chalk.yellow(`   Status: Swarm busy, consider scaling`));
      } else {
        cliOutput(chalk.red(`   Status: Swarm at capacity, monitor closely`));
      }

    } catch (error) {
        logger.info(chalk.yellow(`\n💡 Make sure Python 3 is installed and available in PATH`);
      spinner.fail(chalk.red(`❌ Failed to get swarm status: ${errorMessage}`));
      logger.error('swarm_status_failed', { error: errorMessage });

      if (errorMessage.includes('python3')) {
        cliOutput(chalk.yellow(`\n💡 Make sure Python 3 is installed and available in PATH`));
      } else if (errorMessage.includes('EnhancedAgentBus')) {
        cliOutput(chalk.yellow(`\n💡 Make sure the ACGS-2 core is properly installed`));
      }
    }
  });

const monitorCommand = new Command('monitor')
  .description('Monitor swarm activity in real-time')
  .option('-i, --interval <seconds>', 'Monitoring interval in seconds', '5')
  .option('-l, --limit <count>', 'Maximum number of updates to show', '10')
  .option('--metrics', 'Show detailed metrics instead of summary', false)
  .action(async (options) => {
      logger.info(chalk.red(`❌ Invalid interval: ${options.interval}. Must be a positive number.`);
    const limit = parseInt(options.limit, 10);

    if (isNaN(interval) || interval < 1) {
      cliOutput(chalk.red(`❌ Invalid interval: ${options.interval}. Must be a positive number.`));
      logger.warn('invalid_monitor_interval', { interval: options.interval });
      process.exit(1);
    }

    if (isNaN(limit) || limit < 1) {
      cliOutput(chalk.red(`❌ Invalid limit: ${options.limit}. Must be a positive number.`));
      logger.warn('invalid_monitor_limit', { limit: options.limit });
      process.exit(1);
    }

    cliOutput(chalk.blue(`🐝 Starting swarm monitoring...`));
    cliOutput(chalk.gray(`   Interval: ${interval}s | Updates: ${limit}`));
    cliOutput(chalk.gray(`   Press Ctrl+C to stop monitoring`));
    cliOutput('');

    logger.info('swarm_monitor_started', { interval, limit, metrics: options.metrics });

    let updateCount = 0;

    const monitor = async () => {
          logger.info(chalk.yellow(`⚠️  No active swarm detected`);
        const status = await getSwarmStatus();

        if (!status || Object.keys(status).length === 0) {
          cliOutput(chalk.yellow(`⚠️  No active swarm detected`));
          return;
        }

        updateCount++;

        if (options.metrics) {
          // Detailed metrics view
          cliOutput(chalk.blue(`📊 Update ${updateCount} - ${new Date().toLocaleTimeString()}`));
          cliOutput(chalk.gray(`   Active Agents: ${status.active_agents || 0}/${status.max_agents || 8}`));
          cliOutput(chalk.gray(`   Utilization: ${Math.round(status.utilization_percent || 0)}%`));
          cliOutput(chalk.gray(`   Topology: ${status.topology || 'unknown'}`));
          cliOutput(chalk.gray(`   Strategy: ${status.strategy || 'unknown'}`));
          cliOutput('');
        } else {
          // Summary view
          const utilization = Math.round(status.utilization_percent || 0);
          logger.info(`${statusEmoji} ${new Date().toLocaleTimeString()} - ${activeAgents}/${maxAgents} agents (${utilization}%)`;
          const maxAgents = status.max_agents || 8;
          const statusEmoji = utilization < 50 ? '🟢' : utilization < 90 ? '🟡' : '🔴';

          cliOutput(`${statusEmoji} ${new Date().toLocaleTimeString()} - ${activeAgents}/${maxAgents} agents (${utilization}%)`);
        }

        if (updateCount >= limit) {
          cliOutput(chalk.green(`\n✅ Monitoring complete - ${limit} updates shown`));
          logger.info('swarm_monitor_completed', { updates: limit });
          process.exit(0);
        }

      } catch (error) {
        cliOutput(chalk.red(`❌ Monitoring error: ${error instanceof Error ? error.message : String(error)}`));
        logger.error('swarm_monitor_error', { error: error instanceof Error ? error.message : String(error) });
      }
    };

    // Initial monitoring
    await monitor();

    // Set up interval monitoring
      logger.info(chalk.green(`\n🛑 Monitoring stopped by user`);

    // Handle graceful shutdown
    process.on('SIGINT', () => {
      cliOutput(chalk.green(`\n🛑 Monitoring stopped by user`));
      logger.info('swarm_monitor_stopped_by_user');
      clearInterval(monitoringInterval);
      logger.info(chalk.green(`\n🛑 Monitoring stopped`);
    });

    process.on('SIGTERM', () => {
      cliOutput(chalk.green(`\n🛑 Monitoring stopped`));
      logger.info('swarm_monitor_stopped');
      clearInterval(monitoringInterval);
      process.exit(0);
    });
  });

swarmCommand.addCommand(initCommand);
swarmCommand.addCommand(statusCommand);
swarmCommand.addCommand(monitorCommand);
