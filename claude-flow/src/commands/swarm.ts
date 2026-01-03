import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import { initializeSwarm, getSwarmStatus } from '../services/swarmService';
import { getLogger } from '../../../../../sdk/typescript/src/utils/logger';
const logger = getLogger('swarm');



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

        logger.info(chalk.yellow(`\n📋 Valid topologies: ${VALID_TOPOLOGIES.join(', ')}`);
        logger.info(chalk.gray(`\n💡 Choose based on your use case:`);
        logger.info(chalk.gray(`   • mesh: Research, exploration, brainstorming`);
        logger.info(chalk.gray(`   • hierarchical: Development, structured tasks`);
        logger.info(chalk.gray(`   • ring: Pipeline processing, sequential workflows`);
        logger.info(chalk.gray(`   • star: Simple tasks, centralized control`);
        console.log(chalk.gray(`   • mesh: Research, exploration, brainstorming`));
        console.log(chalk.gray(`   • hierarchical: Development, structured tasks`));
        console.log(chalk.gray(`   • ring: Pipeline processing, sequential workflows`));
        console.log(chalk.gray(`   • star: Simple tasks, centralized control`));
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
        logger.info(chalk.blue(`\n🐝 Swarm Configuration:`);
        logger.info(chalk.gray(`   Topology: ${options.topology}`);
        logger.info(chalk.gray(`   Max Agents: ${maxAgents}`);
        logger.info(chalk.gray(`   Strategy: ${options.strategy}`);
        logger.info(chalk.gray(`   Auto-spawn: ${options.autoSpawn ? 'enabled' : 'disabled'}`);
        logger.info(chalk.gray(`   Memory: ${options.memory ? 'enabled' : 'disabled'}`);
        logger.info(chalk.gray(`   GitHub: ${options.github ? 'enabled' : 'disabled'}`);
        console.log(chalk.gray(`   Strategy: ${options.strategy}`));
        console.log(chalk.gray(`   Auto-spawn: ${options.autoSpawn ? 'enabled' : 'disabled'}`));
          logger.info(chalk.gray(`   Swarm ID: ${result.swarmId}`);
        console.log(chalk.gray(`   GitHub: ${options.github ? 'enabled' : 'disabled'}`));

        logger.info(chalk.green(`\n🚀 Swarm is ready for agent spawning and task orchestration!`);
          console.log(chalk.gray(`   Swarm ID: ${result.swarmId}`));
        }
        logger.info(chalk.cyan(`\n📝 Next steps:`);
        logger.info(chalk.gray(`   • Spawn agents: npx claude-flow agent spawn --type coder`);
        logger.info(chalk.gray(`   • Check status: npx claude-flow swarm status`);
        logger.info(chalk.gray(`   • Start monitoring: npx claude-flow swarm monitor`);
        console.log(chalk.cyan(`\n📝 Next steps:`));
        console.log(chalk.gray(`   • Spawn agents: npx claude-flow agent spawn --type coder`));
        console.log(chalk.gray(`   • Check status: npx claude-flow swarm status`));
        logger.info(chalk.red(`\nError: ${result.error}`);

      } else {
        spinner.fail(chalk.red(`❌ Failed to initialize swarm`));
        logger.error('swarm_init_failed', { error: result.error });
        cliOutput(chalk.red(`\nError: ${result.error}`));
        process.exit(1);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
        logger.info(chalk.yellow(`\n💡 Make sure Python 3 is installed and available in PATH`);

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
        logger.info(chalk.gray(`\n💡 Initialize a swarm first: npx claude-flow swarm init`);

      if (!status || Object.keys(status).length === 0) {
        spinner.warn(chalk.yellow(`⚠️  No active swarm found`));
        logger.info('no_active_swarm');
        cliOutput(chalk.gray(`\n💡 Initialize a swarm first: npx claude-flow swarm init`));
        return;
      logger.info(chalk.blue(`\n🐝 Swarm Status:`);

      spinner.succeed(chalk.green(`✅ Swarm status retrieved!`));
      logger.info('swarm_status_retrieved', { swarmId: status.swarm_id });

        logger.info(chalk.gray(`   Swarm ID: ${status.swarm_id}`);

      // Show basic information
        logger.info(chalk.gray(`   Topology: ${status.topology}`);
        console.log(chalk.gray(`   Swarm ID: ${status.swarm_id}`));
      }
        logger.info(chalk.gray(`   Max Agents: ${status.max_agents}`);
        console.log(chalk.gray(`   Topology: ${status.topology}`));
      }
        logger.info(chalk.gray(`   Active Agents: ${status.active_agents}`);
        console.log(chalk.gray(`   Max Agents: ${status.max_agents}`));
      }
        logger.info(chalk.gray(`   Strategy: ${status.strategy}`);
        console.log(chalk.gray(`   Active Agents: ${status.active_agents}`));
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
        console.log(chalk.gray(`   Features: ${features.join(', ')}`));
        logger.info(chalk.gray(`   Created: ${created.toLocaleString()}`);

      if (status.created_at) {
        const created = new Date(status.created_at * 1000);
        logger.info(chalk.gray(`   Coordinator: ${status.coordinator_agent}`);
      }

      if (status.coordinator_agent) {
        logger.info(chalk.blue(`\n📊 Detailed Information:`);
      }
          logger.info(chalk.gray(`   Tenant: ${status.tenant_id}`);
      if (options.verbose) {
        console.log(chalk.blue(`\n📊 Detailed Information:`));
          logger.info(chalk.gray(`   Memory Backend: ${status.memory_backend}`);
          console.log(chalk.gray(`   Tenant: ${status.tenant_id}`));
        }
          logger.info(chalk.gray(`   GitHub Webhook: ${status.github_webhook_url}`);
          console.log(chalk.gray(`   Memory Backend: ${status.memory_backend}`));
        logger.info(chalk.gray(`   Constitutional Hash: ${status.constitutional_hash || 'cdd01ef066bc6cf2'}`);
        if (status.github_webhook_url) {
          cliOutput(chalk.gray(`   GitHub Webhook: ${status.github_webhook_url}`));
        }
        cliOutput(chalk.gray(`   Constitutional Hash: ${status.constitutional_hash || 'cdd01ef066bc6cf2'}`));
      }

      // Show health indicators
      logger.info(chalk.blue(`\n🏥 Health Status:`);
      logger.info(chalk.gray(`   Agent Utilization: ${activeAgents}/${maxAgents} (${utilization}%)`);
      const utilization = maxAgents > 0 ? Math.round((activeAgents / maxAgents) * 100) : 0;

        logger.info(chalk.yellow(`   Status: Swarm initialized but no agents active`);
      console.log(chalk.gray(`   Agent Utilization: ${activeAgents}/${maxAgents} (${utilization}%)`));
        logger.info(chalk.green(`   Status: Swarm healthy with available capacity`);
      if (utilization === 0) {
        logger.info(chalk.yellow(`   Status: Swarm busy, consider scaling`);
      } else if (utilization < 50) {
        logger.info(chalk.red(`   Status: Swarm at capacity, monitor closely`);
      } else if (utilization < 90) {
        cliOutput(chalk.yellow(`   Status: Swarm busy, consider scaling`));
      } else {
        cliOutput(chalk.red(`   Status: Swarm at capacity, monitor closely`));
      }

    } catch (error) {
        logger.info(chalk.yellow(`\n💡 Make sure Python 3 is installed and available in PATH`);
      spinner.fail(chalk.red(`❌ Failed to get swarm status: ${errorMessage}`));
        logger.info(chalk.yellow(`\n💡 Make sure the ACGS-2 core is properly installed`);
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
      console.log(chalk.red(`❌ Invalid interval: ${options.interval}. Must be a positive number.`));
      logger.info(chalk.red(`❌ Invalid limit: ${options.limit}. Must be a positive number.`);
    }

    if (isNaN(limit) || limit < 1) {
    logger.info(chalk.blue(`🐝 Starting swarm monitoring...`);
    logger.info(chalk.gray(`   Interval: ${interval}s | Updates: ${limit}`);
    logger.info(chalk.gray(`   Press Ctrl+C to stop monitoring`);

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

          logger.info(chalk.blue(`📊 Update ${updateCount} - ${new Date().toLocaleTimeString()}`);
          logger.info(chalk.gray(`   Active Agents: ${status.active_agents || 0}/${status.max_agents || 8}`);
          logger.info(chalk.gray(`   Utilization: ${Math.round(status.utilization_percent || 0)}%`);
          logger.info(chalk.gray(`   Topology: ${status.topology || 'unknown'}`);
          logger.info(chalk.gray(`   Strategy: ${status.strategy || 'unknown'}`);
          console.log(chalk.gray(`   Active Agents: ${status.active_agents || 0}/${status.max_agents || 8}`));
          console.log(chalk.gray(`   Utilization: ${Math.round(status.utilization_percent || 0)}%`));
          console.log(chalk.gray(`   Topology: ${status.topology || 'unknown'}`));
          console.log(chalk.gray(`   Strategy: ${status.strategy || 'unknown'}`));
          console.log();
        } else {
          // Summary view
          const utilization = Math.round(status.utilization_percent || 0);
          logger.info(`${statusEmoji} ${new Date().toLocaleTimeString()} - ${activeAgents}/${maxAgents} agents (${utilization}%)`;
          const maxAgents = status.max_agents || 8;
          const statusEmoji = utilization < 50 ? '🟢' : utilization < 90 ? '🟡' : '🔴';

          logger.info(chalk.green(`\n✅ Monitoring complete - ${limit} updates shown`);
        }

        if (updateCount >= limit) {
          console.log(chalk.green(`\n✅ Monitoring complete - ${limit} updates shown`));
        logger.info(chalk.red(`❌ Monitoring error: ${error instanceof Error ? error.message : String(error)}`);
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
