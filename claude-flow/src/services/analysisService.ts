import * as fs from 'fs';
import * as path from 'path';
import { spawn } from 'child_process';

export interface AnalysisOptions {
  target: string;
  focus: 'quality' | 'security' | 'performance' | 'architecture';
  depth: 'quick' | 'deep';
  format: 'text' | 'json' | 'report';
  includePatterns: string[];
  excludePatterns: string[];
}

export interface AnalysisResult {
  target: string;
  focus: string;
  depth: string;
  format: string;
  summary: {
    filesAnalyzed: number;
    totalLines: number;
    analysisTime: number;
  };
  findings: Finding[];
  recommendations: Recommendation[];
  metrics: Record<string, any>;
}

export interface Finding {
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  category: string;
  message: string;
  file?: string;
  line?: number;
  code?: string;
  recommendation?: string;
}

export interface Recommendation {
  description: string;
  priority: 'high' | 'medium' | 'low';
  estimatedEffort: string;
  benefits?: string;
  category: string;
}

export async function performAnalysis(options: AnalysisOptions): Promise<AnalysisResult> {
  const startTime = Date.now();

  try {
    // Discover files to analyze
    const files = discoverFiles(options.target, options.includePatterns, options.excludePatterns);

    // Perform analysis based on focus
    let findings: Finding[] = [];
    let recommendations: Recommendation[] = [];
    let metrics: Record<string, any> = {};

    switch (options.focus) {
      case 'quality':
        ({ findings, recommendations, metrics } = await analyzeQuality(files, options.depth));
        break;
      case 'security':
        ({ findings, recommendations, metrics } = await analyzeSecurity(files, options.depth));
        break;
      case 'performance':
        ({ findings, recommendations, metrics } = await analyzePerformance(files, options.depth));
        break;
      case 'architecture':
        ({ findings, recommendations, metrics } = await analyzeArchitecture(files, options.depth));
        break;
    }

    // Calculate summary
    const totalLines = await countTotalLines(files);
    const analysisTime = Date.now() - startTime;

    return {
      target: options.target,
      focus: options.focus,
      depth: options.depth,
      format: options.format,
      summary: {
        filesAnalyzed: files.length,
        totalLines,
        analysisTime
      },
      findings,
      recommendations,
      metrics
    };

  } catch (error) {
    throw new Error(`Analysis failed: ${error instanceof Error ? error.message : String(error)}`);
  }
}

function discoverFiles(target: string, includePatterns: string[], excludePatterns: string[]): string[] {
  const allFiles: string[] = [];

  function walkDir(dir: string): void {
    try {
      const items = fs.readdirSync(dir);

      for (const item of items) {
        const fullPath = path.join(dir, item);
        const stat = fs.statSync(fullPath);

        if (stat.isDirectory()) {
          // Check if directory should be excluded
          const relativePath = path.relative(target, fullPath);
          const shouldExclude = excludePatterns.some(pattern => {
            if (pattern.includes('**')) {
              // Simple globstar handling
              return relativePath.startsWith(pattern.replace('/**', '').replace('\\**', ''));
            }
            return relativePath.includes(pattern.replace('/**', '').replace('\\**', ''));
          });

          if (!shouldExclude) {
            walkDir(fullPath);
          }
        } else if (stat.isFile()) {
          // Check if file matches include patterns
          const fileName = path.basename(fullPath);
          const shouldInclude = includePatterns.some(pattern => {
            // Simple glob matching
            if (pattern === '*.py' && fileName.endsWith('.py')) return true;
            if (pattern === '*.js' && fileName.endsWith('.js')) return true;
            if (pattern === '*.ts' && fileName.endsWith('.ts')) return true;
            if (pattern === '*.java' && fileName.endsWith('.java')) return true;
            if (pattern === '*.go' && fileName.endsWith('.go')) return true;
            if (pattern === '*.rs' && fileName.endsWith('.rs')) return true;
            return false;
          });

          if (shouldInclude) {
            allFiles.push(fullPath);
          }
        }
      }
    } catch (error) {
      // Skip directories that can't be read
    }
  }

  walkDir(target);
  return allFiles;
}

