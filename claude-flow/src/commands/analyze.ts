import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import { performAnalysis } from '../services/analysisService';
import { getLogger, cliOutput } from '../utils/logging_config';

// Initialize logger for this module
const logger = getLogger('commands/analyze');

// Type definitions for analysis results
interface AnalysisFinding {
  message: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  file?: string;
  line?: number;
  category?: string;
  recommendation?: string;
}

interface AnalysisRecommendation {
  description: string;
  priority?: string;
  estimatedEffort?: string;
  benefits?: string;
}

interface AnalysisSummary {
  filesAnalyzed: number;
  totalFindings?: number;
}

interface AnalysisResult {
  focus: string;
  target: string;
  depth: string;
  summary: AnalysisSummary;
  findings?: AnalysisFinding[];
  recommendations?: AnalysisRecommendation[];
  metrics?: Record<string, string | number>;
}

type SeverityLevel = 'critical' | 'high' | 'medium' | 'low' | 'info';

export const analyzeCommand = new Command('analyze')
  .description('Code analysis and quality assessment')
  .argument('[target]', 'Target directory or file to analyze', '.')
  .option('-f, --focus <type>', 'Analysis focus (quality, security, performance, architecture)', 'quality')
  .option('-d, --depth <level>', 'Analysis depth (quick, deep)', 'quick')
  .option('--format <format>', 'Output format (text, json, report)', 'text')
  .option('--include-patterns <patterns>', 'File patterns to include (comma-separated)', '*.py,*.js,*.ts,*.java,*.go,*.rs')
  .option('--exclude-patterns <patterns>', 'File patterns to exclude (comma-separated)', 'node_modules/**,*.pyc,__pycache__/**,.git/**')
  .action(async (target: string, options) => {
    const spinner = ora('Initializing analysis...').start();

    try {
      // Validate focus
      const validFocuses = ['quality', 'security', 'performance', 'architecture'];
      if (!validFocuses.includes(options.focus)) {
        spinner.fail(chalk.red(`❌ Invalid focus: ${options.focus}`));
        logger.warn('invalid_focus', { focus: options.focus, validFocuses });
        cliOutput(chalk.yellow(`\n📋 Valid focuses: ${validFocuses.join(', ')}`));
        cliOutput(chalk.gray(`\n💡 Choose based on your analysis needs:`));
        cliOutput(chalk.gray(`   • quality: Code maintainability and best practices`));
        cliOutput(chalk.gray(`   • security: Vulnerability and security issues`));
        cliOutput(chalk.gray(`   • performance: Performance bottlenecks and optimizations`));
        cliOutput(chalk.gray(`   • architecture: Design patterns and structural issues`));
        process.exit(1);
      }

      // Validate depth
      const validDepths = ['quick', 'deep'];
      if (!validDepths.includes(options.depth)) {
        spinner.fail(chalk.red(`❌ Invalid depth: ${options.depth}`));
        logger.warn('invalid_depth', { depth: options.depth, validDepths });
        cliOutput(chalk.yellow(`\n📋 Valid depths: ${validDepths.join(', ')}`));
        process.exit(1);
      }

      // Validate format
      const validFormats = ['text', 'json', 'report'];
      if (!validFormats.includes(options.format)) {
        spinner.fail(chalk.red(`❌ Invalid format: ${options.format}`));
        logger.warn('invalid_format', { format: options.format, validFormats });
        cliOutput(chalk.yellow(`\n📋 Valid formats: ${validFormats.join(', ')}`));
        process.exit(1);
      }

      // Parse patterns
      const includePatterns = options.includePatterns.split(',').map((p: string) => p.trim());
      const excludePatterns = options.excludePatterns.split(',').map((p: string) => p.trim());

      spinner.text = `Analyzing ${target} with ${options.focus} focus (${options.depth} depth)...`;
      logger.info('analysis_started', { target, focus: options.focus, depth: options.depth });

      // Perform the analysis
      const result = await performAnalysis({
        target,
        focus: options.focus,
        depth: options.depth,
        format: options.format,
        includePatterns,
        excludePatterns
      });

      spinner.succeed(chalk.green(`✅ Analysis completed!`));
      logger.info('analysis_completed', { target, focus: options.focus, findingsCount: result.findings?.length || 0 });

      // Display results based on format
      if (options.format === 'json') {
        cliOutput(JSON.stringify(result, null, 2));
      } else if (options.format === 'report') {
        displayReportFormat(result);
      } else {
        displayTextFormat(result);
      }

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      spinner.fail(chalk.red(`❌ Analysis failed: ${errorMessage}`));
      logger.error('analysis_failed', { error: errorMessage, target });
      process.exit(1);
    }
  });

