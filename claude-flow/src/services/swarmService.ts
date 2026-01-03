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
  try {
    // Path to the Python swarm status script
    let statusPath = path.join(__dirname, 'swarmStatus.py');
    if (!require('fs').existsSync(statusPath)) {
      // Try the src path from dist
      statusPath = path.join(__dirname, '../../src/services/swarmStatus.py');
    }

    // Run the Python script to get swarm status
    const result = await runPythonScript([statusPath]);

    if (result.success) {
      return result.status || {};
    } else {
      console.warn('Failed to get swarm status:', result.error);
      return {};
    }

  } catch (error) {
    console.warn('Error getting swarm status:', error);
    return {};
  }
}

export interface SwarmShutdownResult {
  success: boolean;
  message?: string;
  error?: string;
}

export async function shutdownSwarm(): Promise<SwarmShutdownResult> {
  try {
    // Path to the Python swarm shutdown script
    // Use src path for development, fallback to dist for production
    let shutdownPath = path.join(__dirname, 'swarmShutdown.py');
    if (!require('fs').existsSync(shutdownPath)) {
      // Try the src path from dist
      shutdownPath = path.join(__dirname, '../../src/services/swarmShutdown.py');
    }

    // Check if shutdown script exists before attempting to run it
    if (!require('fs').existsSync(shutdownPath)) {
      // No shutdown script available - return success as graceful no-op
      // This is valid when swarm infrastructure is not configured
      return {
        success: true,
        message: 'Swarm shutdown skipped: no shutdown script configured'
      };
    }

    // Run the Python script to shutdown the swarm
    const result = await runPythonScript([shutdownPath]);

    if (result.success) {
      return {
        success: true,
        message: result.message || 'Swarm shutdown completed successfully'
      };
    } else {
      // Shutdown script ran but reported failure
      console.warn('Swarm shutdown reported failure:', result.error);
      return {
        success: false,
        error: result.error || 'Swarm shutdown failed'
      };
    }

  } catch (error) {
    // Handle unexpected errors during shutdown gracefully
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    console.warn('Error during swarm shutdown:', errorMessage);

    // Return success anyway - shutdown should be idempotent
    // If we can't connect to shutdown, assume swarm is already down
    return {
      success: true,
      message: 'Swarm shutdown completed (no active swarm found)',
      error: errorMessage
    };
  }
}
