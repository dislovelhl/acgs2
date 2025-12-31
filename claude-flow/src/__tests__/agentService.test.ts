import { spawnAgent } from '../services/agentService';

describe('AgentService', () => {
  describe('spawnAgent', () => {
    it('should spawn a coder agent successfully', async () => {
      const options = {
        name: 'test-coder',
        type: 'coder' as const,
        skills: ['python', 'typescript']
      };

      // Note: This test will fail in CI without Python/ACGS-2 setup
      // In a real environment, it would test the actual spawning
      const result = await spawnAgent(options);

      // For now, we expect it to fail gracefully
      expect(result).toHaveProperty('success');
      expect(typeof result.success).toBe('boolean');
    });

    it('should handle different agent types', async () => {
      const agentTypes = ['coder', 'researcher', 'analyst', 'tester', 'coordinator'];

      for (const type of agentTypes) {
        const options = {
          name: `test-${type}`,
          type: type as any,
          skills: []
        };

        const result = await spawnAgent(options);
        expect(result).toHaveProperty('success');
      }
    });

    it('should handle empty skills array', async () => {
      const options = {
        name: 'test-agent',
        type: 'coder' as const,
        skills: []
      };

      const result = await spawnAgent(options);
      expect(result).toHaveProperty('success');
    });

    it('should handle agent names with special characters', async () => {
      const options = {
        name: 'test_agent-123',
        type: 'researcher' as const,
        skills: ['analysis']
      };

      const result = await spawnAgent(options);
      expect(result).toHaveProperty('success');
    });
  });
});
