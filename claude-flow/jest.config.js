/**
 * Jest configuration for claude-flow
 *
 * TypeScript testing with ts-jest preset.
 * Coverage thresholds set to 85% for CI/CD enforcement.
 * Cobertura reporter for Codecov integration.
 */
module.exports = {
  // Use ts-jest preset for TypeScript support
  preset: 'ts-jest',

  // Node environment for CLI application testing
  testEnvironment: 'node',

  // Root directories for module resolution
  roots: ['<rootDir>/src'],

  // Test file patterns
  testMatch: ['**/__tests__/**/*.test.ts'],

  // Coverage collection configuration
  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/**/*.d.ts',
    '!src/**/__tests__/**',
  ],

  // Coverage output directory
  coverageDirectory: 'coverage',

  // Coverage reporters for local and CI/CD usage
  // - text: terminal output
  // - lcov: browser-viewable HTML report (in coverage/lcov-report/)
  // - html: alternative HTML report
  // - cobertura: XML format for Codecov CI/CD integration
  coverageReporters: ['text', 'lcov', 'html', 'cobertura'],

  // Coverage thresholds (85% minimum for CI enforcement)
  coverageThreshold: {
    global: {
      branches: 85,
      functions: 85,
      lines: 85,
      statements: 85,
    },
  },

  // Paths to ignore for coverage
  coveragePathIgnorePatterns: [
    '/node_modules/',
    '/dist/',
    '/coverage/',
  ],

  // Module name mapper for path aliases if needed
  moduleNameMapper: {},

  // Clear mocks between tests
  clearMocks: true,

  // Verbose output for better debugging
  verbose: true,
};
