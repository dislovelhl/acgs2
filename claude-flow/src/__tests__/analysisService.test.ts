import { performAnalysis } from '../services/analysisService';

describe('AnalysisService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Mock fs operations
    jest.spyOn(require('fs'), 'statSync').mockReturnValue({
      isFile: () => true
    } as any);
    jest.spyOn(require('fs'), 'readFileSync').mockReturnValue('test content');
    jest.spyOn(require('fs'), 'readdirSync').mockReturnValue(['test.py', 'test.js']);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('performAnalysis', () => {
    it('should perform quality analysis successfully', async () => {
      const options = {
        target: '.',
        focus: 'quality' as const,
        depth: 'quick' as const,
        format: 'text' as const,
        includePatterns: ['*.py'],
        excludePatterns: ['node_modules/**']
      };

      const result = await performAnalysis(options);

      expect(result.focus).toBe('quality');
      expect(result.depth).toBe('quick');
      expect(result.summary.filesAnalyzed).toBeGreaterThanOrEqual(0);
      expect(Array.isArray(result.findings)).toBe(true);
      expect(Array.isArray(result.recommendations)).toBe(true);
      expect(typeof result.metrics).toBe('object');
    });

    it('should perform security analysis successfully', async () => {
      const options = {
        target: '.',
        focus: 'security' as const,
        depth: 'deep' as const,
        format: 'json' as const,
        includePatterns: ['*.py'],
        excludePatterns: ['node_modules/**']
      };

      const result = await performAnalysis(options);

      expect(result.focus).toBe('security');
      expect(result.depth).toBe('deep');
      expect(result.format).toBe('json');
    });

    it('should perform performance analysis successfully', async () => {
      const options = {
        target: '.',
        focus: 'performance' as const,
        depth: 'quick' as const,
        format: 'report' as const,
        includePatterns: ['*.js'],
        excludePatterns: ['node_modules/**']
      };

      const result = await performAnalysis(options);

      expect(result.focus).toBe('performance');
      expect(result.format).toBe('report');
    });

    it('should perform architecture analysis successfully', async () => {
      const options = {
        target: '.',
        focus: 'architecture' as const,
        depth: 'deep' as const,
        format: 'text' as const,
        includePatterns: ['*.ts'],
        excludePatterns: ['node_modules/**']
      };

      const result = await performAnalysis(options);

      expect(result.focus).toBe('architecture');
    });

    it('should handle file analysis results', async () => {
      const options = {
        target: '.',
        focus: 'quality' as const,
        depth: 'quick' as const,
        format: 'text' as const,
        includePatterns: ['*.py'],
        excludePatterns: ['node_modules/**']
      };

      const result = await performAnalysis(options);

      expect(result.summary.filesAnalyzed).toBeGreaterThanOrEqual(0);
      expect(Array.isArray(result.findings)).toBe(true);
      expect(Array.isArray(result.recommendations)).toBe(true);
    });

    it('should handle different analysis depths', async () => {
      const options = {
        target: '.',
        focus: 'quality' as const,
        depth: 'deep' as const,
        format: 'text' as const,
        includePatterns: ['*.py'],
        excludePatterns: ['node_modules/**']
      };

      const result = await performAnalysis(options);

      expect(result.depth).toBe('deep');
    });
  });
});
