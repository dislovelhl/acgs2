/**
 * MSW Server Configuration
 *
 * Sets up Mock Service Worker for intercepting API requests
 * during testing.
 */

import { setupServer } from "msw/node";
import { handlers } from "./handlers";

/**
 * MSW server instance for testing
 * Use this server in setupTests.ts to enable API mocking
 */
export const server = setupServer(...handlers);
