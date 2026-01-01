import { spawn } from 'child_process';
import { promisify } from 'util';
import path from 'path';

export interface AgentSpawnOptions {
  name: string;
  type: string;
  skills: string[];
}

export interface AgentSpawnResult {
  success: boolean;
  agentId?: string;
  error?: string;
}

export async function spawnAgent(options: AgentSpawnOptions): Promise<AgentSpawnResult> {
  try {
    // Path to the Python spawner script
    // Use src path for development, fallback to dist for production
    let spawnerPath = path.join(__dirname, 'agentSpawner.py');
    if (!require('fs').existsSync(spawnerPath)) {
      // Try the src path from dist
      spawnerPath = path.join(__dirname, '../../src/services/agentSpawner.py');
    }

    // Prepare arguments for the Python script
    const args = [
      spawnerPath,
      options.name,
      options.type,
      JSON.stringify(options.skills)
    ];

    // Spawn the Python process
    const result = await runPythonScript(args);

    if (result.success) {
      return {
        success: true,
        agentId: result.agentId
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

export async function listAgents(): Promise<any[]> {
  try {
    // Path to the Python agent list script
    let listPath = path.join(__dirname, 'agentList.py');
    if (!require('fs').existsSync(listPath)) {
      // Try the src path from dist
      listPath = path.join(__dirname, '../../src/services/agentList.py');
    }

    // Run the Python script to get agent list
    const result = await runPythonScript([listPath]);

    if (result.success) {
      return result.agents || [];
    } else {
      console.warn('Failed to list agents:', result.error);
      return [];
    }

  } catch (error) {
    console.warn('Error listing agents:', error);
    return [];
  }
}

export async function removeAgent(agentId: string): Promise<boolean> {
  // TODO: Implement agent removal
  return true;
}
