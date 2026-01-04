import { spawn } from "child_process";
import * as path from "path";
import * as fs from "fs";
import logger from "../utils/logger.js";

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

export async function spawnAgent(
  options: AgentSpawnOptions
): Promise<AgentSpawnResult> {
  try {
    // Path to the Python spawner script
    // Use src path for development, fallback to dist for production
    let spawnerPath = path.join(__dirname, "agentSpawner.py");
    if (!require("fs").existsSync(spawnerPath)) {
      // Try the src path from dist
      spawnerPath = path.join(__dirname, "../../src/services/agentSpawner.py");
    }

    // Prepare arguments for the Python script
    const args = [
      spawnerPath,
      options.name,
      options.type,
      JSON.stringify(options.skills),
    ];

    // Spawn the Python process
    const result = await runPythonScript(args);

    if (result.success) {
      return {
        success: true,
        agentId: result.agentId,
      };
    } else {
      return {
        success: false,
        error: result.error,
      };
    }
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error occurred",
    };
  }
}

async function runPythonScript(args: string[]): Promise<any> {
  return new Promise((resolve, reject) => {
    const pythonProcess = spawn("python3", args, {
      stdio: ["pipe", "pipe", "pipe"],
      cwd: path.dirname(args[0]),
    });

    let stdout = "";
    let stderr = "";

    pythonProcess.stdout.on("data", (data) => {
      stdout += data.toString();
    });

    pythonProcess.stderr.on("data", (data) => {
      stderr += data.toString();
    });

    pythonProcess.on("close", (code) => {
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

    pythonProcess.on("error", (error) => {
      reject(error);
    });
  });
}

export async function listAgents(): Promise<any[]> {
  try {
    // Path to the Python agent list script
    let listPath = path.join(__dirname, "agentList.py");
    if (!require("fs").existsSync(listPath)) {
      // Try the src path from dist
      listPath = path.join(__dirname, "../../src/services/agentList.py");
    }

    // Run the Python script to get agent list
    const result = await runPythonScript([listPath]);

    if (result.success) {
      return result.agents || [];
    }
    if (result.error) {
      logger.warn({ error: result.error }, "Failed to list agents");
      return [];
    }
  } catch (error) {
    console.warn("Error listing agents:", error);
    return [];
  }
}

export interface AgentRemovalResult {
  success: boolean;
  agentId?: string;
  message?: string;
  error?: string;
}

export async function removeAgent(
  agentId: string
): Promise<AgentRemovalResult> {
  try {
    // Path to the Python agent remover script
    // Use src path for development, fallback to dist for production
    let removerPath = path.join(__dirname, "agentRemover.py");
    if (!require("fs").existsSync(removerPath)) {
      // Try the src path from dist
      removerPath = path.join(__dirname, "../../src/services/agentRemover.py");
    }

    // Prepare arguments for the Python script
    const args = [removerPath, agentId];

    // Run the Python script to remove the agent
    const result = await runPythonScript(args);

    if (result.success) {
      return {
        success: true,
        agentId: result.agentId,
        message: result.message,
      };
    } else {
      return {
        success: false,
        error: result.error,
      };
    }
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error occurred",
    };
  }
}