function displayTextFormat(result: AnalysisResult): void {
  cliOutput(chalk.blue(`\n📊 Analysis Results - ${result.focus.toUpperCase()} Focus`));
  cliOutput(chalk.gray(`Target: ${result.target}`));
  cliOutput(chalk.gray(`Files analyzed: ${result.summary.filesAnalyzed}`));
  cliOutput(chalk.gray(`Analysis depth: ${result.depth}`));
  cliOutput(chalk.gray(`Generated: ${new Date().toISOString()}`));

  if (result.findings && result.findings.length > 0) {
    cliOutput(chalk.yellow(`\n⚠️  Findings (${result.findings.length}):`));

    // Group by severity
    const bySeverity = result.findings.reduce<Record<SeverityLevel, AnalysisFinding[]>>(
      (acc, finding) => {
        acc[finding.severity] = acc[finding.severity] || [];
        acc[finding.severity].push(finding);
        return acc;
      },
      { critical: [], high: [], medium: [], low: [], info: [] }
    );

    const severityLevels: SeverityLevel[] = ['critical', 'high', 'medium', 'low', 'info'];
    severityLevels.forEach(severity => {
      if (bySeverity[severity] && bySeverity[severity].length > 0) {
        const severityColorFn = getSeverityColor(severity);
        cliOutput(severityColorFn(`\n${severity.toUpperCase()} (${bySeverity[severity].length}):`));

        bySeverity[severity].forEach((finding) => {
          cliOutput(chalk.gray(`  • ${finding.message}`));
          if (finding.file) {
            cliOutput(chalk.gray(`    📁 ${finding.file}${finding.line ? `:${finding.line}` : ''}`));
          }
          if (finding.recommendation) {
            cliOutput(chalk.gray(`    💡 ${finding.recommendation}`));
          }
        });
      }
    });
  }

  if (result.recommendations && result.recommendations.length > 0) {
    cliOutput(chalk.green(`\n🚀 Recommendations:`));
    result.recommendations.forEach((rec, index) => {
      cliOutput(chalk.gray(`  ${index + 1}. ${rec.description}`));
      if (rec.priority) {
        cliOutput(chalk.gray(`     Priority: ${rec.priority}`));
      }
      if (rec.estimatedEffort) {
        cliOutput(chalk.gray(`     Effort: ${rec.estimatedEffort}`));
      }
    });
  }

  if (result.metrics) {
    cliOutput(chalk.blue(`\n📈 Metrics:`));
    Object.entries(result.metrics).forEach(([key, value]) => {
      cliOutput(chalk.gray(`  • ${key}: ${value}`));
    });
  }
}

function displayReportFormat(result: AnalysisResult): void {
  cliOutput(chalk.blue(`\n📋 Analysis Report - ${result.focus.toUpperCase()} Focus`));
  cliOutput('='.repeat(60));

  cliOutput(chalk.bold('\nEXECUTIVE SUMMARY'));
  cliOutput(`Analysis performed on: ${result.target}`);
  cliOutput(`Focus area: ${result.focus}`);
  cliOutput(`Analysis depth: ${result.depth}`);
  cliOutput(`Files analyzed: ${result.summary.filesAnalyzed}`);
  cliOutput(`Total findings: ${result.findings?.length || 0}`);
  cliOutput(`Generated: ${new Date().toISOString()}`);

  if (result.findings && result.findings.length > 0) {
    cliOutput(chalk.bold('\nFINDINGS BY SEVERITY'));

    const severityStats = result.findings.reduce<Record<string, number>>(
      (acc, finding) => {
        acc[finding.severity] = (acc[finding.severity] || 0) + 1;
        return acc;
      },
      {}
    );

    Object.entries(severityStats).forEach(([severity, count]) => {
      const colorFn = getSeverityColor(severity);
      cliOutput(colorFn(`• ${severity.toUpperCase()}: ${count}`));
    });

    cliOutput(chalk.bold('\nDETAILED FINDINGS'));
    result.findings.forEach((finding, index) => {
      const colorFn = getSeverityColor(finding.severity);
      cliOutput(colorFn(`\n${index + 1}. ${finding.message}`));
      cliOutput(`   Severity: ${finding.severity.toUpperCase()}`);
      if (finding.file) {
        cliOutput(`   Location: ${finding.file}${finding.line ? `:${finding.line}` : ''}`);
      }
      if (finding.category) {
        cliOutput(`   Category: ${finding.category}`);
      }
      if (finding.recommendation) {
        cliOutput(`   Recommendation: ${finding.recommendation}`);
      }
    });
  }

  if (result.recommendations && result.recommendations.length > 0) {
    cliOutput(chalk.bold('\nRECOMMENDATIONS'));
    result.recommendations.forEach((rec, index) => {
      cliOutput(`\n${index + 1}. ${rec.description}`);
      cliOutput(`   Priority: ${rec.priority || 'Medium'}`);
      cliOutput(`   Estimated Effort: ${rec.estimatedEffort || 'Unknown'}`);
      if (rec.benefits) {
        cliOutput(`   Benefits: ${rec.benefits}`);
      }
    });
  }

  if (result.metrics) {
    cliOutput(chalk.bold('\nMETRICS'));
    Object.entries(result.metrics).forEach(([key, value]) => {
      cliOutput(`• ${key}: ${value}`);
    });
  }

  cliOutput('\n' + '='.repeat(60));
  cliOutput(chalk.green('Report generated successfully'));
}

function getSeverityColor(severity: string): (text: string) => string {
  switch (severity.toLowerCase()) {
    case 'critical': return chalk.red;
    case 'high': return chalk.red;
    case 'medium': return chalk.yellow;
    case 'low': return chalk.blue;
    case 'info': return chalk.gray;
    default: return chalk.gray;
  }
}
