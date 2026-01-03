/**
 * Configuration Validator Tests
 *
 * Comprehensive test suite for configuration validation covering:
 * - Happy path (valid configurations)
 * - Invalid inputs (types, formats, ranges)
 * - Security policy enforcement
 * - Error messages with remediation guidance
 *
 * @module validator.test
 */

import {
  validateConfig,
  validateConfigSafe,
  validateConfigOrExit,
  createPartialValidator,
  isValidConfigValue,
  ConfigValidationError,
  ValidationResult,
  EnvConfig,
} from '../../config/validator';

describe('Configuration Validator', () => {
  /**
   * Helper to create a valid base configuration.
   * All required fields with valid defaults.
   */
  function createValidConfig(): Record<string, string> {
    return {
      TENANT_ID: 'test-tenant',
      ENVIRONMENT: 'development',
      LOG_LEVEL: 'INFO',
      DEBUG: 'false',
      RELOAD: 'false',
      REDIS_URL: 'redis://localhost:6379',
      REDIS_PASSWORD: '',
      KAFKA_BOOTSTRAP: '',
      KAFKA_PASSWORD: '',
      AGENT_BUS_URL: 'http://localhost:8000',
      OPA_URL: 'http://localhost:8181',
      HITL_APPROVALS_URL: 'http://localhost:8002',
      HITL_APPROVALS_PORT: '8002',
      DEFAULT_ESCALATION_TIMEOUT_MINUTES: '30',
      CRITICAL_ESCALATION_TIMEOUT_MINUTES: '15',
      EMERGENCY_ESCALATION_TIMEOUT_MINUTES: '60',
    };
  }

  describe('Happy Path - Valid Configurations', () => {
    it('should accept valid configuration with all required fields', () => {
      const validConfig = createValidConfig();

      const result = validateConfigSafe(validConfig);

      expect(result.success).toBe(true);
      expect(result.config).toBeDefined();
      expect(result.errors).toBeUndefined();
    });

    it('should accept valid configuration with default values', () => {
      // Minimal config - most fields have defaults
      const minimalConfig = {};

      const result = validateConfigSafe(minimalConfig);

      expect(result.success).toBe(true);
      expect(result.config).toBeDefined();
      expect(result.config!.TENANT_ID).toBe('acgs-dev'); // default
      expect(result.config!.ENVIRONMENT).toBe('development'); // default
      expect(result.config!.LOG_LEVEL).toBe('INFO'); // default
      expect(result.config!.DEBUG).toBe(false); // default
    });

    it('should accept development environment with DEBUG enabled', () => {
      const config = createValidConfig();
      config.ENVIRONMENT = 'development';
      config.DEBUG = 'true';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(true);
      expect(result.config!.DEBUG).toBe(true);
    });

    it('should accept staging environment with DEBUG enabled', () => {
      const config = createValidConfig();
      config.ENVIRONMENT = 'staging';
      config.DEBUG = 'true';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(true);
      expect(result.config!.DEBUG).toBe(true);
    });

    it('should transform boolean strings correctly', () => {
      const testCases = [
        { input: 'true', expected: true },
        { input: 'TRUE', expected: true },
        { input: '1', expected: true },
        { input: 'yes', expected: true },
        { input: 'YES', expected: true },
        { input: 'false', expected: false },
        { input: 'FALSE', expected: false },
        { input: '0', expected: false },
        { input: 'no', expected: false },
        { input: 'NO', expected: false },
        { input: '', expected: false },
      ];

      for (const testCase of testCases) {
        const config = createValidConfig();
        config.DEBUG = testCase.input;

        const result = validateConfigSafe(config);

        expect(result.success).toBe(true);
        expect(result.config!.DEBUG).toBe(testCase.expected);
      }
    });

    it('should transform timeout strings to numbers', () => {
      const config = createValidConfig();
      config.DEFAULT_ESCALATION_TIMEOUT_MINUTES = '45';
      config.CRITICAL_ESCALATION_TIMEOUT_MINUTES = '10';
      config.EMERGENCY_ESCALATION_TIMEOUT_MINUTES = '120';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(true);
      expect(result.config!.DEFAULT_ESCALATION_TIMEOUT_MINUTES).toBe(45);
      expect(result.config!.CRITICAL_ESCALATION_TIMEOUT_MINUTES).toBe(10);
      expect(result.config!.EMERGENCY_ESCALATION_TIMEOUT_MINUTES).toBe(120);
    });

    it('should accept valid URL formats', () => {
      const config = createValidConfig();
      config.REDIS_URL = 'redis://my-redis-server:6379';
      config.AGENT_BUS_URL = 'https://api.example.com/bus';
      config.OPA_URL = 'http://opa.internal:8181';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(true);
    });

    it('should accept valid log levels', () => {
      const logLevels = ['DEBUG', 'INFO', 'WARN', 'ERROR'];

      for (const level of logLevels) {
        const config = createValidConfig();
        config.LOG_LEVEL = level;

        const result = validateConfigSafe(config);

        expect(result.success).toBe(true);
        expect(result.config!.LOG_LEVEL).toBe(level);
      }
    });

    it('should accept valid environments', () => {
      const environments = ['development', 'staging', 'production'];

      for (const env of environments) {
        const config = createValidConfig();
        config.ENVIRONMENT = env;
        // For production, ensure security constraints are met
        if (env === 'production') {
          config.DEBUG = 'false';
          config.RELOAD = 'false';
          config.REDIS_PASSWORD = 'securepassword123';
        }

        const result = validateConfigSafe(config);

        expect(result.success).toBe(true);
        expect(result.config!.ENVIRONMENT).toBe(env);
      }
    });
  });

  describe('Invalid Inputs - Type Validation', () => {
    it('should reject invalid TENANT_ID (empty string)', () => {
      const config = createValidConfig();
      config.TENANT_ID = '';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
      expect(result.errors).toBeDefined();
      expect(result.errors!.some(e => e.field.includes('TENANT_ID'))).toBe(true);
    });

    it('should reject invalid ENVIRONMENT value', () => {
      const config = createValidConfig();
      config.ENVIRONMENT = 'invalid-env';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
      expect(result.errors).toBeDefined();
      expect(result.errors!.some(e => e.field.includes('ENVIRONMENT'))).toBe(true);
    });

    it('should reject invalid LOG_LEVEL value', () => {
      const config = createValidConfig();
      config.LOG_LEVEL = 'VERBOSE';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
      expect(result.errors).toBeDefined();
      expect(result.errors!.some(e => e.field.includes('LOG_LEVEL'))).toBe(true);
    });
  });

  describe('Invalid Inputs - URL Validation', () => {
    it('should reject invalid REDIS_URL format', () => {
      const config = createValidConfig();
      config.REDIS_URL = 'not-a-valid-url';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
      expect(result.errors!.some(e => e.field.includes('REDIS_URL'))).toBe(true);
    });

    it('should reject REDIS_URL with wrong protocol', () => {
      const config = createValidConfig();
      config.REDIS_URL = 'http://localhost:6379'; // Should be redis://

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
      expect(result.errors!.some(e => e.field.includes('REDIS_URL'))).toBe(true);
    });

    it('should reject invalid AGENT_BUS_URL format', () => {
      const config = createValidConfig();
      config.AGENT_BUS_URL = 'invalid-url';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
      expect(result.errors!.some(e => e.field.includes('AGENT_BUS_URL'))).toBe(true);
    });

    it('should reject invalid OPA_URL format', () => {
      const config = createValidConfig();
      config.OPA_URL = 'ftp://wrong-protocol.com';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
      expect(result.errors!.some(e => e.field.includes('OPA_URL'))).toBe(true);
    });
  });

  describe('Invalid Inputs - Port Validation', () => {
    it('should reject invalid HITL_APPROVALS_PORT (negative)', () => {
      const config = createValidConfig();
      config.HITL_APPROVALS_PORT = '-1';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
      expect(result.errors!.some(e => e.field.includes('HITL_APPROVALS_PORT'))).toBe(true);
    });

    it('should reject invalid HITL_APPROVALS_PORT (zero)', () => {
      const config = createValidConfig();
      config.HITL_APPROVALS_PORT = '0';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
      expect(result.errors!.some(e => e.field.includes('HITL_APPROVALS_PORT'))).toBe(true);
    });

    it('should reject invalid HITL_APPROVALS_PORT (too large)', () => {
      const config = createValidConfig();
      config.HITL_APPROVALS_PORT = '70000';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
      expect(result.errors!.some(e => e.field.includes('HITL_APPROVALS_PORT'))).toBe(true);
    });

    it('should reject non-numeric HITL_APPROVALS_PORT', () => {
      const config = createValidConfig();
      config.HITL_APPROVALS_PORT = 'abc';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
    });

    it('should accept valid port values', () => {
      const validPorts = ['1', '80', '443', '8080', '65535'];

      for (const port of validPorts) {
        const config = createValidConfig();
        config.HITL_APPROVALS_PORT = port;

        const result = validateConfigSafe(config);

        expect(result.success).toBe(true);
        expect(result.config!.HITL_APPROVALS_PORT).toBe(parseInt(port, 10));
      }
    });
  });

  describe('Invalid Inputs - Timeout Validation', () => {
    it('should reject negative timeout values', () => {
      const config = createValidConfig();
      config.DEFAULT_ESCALATION_TIMEOUT_MINUTES = '-5';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
    });

    it('should reject zero timeout values', () => {
      const config = createValidConfig();
      config.CRITICAL_ESCALATION_TIMEOUT_MINUTES = '0';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
    });

    it('should reject non-numeric timeout values', () => {
      const config = createValidConfig();
      config.EMERGENCY_ESCALATION_TIMEOUT_MINUTES = 'invalid';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
    });
  });

  describe('Security Policy Enforcement', () => {
    it('should reject DEBUG=true in production environment', () => {
      const config = createValidConfig();
      config.ENVIRONMENT = 'production';
      config.DEBUG = 'true';
      config.REDIS_PASSWORD = 'securepassword123';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
      expect(result.errors).toBeDefined();
      expect(result.errors!.some(e =>
        e.rule === 'security_violation' &&
        e.message.includes('DEBUG')
      )).toBe(true);
    });

    it('should reject RELOAD=true in production environment', () => {
      const config = createValidConfig();
      config.ENVIRONMENT = 'production';
      config.RELOAD = 'true';
      config.REDIS_PASSWORD = 'securepassword123';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
      expect(result.errors).toBeDefined();
      expect(result.errors!.some(e =>
        e.rule === 'security_violation' &&
        e.message.includes('RELOAD')
      )).toBe(true);
    });

    it('should reject weak REDIS_PASSWORD in production', () => {
      const config = createValidConfig();
      config.ENVIRONMENT = 'production';
      config.REDIS_PASSWORD = 'short'; // Less than 8 characters

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
      expect(result.errors).toBeDefined();
      expect(result.errors!.some(e =>
        e.rule === 'security_violation' &&
        e.field.includes('REDIS_PASSWORD')
      )).toBe(true);
    });

    it('should accept production with valid security settings', () => {
      const config = createValidConfig();
      config.ENVIRONMENT = 'production';
      config.DEBUG = 'false';
      config.RELOAD = 'false';
      config.REDIS_PASSWORD = 'securepassword123'; // 8+ characters

      const result = validateConfigSafe(config);

      expect(result.success).toBe(true);
    });

    it('should allow empty REDIS_PASSWORD in non-production', () => {
      const config = createValidConfig();
      config.ENVIRONMENT = 'development';
      config.REDIS_PASSWORD = '';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(true);
    });

    it('should report multiple security violations at once', () => {
      const config = createValidConfig();
      config.ENVIRONMENT = 'production';
      config.DEBUG = 'true';
      config.RELOAD = 'true';
      config.REDIS_PASSWORD = 'weak';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
      expect(result.errors!.length).toBeGreaterThanOrEqual(3);
    });
  });

  describe('Error Messages with Remediation Guidance', () => {
    it('should include remediation in validation errors', () => {
      const config = createValidConfig();
      config.ENVIRONMENT = 'invalid';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
      expect(result.errors).toBeDefined();
      expect(result.errors![0].remediation).toBeDefined();
      expect(result.errors![0].remediation.length).toBeGreaterThan(0);
    });

    it('should include field name in validation errors', () => {
      const config = createValidConfig();
      config.LOG_LEVEL = 'TRACE';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
      expect(result.errors![0].field).toBeDefined();
      expect(result.errors![0].field).toContain('LOG_LEVEL');
    });

    it('should include rule in validation errors', () => {
      const config = createValidConfig();
      config.REDIS_URL = 'not-a-url';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
      expect(result.errors![0].rule).toBeDefined();
    });

    it('should include message in validation errors', () => {
      const config = createValidConfig();
      config.HITL_APPROVALS_PORT = 'abc';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
      expect(result.errors![0].message).toBeDefined();
    });

    it('should redact sensitive field values', () => {
      const config = createValidConfig();
      config.ENVIRONMENT = 'production';
      config.REDIS_PASSWORD = 'short';

      const result = validateConfigSafe(config);

      // Security violation errors should not expose the actual password value
      const passwordError = result.errors!.find(e => e.field.includes('REDIS_PASSWORD'));
      expect(passwordError).toBeDefined();
      // The remediation should not contain the actual weak password
      expect(passwordError!.remediation).not.toContain('short');
    });

    it('should provide URL-specific remediation for URL validation failures', () => {
      const config = createValidConfig();
      config.REDIS_URL = 'http://wrong-protocol:6379';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
      const urlError = result.errors!.find(e => e.field.includes('REDIS_URL'));
      expect(urlError).toBeDefined();
      // Remediation should mention URL format
      expect(urlError!.message.toLowerCase()).toMatch(/url|protocol|format/);
    });
  });

  describe('validateConfig (throwing variant)', () => {
    it('should return valid config on success', () => {
      const config = createValidConfig();

      const result = validateConfig(config);

      expect(result).toBeDefined();
      expect(result.TENANT_ID).toBe('test-tenant');
    });

    it('should throw ConfigValidationError on failure', () => {
      const config = createValidConfig();
      config.ENVIRONMENT = 'invalid';

      expect(() => validateConfig(config)).toThrow(ConfigValidationError);
    });

    it('should include all error details in thrown error', () => {
      const config = createValidConfig();
      config.ENVIRONMENT = 'invalid';

      try {
        validateConfig(config);
        fail('Should have thrown');
      } catch (error) {
        expect(error).toBeInstanceOf(ConfigValidationError);
        const validationError = error as ConfigValidationError;
        expect(validationError.errors).toBeDefined();
        expect(validationError.errors.length).toBeGreaterThan(0);
        expect(validationError.message).toContain('Remediation');
      }
    });

    it('should mark security violations appropriately', () => {
      const config = createValidConfig();
      config.ENVIRONMENT = 'production';
      config.DEBUG = 'true';
      config.REDIS_PASSWORD = 'securepassword123';

      try {
        validateConfig(config);
        fail('Should have thrown');
      } catch (error) {
        expect(error).toBeInstanceOf(ConfigValidationError);
        const validationError = error as ConfigValidationError;
        expect(validationError.isSecurityViolation).toBe(true);
      }
    });
  });

  describe('validateConfigOrExit', () => {
    let mockExit: jest.SpyInstance;
    let mockStderr: jest.SpyInstance;

    beforeEach(() => {
      mockExit = jest.spyOn(process, 'exit').mockImplementation((code?: number) => {
        throw new Error(`process.exit(${code})`);
      });
      mockStderr = jest.spyOn(process.stderr, 'write').mockImplementation(() => true);
    });

    afterEach(() => {
      mockExit.mockRestore();
      mockStderr.mockRestore();
    });

    it('should return config on successful validation', () => {
      const config = createValidConfig();

      const result = validateConfigOrExit(config);

      expect(result).toBeDefined();
      expect(result.TENANT_ID).toBe('test-tenant');
      expect(mockExit).not.toHaveBeenCalled();
    });

    it('should exit with code 1 on validation failure', () => {
      const config = createValidConfig();
      config.ENVIRONMENT = 'invalid';

      expect(() => validateConfigOrExit(config)).toThrow('process.exit(1)');
      expect(mockExit).toHaveBeenCalledWith(1);
    });

    it('should write error message to stderr on failure', () => {
      const config = createValidConfig();
      config.ENVIRONMENT = 'invalid';

      try {
        validateConfigOrExit(config);
      } catch {
        // Expected
      }

      expect(mockStderr).toHaveBeenCalled();
      const stderrCalls = mockStderr.mock.calls.map(c => c[0]).join('');
      expect(stderrCalls).toContain('ERROR');
      expect(stderrCalls).toContain('Remediation');
    });

    it('should show SECURITY VIOLATION header for security errors', () => {
      const config = createValidConfig();
      config.ENVIRONMENT = 'production';
      config.DEBUG = 'true';
      config.REDIS_PASSWORD = 'securepassword123';

      try {
        validateConfigOrExit(config);
      } catch {
        // Expected
      }

      const stderrCalls = mockStderr.mock.calls.map(c => c[0]).join('');
      expect(stderrCalls).toContain('SECURITY VIOLATION');
    });
  });

  describe('createPartialValidator', () => {
    it('should validate only specified fields', () => {
      const validator = createPartialValidator(['TENANT_ID', 'ENVIRONMENT']);

      const result = validator({
        TENANT_ID: 'test-tenant',
        ENVIRONMENT: 'development',
      });

      expect(result.success).toBe(true);
    });

    it('should fail if specified fields are invalid', () => {
      const validator = createPartialValidator(['TENANT_ID', 'ENVIRONMENT']);

      const result = validator({
        TENANT_ID: 'test-tenant',
        ENVIRONMENT: 'invalid-env',
      });

      expect(result.success).toBe(false);
      expect(result.errors).toBeDefined();
    });

    it('should ignore unspecified fields', () => {
      const validator = createPartialValidator(['TENANT_ID']);

      const result = validator({
        TENANT_ID: 'test-tenant',
        ENVIRONMENT: 'invalid-value', // Not in the specified fields
      });

      expect(result.success).toBe(true);
    });

    it('should handle missing optional fields', () => {
      const validator = createPartialValidator(['LOG_LEVEL']);

      const result = validator({}); // LOG_LEVEL not provided

      expect(result.success).toBe(true);
    });
  });

  describe('isValidConfigValue', () => {
    it('should return true for valid values', () => {
      expect(isValidConfigValue('ENVIRONMENT', 'development')).toBe(true);
      expect(isValidConfigValue('ENVIRONMENT', 'staging')).toBe(true);
      expect(isValidConfigValue('ENVIRONMENT', 'production')).toBe(true);
      expect(isValidConfigValue('LOG_LEVEL', 'INFO')).toBe(true);
      expect(isValidConfigValue('LOG_LEVEL', 'DEBUG')).toBe(true);
    });

    it('should return false for invalid values', () => {
      expect(isValidConfigValue('ENVIRONMENT', 'invalid')).toBe(false);
      expect(isValidConfigValue('LOG_LEVEL', 'VERBOSE')).toBe(false);
    });

    it('should handle optional fields', () => {
      // Optional fields should accept undefined/empty
      expect(isValidConfigValue('REDIS_PASSWORD', '')).toBe(true);
      expect(isValidConfigValue('KAFKA_PASSWORD', '')).toBe(true);
    });
  });

  describe('ConfigValidationError class', () => {
    it('should have correct name property', () => {
      const error = new ConfigValidationError('Test error', [], false);
      expect(error.name).toBe('ConfigValidationError');
    });

    it('should store errors array', () => {
      const errors = [
        {
          field: 'TEST_FIELD',
          rule: 'test_rule',
          message: 'Test message',
          remediation: 'Test remediation',
        },
      ];
      const error = new ConfigValidationError('Test error', errors, false);
      expect(error.errors).toEqual(errors);
    });

    it('should store security violation flag', () => {
      const error1 = new ConfigValidationError('Test', [], false);
      const error2 = new ConfigValidationError('Test', [], true);

      expect(error1.isSecurityViolation).toBe(false);
      expect(error2.isSecurityViolation).toBe(true);
    });

    it('should be an instance of Error', () => {
      const error = new ConfigValidationError('Test', [], false);
      expect(error).toBeInstanceOf(Error);
    });
  });

  describe('Edge Cases', () => {
    it('should handle completely empty config object', () => {
      const result = validateConfigSafe({});

      // Should use all defaults
      expect(result.success).toBe(true);
      expect(result.config).toBeDefined();
    });

    it('should handle undefined values', () => {
      const config = createValidConfig();
      (config as any).UNDEFINED_FIELD = undefined;

      const result = validateConfigSafe(config);

      expect(result.success).toBe(true);
    });

    it('should handle null values gracefully', () => {
      const config = createValidConfig();
      (config as any).TENANT_ID = null;

      // Should fail validation (null is not a valid string)
      const result = validateConfigSafe(config);
      expect(result.success).toBe(false);
    });

    it('should handle extra fields gracefully', () => {
      const config = createValidConfig();
      (config as any).EXTRA_UNKNOWN_FIELD = 'some value';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(true);
    });

    it('should handle whitespace in string values', () => {
      const config = createValidConfig();
      config.TENANT_ID = '  tenant-with-spaces  ';

      const result = validateConfigSafe(config);

      // Should accept (trimming is up to the schema implementation)
      expect(result.success).toBe(true);
    });

    it('should handle boolean-like string values for DEBUG', () => {
      const config = createValidConfig();
      config.DEBUG = '  TRUE  ';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(true);
      expect(result.config!.DEBUG).toBe(true);
    });

    it('should validate rediss:// protocol for secure Redis', () => {
      const config = createValidConfig();
      config.REDIS_URL = 'rediss://secure-redis:6379';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(true);
    });

    it('should validate https:// protocol for AGENT_BUS_URL', () => {
      const config = createValidConfig();
      config.AGENT_BUS_URL = 'https://secure-bus.example.com';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(true);
    });
  });

  describe('formatZodError Coverage - Error Code Branches', () => {
    it('should handle invalid_type errors (wrong type provided)', () => {
      // Passing a number where string is expected triggers invalid_type
      const configWithWrongType = {
        TENANT_ID: 123 as unknown as string, // Wrong type
      };

      const result = validateConfigSafe(configWithWrongType);

      expect(result.success).toBe(false);
      expect(result.errors).toBeDefined();
      expect(result.errors!.some(e => e.rule === 'invalid_type')).toBe(true);
      expect(result.errors![0].remediation).toContain('correct type');
    });

    it('should handle too_small errors (minimum length violation)', () => {
      const config = createValidConfig();
      config.TENANT_ID = ''; // Empty string violates min(1)

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
      expect(result.errors).toBeDefined();
      expect(result.errors!.some(e => e.rule === 'too_small')).toBe(true);
      expect(result.errors![0].remediation).toContain('too short');
    });

    it('should handle invalid_enum_value errors', () => {
      const config = createValidConfig();
      config.ENVIRONMENT = 'invalid-env';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
      expect(result.errors).toBeDefined();
      expect(result.errors!.some(e => e.rule === 'invalid_enum_value')).toBe(true);
      expect(result.errors![0].remediation).toContain('valid options');
    });

    it('should handle custom errors from transform functions', () => {
      const config = createValidConfig();
      config.HITL_APPROVALS_PORT = 'not-a-number';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
      expect(result.errors).toBeDefined();
      // Transform errors become 'custom' errors
      expect(result.errors!.some(e => e.rule === 'custom')).toBe(true);
    });

    it('should handle custom errors from timeout transforms', () => {
      const config = createValidConfig();
      config.DEFAULT_ESCALATION_TIMEOUT_MINUTES = 'invalid-timeout';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
      expect(result.errors).toBeDefined();
      expect(result.errors!.some(e => e.rule === 'custom')).toBe(true);
    });

    it('should handle custom URL validation errors (refine)', () => {
      const config = createValidConfig();
      // OPA_URL uses refine which produces custom errors
      config.OPA_URL = 'invalid-url-format';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
      expect(result.errors).toBeDefined();
      const urlError = result.errors!.find(e => e.field.includes('OPA_URL'));
      expect(urlError).toBeDefined();
    });

    it('should handle multiple validation errors simultaneously', () => {
      const configWithMultipleErrors = {
        TENANT_ID: '', // too_small
        ENVIRONMENT: 'invalid-env', // invalid_enum_value
        HITL_APPROVALS_PORT: 'abc', // custom
      };

      const result = validateConfigSafe(configWithMultipleErrors);

      expect(result.success).toBe(false);
      expect(result.errors).toBeDefined();
      expect(result.errors!.length).toBeGreaterThanOrEqual(3);
    });

    it('should provide remediation for all error types', () => {
      const configWithErrors = {
        TENANT_ID: '', // too_small
        ENVIRONMENT: 'invalid', // invalid_enum_value
        LOG_LEVEL: 'VERBOSE', // invalid_enum_value
        REDIS_URL: 'bad-url', // custom (refine)
      };

      const result = validateConfigSafe(configWithErrors);

      expect(result.success).toBe(false);
      expect(result.errors).toBeDefined();

      // All errors should have remediation guidance
      for (const error of result.errors!) {
        expect(error.remediation).toBeDefined();
        expect(error.remediation.length).toBeGreaterThan(0);
      }
    });
  });

  describe('Validation Error Details', () => {
    it('should include correct field paths in nested errors', () => {
      const result = validateConfigSafe({
        TENANT_ID: 123 as unknown as string,
      });

      expect(result.success).toBe(false);
      expect(result.errors).toBeDefined();
      const error = result.errors![0];
      expect(error.field).toBe('TENANT_ID');
    });

    it('should not expose sensitive values in providedValue', () => {
      // The formatZodError function checks SENSITIVE_FIELDS
      // For sensitive fields, providedValue should be '[REDACTED]' or undefined
      const config = createValidConfig();
      config.ENVIRONMENT = 'production';
      config.REDIS_PASSWORD = 'weak'; // Short password in production

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
      const passwordError = result.errors!.find(e => e.field.includes('REDIS_PASSWORD'));
      if (passwordError && passwordError.providedValue) {
        expect(passwordError.providedValue).toBe('[REDACTED]');
      }
    });

    it('should include message in all error details', () => {
      const result = validateConfigSafe({
        ENVIRONMENT: 'invalid',
      });

      expect(result.success).toBe(false);
      expect(result.errors![0].message).toBeDefined();
      expect(result.errors![0].message.length).toBeGreaterThan(0);
    });

    it('should include rule in all error details', () => {
      const result = validateConfigSafe({
        LOG_LEVEL: 'INVALID',
      });

      expect(result.success).toBe(false);
      expect(result.errors![0].rule).toBeDefined();
    });
  });

  describe('Security Policy Edge Cases', () => {
    it('should detect DEBUG security violation even with other valid fields', () => {
      const config = createValidConfig();
      config.ENVIRONMENT = 'production';
      config.DEBUG = 'true';
      config.RELOAD = 'false';
      config.REDIS_PASSWORD = 'strongpassword123';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
      expect(result.errors!.some(e =>
        e.rule === 'security_violation' && e.field === 'production-debug-mode'
      )).toBe(true);
    });

    it('should detect RELOAD security violation even with other valid fields', () => {
      const config = createValidConfig();
      config.ENVIRONMENT = 'production';
      config.DEBUG = 'false';
      config.RELOAD = 'true';
      config.REDIS_PASSWORD = 'strongpassword123';

      const result = validateConfigSafe(config);

      expect(result.success).toBe(false);
      expect(result.errors!.some(e =>
        e.rule === 'security_violation' && e.field === 'production-reload-mode'
      )).toBe(true);
    });

    it('should validate production with empty KAFKA_PASSWORD (optional)', () => {
      const config = createValidConfig();
      config.ENVIRONMENT = 'production';
      config.DEBUG = 'false';
      config.RELOAD = 'false';
      config.REDIS_PASSWORD = 'strongpassword123';
      config.KAFKA_PASSWORD = ''; // Optional

      const result = validateConfigSafe(config);

      expect(result.success).toBe(true);
    });

    it('should fail production with weak KAFKA_PASSWORD when provided', () => {
      const config = createValidConfig();
      config.ENVIRONMENT = 'production';
      config.DEBUG = 'false';
      config.RELOAD = 'false';
      config.REDIS_PASSWORD = 'strongpassword123';
      config.KAFKA_PASSWORD = 'short'; // Too short

      const result = validateConfigSafe(config);

      // The ProductionSecuritySchema makes KAFKA_PASSWORD optional
      // So short non-empty passwords should trigger the min(8) validation
      expect(result.success).toBe(false);
      expect(result.errors!.some(e => e.field.includes('KAFKA_PASSWORD'))).toBe(true);
    });
  });

  describe('Partial Validator Edge Cases', () => {
    it('should validate empty field list', () => {
      const validator = createPartialValidator([]);

      const result = validator({
        TENANT_ID: 'anything',
        ENVIRONMENT: 'invalid',
      });

      // No fields to validate means success
      expect(result.success).toBe(true);
    });

    it('should validate single field', () => {
      const validator = createPartialValidator(['ENVIRONMENT']);

      const validResult = validator({ ENVIRONMENT: 'production' });
      expect(validResult.success).toBe(true);

      const invalidResult = validator({ ENVIRONMENT: 'invalid' });
      expect(invalidResult.success).toBe(false);
    });

    it('should handle fields not present in config', () => {
      const validator = createPartialValidator(['LOG_LEVEL', 'TENANT_ID']);

      const result = validator({}); // Neither field provided

      // Should succeed with defaults
      expect(result.success).toBe(true);
    });
  });

  describe('isValidConfigValue Edge Cases', () => {
    it('should validate boolean-like strings for DEBUG', () => {
      expect(isValidConfigValue('DEBUG', 'true')).toBe(true);
      expect(isValidConfigValue('DEBUG', 'false')).toBe(true);
      expect(isValidConfigValue('DEBUG', '1')).toBe(true);
      expect(isValidConfigValue('DEBUG', '0')).toBe(true);
    });

    it('should validate timeout values', () => {
      expect(isValidConfigValue('DEFAULT_ESCALATION_TIMEOUT_MINUTES', '30')).toBe(true);
      expect(isValidConfigValue('DEFAULT_ESCALATION_TIMEOUT_MINUTES', '1')).toBe(true);
    });

    it('should reject invalid timeout values', () => {
      expect(isValidConfigValue('DEFAULT_ESCALATION_TIMEOUT_MINUTES', '0')).toBe(false);
      expect(isValidConfigValue('DEFAULT_ESCALATION_TIMEOUT_MINUTES', '-5')).toBe(false);
      expect(isValidConfigValue('DEFAULT_ESCALATION_TIMEOUT_MINUTES', 'abc')).toBe(false);
    });

    it('should validate URL fields', () => {
      expect(isValidConfigValue('REDIS_URL', 'redis://localhost:6379')).toBe(true);
      expect(isValidConfigValue('REDIS_URL', 'rediss://secure:6379')).toBe(true);
      expect(isValidConfigValue('AGENT_BUS_URL', 'http://localhost:8000')).toBe(true);
      expect(isValidConfigValue('AGENT_BUS_URL', 'https://secure.example.com')).toBe(true);
    });

    it('should reject invalid URLs', () => {
      expect(isValidConfigValue('REDIS_URL', 'http://wrong-protocol')).toBe(false);
      expect(isValidConfigValue('REDIS_URL', 'not-a-url')).toBe(false);
    });

    it('should validate port values', () => {
      expect(isValidConfigValue('HITL_APPROVALS_PORT', '8080')).toBe(true);
      expect(isValidConfigValue('HITL_APPROVALS_PORT', '1')).toBe(true);
      expect(isValidConfigValue('HITL_APPROVALS_PORT', '65535')).toBe(true);
    });

    it('should reject invalid port values', () => {
      expect(isValidConfigValue('HITL_APPROVALS_PORT', '0')).toBe(false);
      expect(isValidConfigValue('HITL_APPROVALS_PORT', '70000')).toBe(false);
      expect(isValidConfigValue('HITL_APPROVALS_PORT', 'abc')).toBe(false);
    });
  });
});