async function countTotalLines(files: string[]): Promise<number> {
  let totalLines = 0;

  for (const file of files) {
    try {
      const content = fs.readFileSync(file, 'utf-8');
      totalLines += content.split('\n').length;
    } catch {
      // Skip files that can't be read
    }
  }

  return totalLines;
}

async function analyzeQuality(files: string[], depth: string): Promise<{
  findings: Finding[];
  recommendations: Recommendation[];
  metrics: Record<string, any>;
}> {
  const findings: Finding[] = [];
  const metrics: Record<string, any> = {
    totalFiles: files.length,
    averageComplexity: 0,
    codeSmells: 0,
    maintainabilityIndex: 85
  };

  for (const file of files) {
    try {
      const content = fs.readFileSync(file, 'utf-8');
      const lines = content.split('\n');

      // Quick analysis for code quality issues
      const fileFindings = analyzeFileQuality(file, content, lines, depth);
      findings.push(...fileFindings);

      // Update metrics
      metrics.codeSmells += fileFindings.length;

    } catch (error) {
      findings.push({
        severity: 'low',
        category: 'quality',
        message: `Could not analyze file: ${path.basename(file)}`,
        file: path.relative(process.cwd(), file),
        recommendation: 'Ensure file is readable and properly encoded'
      });
    }
  }

  // Calculate average complexity (simplified)
  metrics.averageComplexity = metrics.codeSmells / Math.max(files.length, 1);

  const recommendations: Recommendation[] = [
    {
      description: 'Implement consistent code formatting and linting rules',
      priority: 'high',
      estimatedEffort: '2-4 hours',
      benefits: 'Improved code readability and reduced review time',
      category: 'quality'
    },
    {
      description: 'Add comprehensive unit test coverage (>80%)',
      priority: 'high',
      estimatedEffort: '1-2 weeks',
      benefits: 'Increased code reliability and reduced regression bugs',
      category: 'quality'
    },
    {
      description: 'Refactor functions with high cyclomatic complexity',
      priority: 'medium',
      estimatedEffort: '3-5 days',
      benefits: 'Improved maintainability and reduced bug likelihood',
      category: 'quality'
    }
  ];

  return { findings, recommendations, metrics };
}

function analyzeFileQuality(file: string, content: string, lines: string[], depth: string): Finding[] {
  const findings: Finding[] = [];
  const filePath = path.relative(process.cwd(), file);
  const ext = path.extname(file).toLowerCase();

  // Check for long functions (basic complexity check)
  let currentFunctionLines = 0;
  let inFunction = false;
  let functionStart = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    // Language-specific function detection
    if (ext === '.py' && (line.startsWith('def ') || line.startsWith('async def '))) {
      if (inFunction && currentFunctionLines > 50) {
        findings.push({
          severity: 'medium',
          category: 'quality',
          message: 'Function exceeds 50 lines - consider refactoring',
          file: filePath,
          line: functionStart + 1,
          recommendation: 'Break down into smaller, focused functions'
        });
      }
      inFunction = true;
      currentFunctionLines = 0;
      functionStart = i;
    } else if (ext === '.js' || ext === '.ts') {
      if (line.includes('function ') || line.includes('=>') || line.match(/\bconst\s+\w+\s*=/)) {
        if (inFunction && currentFunctionLines > 30) {
          findings.push({
            severity: 'medium',
            category: 'quality',
            message: 'Function exceeds 30 lines - consider refactoring',
            file: filePath,
            line: functionStart + 1,
            recommendation: 'Break down into smaller, focused functions'
          });
        }
        inFunction = true;
        currentFunctionLines = 0;
        functionStart = i;
      }
    }

    if (inFunction) {
      currentFunctionLines++;

      // Check for nested complexity
      if (depth === 'deep') {
        const indentLevel = line.length - line.trimStart().length;
        if (indentLevel > 12) { // Roughly 3 levels of nesting
          findings.push({
            severity: 'low',
            category: 'quality',
            message: 'Deep nesting detected - consider simplifying logic',
            file: filePath,
            line: i + 1,
            recommendation: 'Extract nested logic into separate functions'
          });
        }
      }
    }

    // Check for TODO comments
    if (line.toLowerCase().includes('todo') || line.toLowerCase().includes('fixme')) {
      findings.push({
        severity: 'info',
        category: 'quality',
        message: 'TODO/FIXME comment found',
        file: filePath,
        line: i + 1,
        recommendation: 'Address the TODO item or create a proper issue'
      });
    }

    // Check for console.log statements in production code
    if (depth === 'deep' && (line.includes('console.log') || line.includes('print('))) {
      findings.push({
        severity: 'low',
        category: 'quality',
        message: 'Debug logging statement found in code',
        file: filePath,
        line: i + 1,
        recommendation: 'Remove debug statements or use proper logging'
      });
    }
  }

  return findings;
}

