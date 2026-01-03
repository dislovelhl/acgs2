import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import { performAnalysis } from '../services/analysisService';

// Type definitions for analysis results
import { getLogger } from '../../../../../sdk/typescript/src/utils/logger';
const logger = getLogger('analyze');


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
        logger.info(chalk.yellow(`\n📋 Valid focuses: ${validFocuses.join(', ')}`);
        logger.info(chalk.gray(`\n💡 Choose based on your analysis needs:`);
        logger.info(chalk.gray(`   • quality: Code maintainability and best practices`);
        logger.info(chalk.gray(`   • security: Vulnerability and security issues`);
        logger.info(chalk.gray(`   • performance: Performance bottlenecks and optimizations`);
        logger.info(chalk.gray(`   • architecture: Design patterns and structural issues`);
        console.log(chalk.gray(`   • quality: Code maintainability and best practices`));
        console.log(chalk.gray(`   • security: Vulnerability and security issues`));
        console.log(chalk.gray(`   • performance: Performance bottlenecks and optimizations`));
        console.log(chalk.gray(`   • architecture: Design patterns and structural issues`));
        process.exit(1);
      }

        logger.info(chalk.yellow(`\n📋 Valid depths: ${validDepths.join(', ')}`);
      const validDepths = ['quick', 'deep'];
      if (!validDepths.includes(options.depth)) {
        spinner.fail(chalk.red(`❌ Invalid depth: ${options.depth}`));
        console.log(chalk.yellow(`\n📋 Valid depths: ${validDepths.join(', ')}`));
        process.exit(1);
      }

        logger.info(chalk.yellow(`\n📋 Valid formats: ${validFormats.join(', ')}`);
      const validFormats = ['text', 'json', 'report'];
      if (!validFormats.includes(options.format)) {
        spinner.fail(chalk.red(`❌ Invalid format: ${options.format}`));
        console.log(chalk.yellow(`\n📋 Valid formats: ${validFormats.join(', ')}`));
        process.exit(1);
      }

      // Parse patterns
      const includePatterns = options.includePatterns.split(',').map((p: string) => p.trim());
      const excludePatterns = options.excludePatterns.split(',').map((p: string) => p.trim());

      spinner.text = `Analyzing ${target} with ${options.focus} focus (${options.depth} depth)...`;

      // Perform the analysis
      const result = await performAnalysis({
        target,
        focus: options.focus,
        depth: options.depth,
        format: options.format,
        includePatterns,
        excludePatterns
      });

        logger.info(JSON.stringify(result, null, 2);

      // Display results based on format
      if (options.format === 'json') {
        console.log(JSON.stringify(result, null, 2));
      } else if (options.format === 'report') {
        displayReportFormat(result);
      } else {
        displayTextFormat(result);
      }

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      spinner.fail(chalk.red(`❌ Analysis failed: ${errorMessage}`));
      process.exit(1);
  logger.info(chalk.blue(`\n📊 Analysis Results - ${result.focus.toUpperCase()} Focus`);
  logger.info(chalk.gray(`Target: ${result.target}`);
  logger.info(chalk.gray(`Files analyzed: ${result.summary.filesAnalyzed}`);
  logger.info(chalk.gray(`Analysis depth: ${result.depth}`);
  logger.info(chalk.gray(`Generated: ${new Date().toISOString()}`);
  console.log(chalk.gray(`Target: ${result.target}`));
  console.log(chalk.gray(`Files analyzed: ${result.summary.filesAnalyzed}`));
    logger.info(chalk.yellow(`\n⚠️  Findings (${result.findings.length}):`);
  console.log(chalk.gray(`Generated: ${new Date().toISOString()}`));

  if (result.findings && result.findings.length > 0) {
    console.log(chalk.yellow(`\n⚠️  Findings (${result.findings.length}):`));

    // Group by severity
    const bySeverity = result.findings.reduce<Record<SeverityLevel, AnalysisFinding[]>>(
      (acc, finding) => {
        acc[finding.severity] = acc[finding.severity] || [];
        acc[finding.severity].push(finding);
        return acc;
      },
      { critical: [], high: [], medium: [], low: [], info: [] }
    );

        logger.info(severityColorFn(`\n${severity.toUpperCase()} (${bySeverity[severity].length}):`);
    severityLevels.forEach(severity => {
      if (bySeverity[severity] && bySeverity[severity].length > 0) {
          logger.info(chalk.gray(`  • ${finding.message}`);
        console.log(severityColorFn(`\n${severity.toUpperCase()} (${bySeverity[severity].length}):`));
            logger.info(chalk.gray(`    📁 ${finding.file}${finding.line ? `:${finding.line}` : ''}`);
        bySeverity[severity].forEach((finding) => {
          console.log(chalk.gray(`  • ${finding.message}`));
            logger.info(chalk.gray(`    💡 ${finding.recommendation}`);
            console.log(chalk.gray(`    📁 ${finding.file}${finding.line ? `:${finding.line}` : ''}`));
          }
          if (finding.recommendation) {
            console.log(chalk.gray(`    💡 ${finding.recommendation}`));
          }
        });
      }
    logger.info(chalk.green(`\n🚀 Recommendations:`);
  }
      logger.info(chalk.gray(`  ${index + 1}. ${rec.description}`);
  if (result.recommendations && result.recommendations.length > 0) {
        logger.info(chalk.gray(`     Priority: ${rec.priority}`);
    result.recommendations.forEach((rec, index) => {
      console.log(chalk.gray(`  ${index + 1}. ${rec.description}`));
        logger.info(chalk.gray(`     Effort: ${rec.estimatedEffort}`);
        console.log(chalk.gray(`     Priority: ${rec.priority}`));
      }
      if (rec.estimatedEffort) {
        console.log(chalk.gray(`     Effort: ${rec.estimatedEffort}`));
      }
    logger.info(chalk.blue(`\n📈 Metrics:`);
  }
      logger.info(chalk.gray(`  • ${key}: ${value}`);
  if (result.metrics) {
    console.log(chalk.blue(`\n📈 Metrics:`));
    Object.entries(result.metrics).forEach(([key, value]) => {
      console.log(chalk.gray(`  • ${key}: ${value}`));
    });
  logger.info(chalk.blue(`\n📋 Analysis Report - ${result.focus.toUpperCase()} Focus`);
  logger.info('='.repeat(60);

  logger.info(chalk.bold('\nEXECUTIVE SUMMARY');
  logger.info(`Analysis performed on: ${result.target}`;
  logger.info(`Focus area: ${result.focus}`;
  logger.info(`Analysis depth: ${result.depth}`;
  logger.info(`Files analyzed: ${result.summary.filesAnalyzed}`;
  logger.info(`Total findings: ${result.findings?.length || 0}`;
  logger.info(`Generated: ${new Date().toISOString()}`;
  console.log(`Analysis depth: ${result.depth}`);
  console.log(`Files analyzed: ${result.summary.filesAnalyzed}`);
    logger.info(chalk.bold('\nFINDINGS BY SEVERITY');
  console.log(`Generated: ${new Date().toISOString()}`);

  if (result.findings && result.findings.length > 0) {
    console.log(chalk.bold('\nFINDINGS BY SEVERITY'));

    const severityStats = result.findings.reduce<Record<string, number>>(
      (acc, finding) => {
        acc[finding.severity] = (acc[finding.severity] || 0) + 1;
        return acc;
      },
      {}
      logger.info(colorFn(`• ${severity.toUpperCase()}: ${count}`);

    Object.entries(severityStats).forEach(([severity, count]) => {
    logger.info(chalk.bold('\nDETAILED FINDINGS');
      console.log(colorFn(`• ${severity.toUpperCase()}: ${count}`));
    });
      logger.info(colorFn(`\n${index + 1}. ${finding.message}`);
      logger.info(`   Severity: ${finding.severity.toUpperCase()}`;
    result.findings.forEach((finding, index) => {
        logger.info(`   Location: ${finding.file}${finding.line ? `:${finding.line}` : ''}`;
      console.log(colorFn(`\n${index + 1}. ${finding.message}`));
      console.log(`   Severity: ${finding.severity.toUpperCase()}`);
        logger.info(`   Category: ${finding.category}`;
        console.log(`   Location: ${finding.file}${finding.line ? `:${finding.line}` : ''}`);
      }
        logger.info(`   Recommendation: ${finding.recommendation}`;
        console.log(`   Category: ${finding.category}`);
      }
      if (finding.recommendation) {
        console.log(`   Recommendation: ${finding.recommendation}`);
      }
    logger.info(chalk.bold('\nRECOMMENDATIONS');
  }
      logger.info(`\n${index + 1}. ${rec.description}`;
      logger.info(`   Priority: ${rec.priority || 'Medium'}`;
      logger.info(`   Estimated Effort: ${rec.estimatedEffort || 'Unknown'}`;
    result.recommendations.forEach((rec, index) => {
        logger.info(`   Benefits: ${rec.benefits}`;
      console.log(`   Priority: ${rec.priority || 'Medium'}`);
      console.log(`   Estimated Effort: ${rec.estimatedEffort || 'Unknown'}`);
      if (rec.benefits) {
        console.log(`   Benefits: ${rec.benefits}`);
      }
    logger.info(chalk.bold('\nMETRICS');
  }
      logger.info(`• ${key}: ${value}`;
  if (result.metrics) {
    console.log(chalk.bold('\nMETRICS'));
    Object.entries(result.metrics).forEach(([key, value]) => {
  logger.info('\n' + '='.repeat(60);
  logger.info(chalk.green('Report generated successfully');
  }

  console.log('\n' + '='.repeat(60));
  console.log(chalk.green('Report generated successfully'));
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
