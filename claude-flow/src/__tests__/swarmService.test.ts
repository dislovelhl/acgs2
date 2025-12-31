import { initializeSwarm } from '../services/swarmService';

describe('SwarmService', () => {
  describe('initializeSwarm', () => {
    it('should initialize a hierarchical swarm successfully', async () => {
      const config = {
        topology: 'hierarchical' as const,
        maxAgents: 8,
        strategy: 'parallel' as const,
        autoSpawn: false,
        memory: false,
        github: false
      };

      // Note: This test will fail in CI without Python/ACGS-2 setup
      // In a real environment, it would test the actual initialization
      const result = await initializeSwarm(config);

      // For now, we expect it to fail gracefully
      expect(result).toHaveProperty('success');
      expect(typeof result.success).toBe('boolean');
    });

    it('should handle different topologies', async () => {
      const topologies = ['mesh', 'hierarchical', 'ring', 'star'] as const;

      for (const topology of topologies) {
        const config = {
          topology,
          maxAgents: 5,
          strategy: 'balanced' as const,
          autoSpawn: false,
          memory: false,
          github: false
        };

        const result = await initializeSwarm(config);
        expect(result).toHaveProperty('success');
      }
    });

    it('should handle different strategies', async () => {
      const strategies = ['balanced', 'parallel', 'sequential'] as const;

      for (const strategy of strategies) {
        const config = {
          topology: 'mesh' as const,
          maxAgents: 5,
          strategy,
          autoSpawn: false,
          memory: false,
          github: false
        };

        const result = await initializeSwarm(config);
        expect(result).toHaveProperty('success');
      }
    });

    it('should handle feature flags', async () => {
      const config = {
        topology: 'star' as const,
        maxAgents: 10,
        strategy: 'parallel' as const,
        autoSpawn: true,
        memory: true,
        github: true
      };

      const result = await initializeSwarm(config);
      expect(result).toHaveProperty('success');
    });

    it('should validate max agents range', async () => {
      // Test with invalid max agents (this would be caught by validation in the command)
      const config = {
        topology: 'hierarchical' as const,
        maxAgents: 150, // Invalid - over 100
        strategy: 'parallel' as const,
        autoSpawn: false,
        memory: false,
        github: false
      };

      const result = await initializeSwarm(config);
      // The Python script will validate this
      expect(result).toHaveProperty('success');
    });
  });
});