async function analyzeSecurity(files: string[], depth: string): Promise<{
  findings: Finding[];
  recommendations: Recommendation[];
  metrics: Record<string, any>;
}> {
  const findings: Finding[] = [];
  const metrics: Record<string, any> = {
    totalFiles: files.length,
    vulnerabilitiesFound: 0,
    securityScore: 85,
    riskLevel: 'low'
  };

  for (const file of files) {
    try {
      const content = fs.readFileSync(file, 'utf-8');
      const fileFindings = analyzeFileSecurity(file, content, depth);
      findings.push(...fileFindings);
      metrics.vulnerabilitiesFound += fileFindings.length;
    } catch (error) {
      // Skip files that can't be read
    }
  }

  // Adjust security score based on findings
  const highSeverityCount = findings.filter(f => f.severity === 'high' || f.severity === 'critical').length;
  if (highSeverityCount > 0) {
    metrics.securityScore -= highSeverityCount * 10;
    metrics.riskLevel = highSeverityCount > 5 ? 'high' : 'medium';
  }

  const recommendations: Recommendation[] = [
    {
      description: 'Implement input validation and sanitization for all user inputs',
      priority: 'high',
      estimatedEffort: '1-2 days',
      benefits: 'Protection against injection attacks and malformed data',
      category: 'security'
    },
    {
      description: 'Add authentication and authorization checks',
      priority: 'high',
      estimatedEffort: '3-5 days',
      benefits: 'Prevents unauthorized access to sensitive operations',
      category: 'security'
    },
    {
      description: 'Implement proper error handling without information leakage',
      priority: 'medium',
      estimatedEffort: '1-2 days',
      benefits: 'Prevents information disclosure to attackers',
      category: 'security'
    },
    {
      description: 'Regular security dependency updates and vulnerability scanning',
      priority: 'medium',
      estimatedEffort: 'Ongoing',
      benefits: 'Protection against known vulnerabilities in dependencies',
      category: 'security'
    }
  ];

  return { findings, recommendations, metrics };
}

function analyzeFileSecurity(file: string, content: string, depth: string): Finding[] {
  const findings: Finding[] = [];
  const filePath = path.relative(process.cwd(), file);
  const lines = content.split('\n');

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Check for common security issues
    if (depth === 'deep') {
      // SQL injection patterns
      if (line.includes('SELECT') || line.includes('INSERT') || line.includes('UPDATE')) {
        if (line.includes('+') || line.includes('format(') || line.includes('f"')) {
          findings.push({
            severity: 'high',
            category: 'security',
            message: 'Potential SQL injection vulnerability',
            file: filePath,
            line: i + 1,
            code: line.trim(),
            recommendation: 'Use parameterized queries or prepared statements'
          });
        }
      }

      // Hardcoded secrets
      if (line.match(/password|secret|key|token/i) &&
          (line.includes('"') || line.includes("'")) &&
          !line.includes('process.env') && !line.includes('os.getenv')) {
        findings.push({
          severity: 'high',
          category: 'security',
          message: 'Potential hardcoded secret detected',
          file: filePath,
          line: i + 1,
          recommendation: 'Use environment variables or secure credential storage'
        });
      }

      // XSS vulnerabilities in web code
      if ((file.endsWith('.js') || file.endsWith('.ts') || file.endsWith('.jsx') || file.endsWith('.tsx')) &&
          line.includes('innerHTML') || line.includes('outerHTML')) {
        findings.push({
          severity: 'medium',
          category: 'security',
          message: 'Potential XSS vulnerability with direct HTML injection',
          file: filePath,
          line: i + 1,
          code: line.trim(),
          recommendation: 'Use textContent or sanitize HTML input'
        });
      }

      // Path traversal
      if (line.includes('../') || line.includes('..\\')) {
        findings.push({
          severity: 'medium',
          category: 'security',
          message: 'Potential path traversal vulnerability',
          file: filePath,
          line: i + 1,
          code: line.trim(),
          recommendation: 'Validate and sanitize file paths'
        });
      }
    }

    // Check for eval usage
    if (line.includes('eval(')) {
      findings.push({
        severity: 'high',
        category: 'security',
        message: 'Use of eval() function detected',
        file: filePath,
        line: i + 1,
        code: line.trim(),
        recommendation: 'Avoid eval() - use safer alternatives'
      });
    }
  }

  return findings;
}

