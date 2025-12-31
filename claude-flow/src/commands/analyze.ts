import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import { performAnalysis } from '../services/analysisService';

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
        console.log(chalk.yellow(`\n📋 Valid focuses: ${validFocuses.join(', ')}`));
        console.log(chalk.gray(`\n💡 Choose based on your analysis needs:`));
        console.log(chalk.gray(`   • quality: Code maintainability and best practices`));
        console.log(chalk.gray(`   • security: Vulnerability and security issues`));
        console.log(chalk.gray(`   • performance: Performance bottlenecks and optimizations`));
        console.log(chalk.gray(`   • architecture: Design patterns and structural issues`));
        process.exit(1);
      }

      // Validate depth
      const validDepths = ['quick', 'deep'];
      if (!validDepths.includes(options.depth)) {
        spinner.fail(chalk.red(`❌ Invalid depth: ${options.depth}`));
        console.log(chalk.yellow(`\n📋 Valid depths: ${validDepths.join(', ')}`));
        process.exit(1);
      }

      // Validate format
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

      spinner.succeed(chalk.green(`✅ Analysis completed!`));

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
    }
  });

function displayTextFormat(result: any): void {
  console.log(chalk.blue(`\n📊 Analysis Results - ${result.focus.toUpperCase()} Focus`));
  console.log(chalk.gray(`Target: ${result.target}`));
  console.log(chalk.gray(`Files analyzed: ${result.summary.filesAnalyzed}`));
  console.log(chalk.gray(`Analysis depth: ${result.depth}`));
  console.log(chalk.gray(`Generated: ${new Date().toISOString()}`));

  if (result.findings && result.findings.length > 0) {
    console.log(chalk.yellow(`\n⚠️  Findings (${result.findings.length}):`));

    // Group by severity
    const bySeverity = result.findings.reduce((acc: any, finding: any) => {
      acc[finding.severity] = acc[finding.severity] || [];
      acc[finding.severity].push(finding);
      return acc;
    }, {});

    ['critical', 'high', 'medium', 'low', 'info'].forEach(severity => {
      if (bySeverity[severity] && bySeverity[severity].length > 0) {
        const severityColorFn = getSeverityColor(severity);
        console.log(severityColorFn(`\n${severity.toUpperCase()} (${bySeverity[severity].length}):`));

        bySeverity[severity].forEach((finding: any) => {
          console.log(chalk.gray(`  • ${finding.message}`));
          if (finding.file) {
            console.log(chalk.gray(`    📁 ${finding.file}${finding.line ? `:${finding.line}` : ''}`));
          }
          if (finding.recommendation) {
            console.log(chalk.gray(`    💡 ${finding.recommendation}`));
          }
        });
      }
    });
  }

  if (result.recommendations && result.recommendations.length > 0) {
    console.log(chalk.green(`\n🚀 Recommendations:`));
    result.recommendations.forEach((rec: any, index: number) => {
      console.log(chalk.gray(`  ${index + 1}. ${rec.description}`));
      if (rec.priority) {
        console.log(chalk.gray(`     Priority: ${rec.priority}`));
      }
      if (rec.estimatedEffort) {
        console.log(chalk.gray(`     Effort: ${rec.estimatedEffort}`));
      }
    });
  }

  if (result.metrics) {
    console.log(chalk.blue(`\n📈 Metrics:`));
    Object.entries(result.metrics).forEach(([key, value]) => {
      console.log(chalk.gray(`  • ${key}: ${value}`));
    });
  }
}

function displayReportFormat(result: any): void {
  console.log(chalk.blue(`\n📋 Analysis Report - ${result.focus.toUpperCase()} Focus`));
  console.log('='.repeat(60));

  console.log(chalk.bold('\nEXECUTIVE SUMMARY'));
  console.log(`Analysis performed on: ${result.target}`);
  console.log(`Focus area: ${result.focus}`);
  console.log(`Analysis depth: ${result.depth}`);
  console.log(`Files analyzed: ${result.summary.filesAnalyzed}`);
  console.log(`Total findings: ${result.findings?.length || 0}`);
  console.log(`Generated: ${new Date().toISOString()}`);

  if (result.findings && result.findings.length > 0) {
    console.log(chalk.bold('\nFINDINGS BY SEVERITY'));

    const severityStats = result.findings.reduce((acc: any, finding: any) => {
      acc[finding.severity] = (acc[finding.severity] || 0) + 1;
      return acc;
    }, {});

    Object.entries(severityStats).forEach(([severity, count]) => {
      const colorFn = getSeverityColor(severity);
      console.log(colorFn(`• ${severity.toUpperCase()}: ${count}`));
    });

    console.log(chalk.bold('\nDETAILED FINDINGS'));
    result.findings.forEach((finding: any, index: number) => {
      const colorFn = getSeverityColor(finding.severity);
      console.log(colorFn(`\n${index + 1}. ${finding.message}`));
      console.log(`   Severity: ${finding.severity.toUpperCase()}`);
      if (finding.file) {
        console.log(`   Location: ${finding.file}${finding.line ? `:${finding.line}` : ''}`);
      }
      if (finding.category) {
        console.log(`   Category: ${finding.category}`);
      }
      if (finding.recommendation) {
        console.log(`   Recommendation: ${finding.recommendation}`);
      }
    });
  }

  if (result.recommendations && result.recommendations.length > 0) {
    console.log(chalk.bold('\nRECOMMENDATIONS'));
    result.recommendations.forEach((rec: any, index: number) => {
      console.log(`\n${index + 1}. ${rec.description}`);
      console.log(`   Priority: ${rec.priority || 'Medium'}`);
      console.log(`   Estimated Effort: ${rec.estimatedEffort || 'Unknown'}`);
      if (rec.benefits) {
        console.log(`   Benefits: ${rec.benefits}`);
      }
    });
  }

  if (result.metrics) {
    console.log(chalk.bold('\nMETRICS'));
    Object.entries(result.metrics).forEach(([key, value]) => {
      console.log(`• ${key}: ${value}`);
    });
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
