import pino from "pino";
import config from "../config/index.js";

const isProduction = config.ENVIRONMENT === "production";

export const logger = pino({
  level: config.LOG_LEVEL?.toLowerCase() || "info",
  base: {
    service: "claude-flow",
    env: config.ENVIRONMENT,
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
