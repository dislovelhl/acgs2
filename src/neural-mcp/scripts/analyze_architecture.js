#!/usr/bin/env node
/**
 * Run a full Neural MCP analysis cycle (load → train → patterns → deps → optimize)
 * and print a compact summary.
 *
 * Note: MCP servers communicate over stdio. This script spawns the server,
 * sends JSON-RPC requests, and parses line-delimited JSON responses.
 */

const { spawn } = require("child_process");

const REQUESTS = [
  {
    id: 1,
    name: "neural_load_domains",
    arguments: { preset: "enhanced_agent_bus" },
  },
  {
    id: 2,
    name: "neural_train",
    arguments: { epochs: 50, learningRate: 0.001 },
  },
  { id: 3, name: "neural_patterns", arguments: {} },
  { id: 4, name: "neural_dependencies", arguments: {} },
  { id: 5, name: "neural_optimize", arguments: {} },
];

function buildToolCall({ id, name, arguments: args }) {
  return {
    jsonrpc: "2.0",
    id,
    method: "tools/call",
    params: { name, arguments: args || {} },
  };
}

function safeJsonParse(str) {
  try {
    return JSON.parse(str);
  } catch {
    return null;
  }
}

function pct(x) {
  if (typeof x !== "number" || Number.isNaN(x)) return "N/A";
  return `${(x * 100).toFixed(1)}%`;
}

function num(x, digits = 3) {
  if (typeof x !== "number" || Number.isNaN(x)) return "N/A";
  return x.toFixed(digits);
}

async function main() {
  const server = spawn("node", ["dist/index.js"], {
    cwd: `${__dirname}/..`,
    stdio: ["pipe", "pipe", "pipe"],
    env: {
      ...process.env,
      // best-effort: suppress dotenv v17 startup tip noise
      DOTENV_CONFIG_QUIET: "true",
    },
  });

  const responses = new Map();
  let stdoutBuf = "";
  let ready = false;

  const done = () => responses.size >= REQUESTS.length;

  const maybeFinish = () => {
    if (!done()) return;
    try {
      server.kill();
    } catch {
      // ignore
    }
  };

  server.stdout.on("data", (chunk) => {
    stdoutBuf += chunk.toString();
    const lines = stdoutBuf.split("\n");
    stdoutBuf = lines.pop() || "";

    for (const raw of lines) {
      const line = raw.trim();
      if (!line.startsWith("{")) continue;
      const parsed = safeJsonParse(line);
      if (!parsed || typeof parsed.id !== "number") continue;
      responses.set(parsed.id, parsed);
    }

    maybeFinish();
  });

  const onReady = (data) => {
    const text = data.toString();
    if (!ready && text.includes("running on stdio")) {
      ready = true;
      for (const req of REQUESTS) {
        server.stdin.write(JSON.stringify(buildToolCall(req)) + "\n");
      }
    }
  };

  server.stderr.on("data", onReady);
  server.stdout.on("data", onReady);

  // Hard timeout
  const timeout = setTimeout(() => {
    try {
      server.kill();
    } catch {
      // ignore
    }
    console.error("❌ Timed out waiting for MCP responses");
    process.exitCode = 1;
  }, 60000);

  // Wait until all responses are collected (or timeout)
  while (!done() && server.exitCode == null) {
    // eslint-disable-next-line no-await-in-loop
    await new Promise((r) => setTimeout(r, 50));
  }

  clearTimeout(timeout);
  if (!done()) return;

  const payload = (id) => {
    const resp = responses.get(id);
    const text = resp?.result?.content?.[0]?.text;
    return safeJsonParse(text);
  };

  const load = payload(1);
  const train = payload(2);
  const patterns = payload(3);
  const deps = payload(4);
  const opt = payload(5);

  console.log("\n### Neural MCP Architecture Summary\n");
  console.log(
    `- **Domains**: ${load?.graphSize?.nodes ?? "?"} nodes, ${load?.graphSize?.edges ?? "?"} edges`
  );
  console.log(
    `- **Training**: acc ${pct(train?.result?.finalAccuracy)}, loss ${num(train?.result?.finalLoss, 4)}, epochs ${train?.result?.totalEpochs ?? "?"}`
  );
  console.log(
    `- **Cohesion**: overall ${pct(patterns?.overallScore)} (struct ${pct(patterns?.factors?.structural)}, func ${pct(patterns?.factors?.functional)}, beh ${pct(patterns?.factors?.behavioral)}, sem ${pct(patterns?.factors?.semantic)})`
  );
  console.log(
    `- **Dependencies**: maxDepth ${deps?.metrics?.maxDepth ?? "?"}, cyclomatic ${deps?.metrics?.cyclomaticComplexity ?? "?"}, criticalPaths ${deps?.criticalPaths?.length ?? "?"}`
  );
  console.log(
    `- **Optimization**: score ${num(opt?.optimizationScore, 3)}, priority ${opt?.priority ?? "?"}, proposals ${opt?.proposals?.length ?? "?"}`
  );

  if (Array.isArray(patterns?.weakPoints) && patterns.weakPoints.length > 0) {
    console.log("\n### Top Weak Points\n");
    patterns.weakPoints.slice(0, 5).forEach((w) => {
      console.log(
        `- **${w.domainId}**: score ${num(w.score, 3)} — ${w.reason}`
      );
    });
  }

  if (Array.isArray(opt?.proposals) && opt.proposals.length > 0) {
    console.log("\n### Top Optimization Proposals\n");
    opt.proposals.slice(0, 5).forEach((p) => {
      console.log(
        `- **${p.type.toUpperCase()}** \`${p.id}\`: ${p.domains.join(", ")} (conf ${pct(p.confidence)})`
      );
    });
  }
}

main().catch((err) => {
  console.error("❌ Failed:", err);
  process.exitCode = 1;
});
