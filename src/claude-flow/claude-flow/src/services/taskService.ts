import { spawn } from "child_process";
import path from "path";

export interface TaskOrchestrationOptions {
  task: string;
  strategy: string;
  priority: string;
}

export interface TaskOrchestrationResult {
  success: boolean;
  taskId?: string;
  workflowId?: string;
  error?: string;
}

export async function orchestrateTask(
  options: TaskOrchestrationOptions
): Promise<TaskOrchestrationResult> {
  try {
    // Path to the Python orchestrator script
    let orchestratorPath = path.join(__dirname, "taskOrchestrator.py");
    if (!require("fs").existsSync(orchestratorPath)) {
      // Try the src path from dist
      orchestratorPath = path.join(
        __dirname,
        "../../src/services/taskOrchestrator.py"
      );
    }

    // Prepare arguments for the Python script
    const args = [
      orchestratorPath,
      options.task,
      options.strategy,
      options.priority,
    ];

    // Spawn the Python process
    const result = await runPythonScript(args);

    if (result.success) {
      return {
        success: true,
        taskId: result.taskId,
        workflowId: result.workflowId,
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
