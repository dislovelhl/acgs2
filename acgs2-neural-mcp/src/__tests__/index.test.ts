/**
 * Tests for acgs2-neural-mcp
 *
 * Tests for NeuralDomainMapper and related functionality.
 */

import { NeuralDomainMapper, DomainNode, DomainEdge } from '../neural/NeuralDomainMapper';

describe('NeuralDomainMapper', () => {
  let mapper: NeuralDomainMapper;

  beforeEach(() => {
    mapper = new NeuralDomainMapper();
  });

  describe('constructor', () => {
    it('should create a new instance with default configuration', () => {
      expect(mapper).toBeInstanceOf(NeuralDomainMapper);
    });

    it('should accept custom training configuration', () => {
      const customMapper = new NeuralDomainMapper({
        learningRate: 0.01,
        epochs: 50,
        batchSize: 16,
      });
      expect(customMapper).toBeInstanceOf(NeuralDomainMapper);
      const stats = customMapper.getModelStats();
      expect(stats.trainingState.learningRate).toBe(0.01);
    });
  });

  describe('getModelStats', () => {
    it('should return model statistics', () => {
      const stats = mapper.getModelStats();

      expect(stats).toHaveProperty('graphSize');
      expect(stats).toHaveProperty('trainingState');
      expect(stats).toHaveProperty('modelVersion');
      expect(stats).toHaveProperty('lastTraining');
      expect(stats).toHaveProperty('cohesionScore');
    });

    it('should have zero nodes and edges initially', () => {
      const stats = mapper.getModelStats();

      expect(stats.graphSize.nodes).toBe(0);
      expect(stats.graphSize.edges).toBe(0);
    });
  });

  describe('convertToGraph', () => {
    const testDomains = [
      {
        id: 'domain_a',
        name: 'Domain A',
        type: 'functional' as const,
        metadata: {
          size: 5,
          complexity: 0.6,
          stability: 0.9,
          dependencies: ['domain_b'],
        },
      },
      {
        id: 'domain_b',
        name: 'Domain B',
        type: 'technical' as const,
        metadata: {
          size: 3,
          complexity: 0.4,
          stability: 0.95,
          dependencies: [],
        },
      },
    ];

    const testRelationships = [
      {
        source: 'domain_a',
        target: 'domain_b',
        type: 'dependency' as const,
        weight: 0.9,
      },
    ];

    it('should convert domains to graph structure', () => {
      const graph = mapper.convertToGraph(testDomains, testRelationships);

      expect(graph).toHaveProperty('nodes');
      expect(graph).toHaveProperty('edges');
      expect(graph).toHaveProperty('metadata');
    });

    it('should create correct number of nodes', () => {
      mapper.convertToGraph(testDomains, testRelationships);
      const stats = mapper.getModelStats();

      expect(stats.graphSize.nodes).toBe(2);
    });

    it('should create correct number of edges', () => {
      mapper.convertToGraph(testDomains, testRelationships);
      const stats = mapper.getModelStats();

      expect(stats.graphSize.edges).toBe(1);
    });

    it('should update graph metadata', () => {
      const graph = mapper.convertToGraph(testDomains, testRelationships);

      expect(graph.metadata.totalNodes).toBe(2);
      expect(graph.metadata.totalEdges).toBe(1);
    });

    it('should handle empty domains array', () => {
      const graph = mapper.convertToGraph([], []);
      const stats = mapper.getModelStats();

      expect(stats.graphSize.nodes).toBe(0);
      expect(stats.graphSize.edges).toBe(0);
    });

    it('should handle domains without metadata', () => {
      const domainsWithoutMetadata = [
        { id: 'simple', name: 'Simple Domain', type: 'data' as const },
      ];

      const graph = mapper.convertToGraph(domainsWithoutMetadata, []);
      const stats = mapper.getModelStats();

      expect(stats.graphSize.nodes).toBe(1);
    });
  });

  describe('calculateDomainCohesion', () => {
    const testDomains = [
      {
        id: 'core',
        name: 'Core Module',
        type: 'functional' as const,
        metadata: { size: 10, complexity: 0.7, stability: 0.9, dependencies: [] },
      },
      {
        id: 'utils',
        name: 'Utilities',
        type: 'functional' as const,
        metadata: { size: 5, complexity: 0.3, stability: 0.95, dependencies: [] },
      },
      {
        id: 'api',
        name: 'API Layer',
        type: 'api' as const,
        metadata: { size: 8, complexity: 0.6, stability: 0.85, dependencies: ['core'] },
      },
    ];

    const testRelationships = [
      { source: 'core', target: 'utils', type: 'dependency' as const, weight: 0.8 },
      { source: 'api', target: 'core', type: 'dependency' as const, weight: 1.0 },
    ];

    beforeEach(() => {
      mapper.convertToGraph(testDomains, testRelationships);
    });

    it('should calculate cohesion analysis', async () => {
      const analysis = await mapper.calculateDomainCohesion();

      expect(analysis).toHaveProperty('overallScore');
      expect(analysis).toHaveProperty('domainScores');
      expect(analysis).toHaveProperty('factors');
      expect(analysis).toHaveProperty('weakPoints');
      expect(analysis).toHaveProperty('recommendations');
    });

    it('should return overall score between 0 and 1', async () => {
      const analysis = await mapper.calculateDomainCohesion();

      expect(analysis.overallScore).toBeGreaterThanOrEqual(0);
      expect(analysis.overallScore).toBeLessThanOrEqual(1);
    });

    it('should include cohesion factors', async () => {
      const analysis = await mapper.calculateDomainCohesion();

      expect(analysis.factors).toHaveProperty('structural');
      expect(analysis.factors).toHaveProperty('functional');
      expect(analysis.factors).toHaveProperty('behavioral');
      expect(analysis.factors).toHaveProperty('semantic');
    });

    it('should have domain scores for each domain', async () => {
      const analysis = await mapper.calculateDomainCohesion();

      expect(analysis.domainScores.size).toBe(3);
      expect(analysis.domainScores.has('core')).toBe(true);
      expect(analysis.domainScores.has('utils')).toBe(true);
      expect(analysis.domainScores.has('api')).toBe(true);
    });
  });

  describe('identifyCrossDomainDependencies', () => {
    const testDomains = [
      { id: 'a', name: 'A', type: 'functional' as const },
      { id: 'b', name: 'B', type: 'functional' as const },
      { id: 'c', name: 'C', type: 'functional' as const },
    ];

    const linearRelationships = [
      { source: 'a', target: 'b', type: 'dependency' as const },
      { source: 'b', target: 'c', type: 'dependency' as const },
    ];

    beforeEach(() => {
      mapper.convertToGraph(testDomains, linearRelationships);
    });

    it('should analyze dependencies', async () => {
      const analysis = await mapper.identifyCrossDomainDependencies();

      expect(analysis).toHaveProperty('graph');
      expect(analysis).toHaveProperty('circularDependencies');
      expect(analysis).toHaveProperty('criticalPaths');
      expect(analysis).toHaveProperty('metrics');
      expect(analysis).toHaveProperty('optimizations');
    });

    it('should build dependency graph', async () => {
      const analysis = await mapper.identifyCrossDomainDependencies();

      expect(analysis.graph.size).toBe(3);
    });

    it('should include metrics', async () => {
      const analysis = await mapper.identifyCrossDomainDependencies();

      expect(analysis.metrics).toHaveProperty('averageInDegree');
      expect(analysis.metrics).toHaveProperty('averageOutDegree');
      expect(analysis.metrics).toHaveProperty('maxDepth');
      expect(analysis.metrics).toHaveProperty('cyclomaticComplexity');
    });

    it('should detect no circular dependencies in linear graph', async () => {
      const analysis = await mapper.identifyCrossDomainDependencies();

      // Linear dependencies should not have cycles
      expect(analysis.circularDependencies.length).toBe(0);
    });
  });

  describe('provideBoundaryOptimization', () => {
    const testDomains = [
      { id: 'd1', name: 'Domain 1', type: 'functional' as const },
      { id: 'd2', name: 'Domain 2', type: 'functional' as const },
    ];

    const testRelationships = [
      { source: 'd1', target: 'd2', type: 'dependency' as const, weight: 0.9 },
    ];

    beforeEach(() => {
      mapper.convertToGraph(testDomains, testRelationships);
    });

    it('should provide optimization recommendations', async () => {
      const optimization = await mapper.provideBoundaryOptimization();

      expect(optimization).toHaveProperty('proposals');
      expect(optimization).toHaveProperty('optimizationScore');
      expect(optimization).toHaveProperty('priority');
    });

    it('should have valid priority value', async () => {
      const optimization = await mapper.provideBoundaryOptimization();

      expect(['low', 'medium', 'high', 'critical']).toContain(optimization.priority);
    });

    it('should have optimization score', async () => {
      const optimization = await mapper.provideBoundaryOptimization();

      expect(typeof optimization.optimizationScore).toBe('number');
    });
  });

  describe('train', () => {
    beforeEach(() => {
      const domains = [
        { id: 't1', name: 'Test 1', type: 'functional' as const },
        { id: 't2', name: 'Test 2', type: 'technical' as const },
      ];
      const relationships = [
        { source: 't1', target: 't2', type: 'dependency' as const },
      ];
      mapper.convertToGraph(domains, relationships);
    });

    it('should train the model with training data', async () => {
      const trainingData = {
        inputs: [
          { features: Array.from({ length: 64 }, () => Math.random()) },
          { features: Array.from({ length: 64 }, () => Math.random()) },
        ],
        outputs: [0, 1],
        batchSize: 2,
        epochs: 5,
      };

      const result = await mapper.train(trainingData);

      expect(result).toHaveProperty('finalAccuracy');
      expect(result).toHaveProperty('trainingHistory');
      expect(result).toHaveProperty('bestModel');
    });

    it('should return training history', async () => {
      const trainingData = {
        inputs: [
          { features: Array.from({ length: 64 }, () => Math.random()) },
        ],
        outputs: [0],
        batchSize: 1,
        epochs: 3,
      };

      const result = await mapper.train(trainingData);

      expect(result.trainingHistory.length).toBeGreaterThan(0);
      expect(result.trainingHistory[0]).toHaveProperty('epoch');
      expect(result.trainingHistory[0]).toHaveProperty('loss');
      expect(result.trainingHistory[0]).toHaveProperty('accuracy');
    });

    it('should prevent concurrent training', async () => {
      const trainingData = {
        inputs: [{ features: Array.from({ length: 64 }, () => Math.random()) }],
        outputs: [0],
        batchSize: 1,
        epochs: 10,
      };

      // Start first training
      const firstTraining = mapper.train(trainingData);

      // Attempt second training should fail
      await expect(mapper.train(trainingData)).rejects.toThrow(
        'Training already in progress'
      );

      // Wait for first training to complete
      await firstTraining;
    });
  });

  describe('predict', () => {
    beforeEach(async () => {
      const domains = [
        { id: 'p1', name: 'Predict 1', type: 'functional' as const },
      ];
      mapper.convertToGraph(domains, []);

      // Train the model first
      const trainingData = {
        inputs: [
          { features: Array.from({ length: 64 }, () => Math.random()) },
        ],
        outputs: [0],
        batchSize: 1,
        epochs: 2,
      };
      await mapper.train(trainingData);
    });

    it('should make predictions', async () => {
      const input = { features: Array.from({ length: 64 }, () => Math.random()) };
      const prediction = await mapper.predict(input);

      expect(prediction).toHaveProperty('input');
      expect(prediction).toHaveProperty('output');
      expect(prediction).toHaveProperty('confidence');
      expect(prediction).toHaveProperty('alternatives');
    });

    it('should return confidence score', async () => {
      const input = { features: Array.from({ length: 64 }, () => Math.random()) };
      const prediction = await mapper.predict(input);

      expect(typeof prediction.confidence).toBe('number');
      expect(prediction.confidence).toBeGreaterThanOrEqual(0);
      expect(prediction.confidence).toBeLessThanOrEqual(1);
    });

    it('should return alternative predictions', async () => {
      const input = { features: Array.from({ length: 64 }, () => Math.random()) };
      const prediction = await mapper.predict(input);

      expect(Array.isArray(prediction.alternatives)).toBe(true);
    });
  });

  describe('exportModel and importModel', () => {
    it('should export model state', () => {
      const domains = [
        { id: 'e1', name: 'Export 1', type: 'data' as const },
      ];
      mapper.convertToGraph(domains, []);

      const exported = mapper.exportModel();

      expect(exported).toHaveProperty('graph');
      expect(exported).toHaveProperty('weights');
      expect(exported).toHaveProperty('biases');
      expect(exported).toHaveProperty('trainingState');
      expect(exported).toHaveProperty('config');
    });

    it('should import model state', () => {
      const domains = [
        { id: 'i1', name: 'Import 1', type: 'data' as const },
      ];
      mapper.convertToGraph(domains, []);

      const exported = mapper.exportModel();

      // Create a new mapper and import
      const newMapper = new NeuralDomainMapper();
      newMapper.importModel(exported);

      const stats = newMapper.getModelStats();
      expect(stats.graphSize.nodes).toBe(1);
    });
  });

  describe('analyzeDomains', () => {
    it('should analyze domains comprehensively', async () => {
      const graph = mapper.convertToGraph(
        [
          { id: 'an1', name: 'Analysis 1', type: 'functional' as const },
          { id: 'an2', name: 'Analysis 2', type: 'technical' as const },
        ],
        [{ source: 'an1', target: 'an2', type: 'dependency' as const }]
      );

      const analysis = await mapper.analyzeDomains(graph);

      expect(analysis).toHaveProperty('cohesion');
      expect(analysis).toHaveProperty('dependencies');
      expect(analysis).toHaveProperty('optimization');
      expect(analysis).toHaveProperty('recommendations');
    });

    it('should return recommendations as array', async () => {
      const graph = mapper.convertToGraph(
        [{ id: 'r1', name: 'Rec 1', type: 'functional' as const }],
        []
      );

      const analysis = await mapper.analyzeDomains(graph);

      expect(Array.isArray(analysis.recommendations)).toBe(true);
    });
  });
});