async function analyzePerformance(files: string[], depth: string): Promise<{
  findings: Finding[];
  recommendations: Recommendation[];
  metrics: Record<string, any>;
}> {
  const findings: Finding[] = [];
  const metrics: Record<string, any> = {
    totalFiles: files.length,
    performanceIssues: 0,
    estimatedOptimizationPotential: 0
  };

  for (const file of files) {
    try {
      const content = fs.readFileSync(file, 'utf-8');
      const fileFindings = analyzeFilePerformance(file, content, depth);
      findings.push(...fileFindings);
      metrics.performanceIssues += fileFindings.length;
    } catch (error) {
      // Skip files that can't be read
    }
  }

  const recommendations: Recommendation[] = [
    {
      description: 'Implement caching for frequently accessed data',
      priority: 'high',
      estimatedEffort: '2-3 days',
      benefits: 'Significant performance improvement for repeated operations',
      category: 'performance'
    },
    {
      description: 'Optimize database queries and add proper indexing',
      priority: 'high',
      estimatedEffort: '3-5 days',
      benefits: 'Faster data retrieval and reduced database load',
      category: 'performance'
    },
    {
      description: 'Implement lazy loading for large datasets',
      priority: 'medium',
      estimatedEffort: '1-2 days',
      benefits: 'Reduced memory usage and faster initial load times',
      category: 'performance'
    },
    {
      description: 'Add performance monitoring and profiling',
      priority: 'medium',
      estimatedEffort: '1-2 days',
      benefits: 'Ability to identify and resolve performance bottlenecks',
      category: 'performance'
    }
  ];

  return { findings, recommendations, metrics };
}

function analyzeFilePerformance(file: string, content: string, depth: string): Finding[] {
  const findings: Finding[] = [];
  const filePath = path.relative(process.cwd(), file);
  const lines = content.split('\n');

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (depth === 'deep') {
      // Check for inefficient loops
      if (line.includes('for') && line.includes('length') && line.includes('.length')) {
        if (lines[i + 1] && lines[i + 1].includes('.length')) {
          findings.push({
            severity: 'medium',
            category: 'performance',
            message: 'Potential inefficient loop - accessing length property repeatedly',
            file: filePath,
            line: i + 1,
            code: line.trim(),
            recommendation: 'Cache array length outside the loop'
          });
        }
      }

      // Check for synchronous file operations
      if (line.includes('readFileSync') || line.includes('writeFileSync')) {
        findings.push({
          severity: 'medium',
          category: 'performance',
          message: 'Synchronous file operation detected',
          file: filePath,
          line: i + 1,
          code: line.trim(),
          recommendation: 'Use asynchronous file operations to avoid blocking'
        });
      }

      // Check for large object creation in loops
      if (line.includes('new ') && lines[i - 1] && lines[i - 1].includes('for ')) {
        findings.push({
          severity: 'low',
          category: 'performance',
          message: 'Object creation inside loop detected',
          file: filePath,
          line: i + 1,
          code: line.trim(),
          recommendation: 'Consider moving object creation outside the loop'
        });
      }
    }

    // Check for nested loops (basic detection)
    if (line.includes('for ') && lines[i + 1] && lines[i + 1].includes('for ')) {
      findings.push({
        severity: 'low',
        category: 'performance',
        message: 'Nested loops detected - potential O(n²) complexity',
        file: filePath,
        line: i + 1,
        recommendation: 'Review algorithm complexity and consider optimization'
      });
    }
  }

  return findings;
}

