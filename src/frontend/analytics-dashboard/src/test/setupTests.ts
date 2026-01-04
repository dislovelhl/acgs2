/**
 * Test Setup for Analytics Dashboard
 *
 * Configures testing environment with:
 * - Jest DOM matchers for DOM assertions
 * - MSW (Mock Service Worker) for API mocking
 * - Fetch polyfill for Node.js environment
 * - LocalStorage mock for persistence tests
 */

import "@testing-library/jest-dom";
import { afterAll, afterEach, beforeAll, vi } from "vitest";
import { cleanup } from "@testing-library/react";
import { server } from "./mocks/server";

// Setup MSW server before tests
beforeAll(() => {
  server.listen({ onUnhandledRequest: "warn" });
});

// Reset handlers after each test
afterEach(() => {
  cleanup();
  server.resetHandlers();
  localStorage.clear();
});

// Clean up after all tests
afterAll(() => {
  server.close();
});

// Mock window.matchMedia for responsive tests
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock ResizeObserver for react-grid-layout
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

// Mock import.meta.env
vi.stubEnv("VITE_ANALYTICS_API_URL", "http://localhost:8080");
vi.stubEnv("VITE_TENANT_ID", "acgs-dev");
