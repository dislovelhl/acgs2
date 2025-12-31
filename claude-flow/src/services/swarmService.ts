import { spawn } from 'child_process';
import { promisify } from 'util';
import path from 'path';

export interface SwarmConfig {
  topology: 'mesh' | 'hierarchical' | 'ring' | 'star';
  maxAgents: number;
  strategy: 'balanced' | 'parallel' | 'sequential';
  autoSpawn: boolean;
  memory: boolean;
  github: boolean;
}

export interface SwarmInitResult {
  success: boolean;
  swarmId?: string;
  error?: string;
}

export async function initializeSwarm(config: SwarmConfig): Promise<SwarmInitResult> {
  try {
    // Path to the Python swarm initializer script
    // Use src path for development, fallback to dist for production
    let initializerPath = path.join(__dirname, 'swarmInitializer.py');
    if (!require('fs').existsSync(initializerPath)) {
      // Try the src path from dist
      initializerPath = path.join(__dirname, '../../src/services/swarmInitializer.py');
    }

    // Prepare arguments for the Python script
    const args = [
      initializerPath,
      config.topology,
      config.maxAgents.toString(),
      config.strategy,
      config.autoSpawn.toString(),
      config.memory.toString(),
      config.github.toString()
    ];

    // Spawn the Python process
    const result = await runPythonScript(args);

    if (result.success) {
      return {
        success: true,
        swarmId: result.swarmId
      };
    } else {
      return {
        success: false,
        error: result.error
      };
    }

  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error occurred'
    };
  }
}

async function runPythonScript(args: string[]): Promise<any> {
  return new Promise((resolve, reject) => {
    const pythonProcess = spawn('python3', args, {
      stdio: ['pipe', 'pipe', 'pipe'],
      cwd: path.dirname(args[0])
    });

    let stdout = '';
    let stderr = '';

    pythonProcess.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    pythonProcess.on('close', (code) => {
      if (code === 0) {
        try {
          const result = JSON.parse(stdout.trim());
          resolve(result);
        } catch (e) {
          reject(new Error(`Failed to parse Python output: ${stdout}`));
        }
      } else {
        reject(new Error(`Python script failed with code ${code}: ${stderr}`));
      }
    });

    pythonProcess.on('error', (error) => {
      reject(error);
    });
  });
}

export async function getSwarmStatus(): Promise<any> {
  // TODO: Implement getting swarm status
  return {};
}

export async function shutdownSwarm(): Promise<boolean> {
  // TODO: Implement swarm shutdown
  return true;
}