async function analyzeArchitecture(files: string[], depth: string): Promise<{
  findings: Finding[];
  recommendations: Recommendation[];
  metrics: Record<string, any>;
}> {
  const findings: Finding[] = [];
  const metrics: Record<string, any> = {
    totalFiles: files.length,
    circularDependencies: 0,
    tightCoupling: 0,
    architectureScore: 80
  };

  // Analyze file structure and imports
  const fileMap = new Map<string, string[]>();
  const importMap = new Map<string, string[]>();

  for (const file of files) {
    try {
      const content = fs.readFileSync(file, 'utf-8');
      const imports = extractImports(file, content);
      importMap.set(file, imports);

      // Build reverse map for dependency analysis
      for (const imp of imports) {
        if (!fileMap.has(imp)) {
          fileMap.set(imp, []);
        }
        fileMap.get(imp)!.push(file);
      }
    } catch (error) {
      // Skip files that can't be read
    }
  }

  // Check for architectural issues
  for (const [file, imports] of importMap.entries()) {
    const filePath = path.relative(process.cwd(), file);

    // Check for circular dependencies (simplified)
    for (const imp of imports) {
      const importedBy = fileMap.get(imp) || [];
      if (importedBy.some(f => {
        const fImports = importMap.get(f) || [];
        return fImports.includes(file);
      })) {
        findings.push({
          severity: 'medium',
          category: 'architecture',
          message: 'Potential circular dependency detected',
          file: filePath,
          recommendation: 'Refactor to break circular dependencies using dependency injection'
        });
        metrics.circularDependencies++;
      }
    }

    // Check for tight coupling (too many imports)
    if (depth === 'deep' && imports.length > 20) {
      findings.push({
        severity: 'low',
        category: 'architecture',
        message: 'High number of imports - potential tight coupling',
        file: filePath,
        recommendation: 'Consider breaking down into smaller, focused modules'
      });
      metrics.tightCoupling++;
    }
  }

  const recommendations: Recommendation[] = [
    {
      description: 'Implement clean architecture with clear separation of concerns',
      priority: 'high',
      estimatedEffort: '1-2 weeks',
      benefits: 'Improved maintainability and testability',
      category: 'architecture'
    },
    {
      description: 'Define clear module boundaries and interfaces',
      priority: 'high',
      estimatedEffort: '3-5 days',
      benefits: 'Reduced coupling and improved modularity',
      category: 'architecture'
    },
    {
      description: 'Implement dependency injection pattern',
      priority: 'medium',
      estimatedEffort: '1 week',
      benefits: 'Better testability and flexibility',
      category: 'architecture'
    },
    {
      description: 'Add comprehensive API documentation and contracts',
      priority: 'medium',
      estimatedEffort: '3-5 days',
      benefits: 'Improved developer experience and API stability',
      category: 'architecture'
    }
  ];

  return { findings, recommendations, metrics };
}

function extractImports(file: string, content: string): string[] {
  const imports: string[] = [];
  const lines = content.split('\n');
  const ext = path.extname(file).toLowerCase();

  for (const line of lines) {
    const trimmed = line.trim();

    if (ext === '.py') {
      // Python imports
      if (trimmed.startsWith('import ') || trimmed.startsWith('from ')) {
        // Extract module names (simplified)
        const parts = trimmed.split(' ');
        if (parts.length >= 2) {
          imports.push(parts[1].split('.')[0]);
        }
      }
    } else if (ext === '.js' || ext === '.ts') {
      // JavaScript/TypeScript imports
      if (trimmed.startsWith('import ') || trimmed.startsWith('require(')) {
        // Extract module names (simplified)
        if (trimmed.includes('from ')) {
          const fromMatch = trimmed.match(/from ['"]([^'"]+)['"]/);
          if (fromMatch) {
            imports.push(fromMatch[1]);
          }
        } else if (trimmed.includes('require(')) {
          const requireMatch = trimmed.match(/require\(['"]([^'"]+)['"]\)/);
          if (requireMatch) {
            imports.push(requireMatch[1]);
          }
        }
      }
    }
  }

  return [...new Set(imports)]; // Remove duplicates
}
