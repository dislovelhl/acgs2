import pino from "pino";
import config from "../config/index.js";

const isProduction = process.env.NODE_ENV === "production";

export const logger = pino({
  level: config.LOG_LEVEL?.toLowerCase() || "info",
  base: {
    service: config.MCP_NAME || "acgs2-neural-mcp",
    version: config.MCP_VERSION,
  },
  transport: isProduction
    ? undefined
    : {
        target: "pino-pretty",
        options: {
          colorize: true,
          ignore: "pid,hostname",
          translateTime: "SYS:standard",
        },
      },
  formatters: {
    level: (label) => {
      return { level: label.toUpperCase() };
    },
  },
  timestamp: pino.stdTimeFunctions.isoTime,
});

export default logger;
