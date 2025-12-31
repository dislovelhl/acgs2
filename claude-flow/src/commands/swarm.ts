import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import { initializeSwarm } from '../services/swarmService';

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

swarmCommand.addCommand(initCommand);
