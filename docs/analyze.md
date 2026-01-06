--- Cursor Command: analyze.md ---
# analyze

Code analysis and quality assessment for ACGS-2 projects.

## Usage
```bash
npx claude-flow analyze [target] [options]
```

## Arguments
- `target` - Target directory or file to analyze (default: current directory)

## Options
- `-f, --focus <type>` - Analysis focus: quality, security, performance, architecture (default: quality)
- `-d, --depth <level>` - Analysis depth: quick, deep (default: quick)
- `--format <format>` - Output format: text, json, report (default: text)
- `--include-patterns <patterns>` - File patterns to include (comma-separated)
- `--exclude-patterns <patterns>` - File patterns to exclude (comma-separated)

## MCP Tool Usage in Claude Code

**Tool:** `mcp__claude-flow__analyze`

## Parameters
```json
{
  "target": "./src",
  "focus": "security",
  "depth": "deep",
  "format": "json",
  "includePatterns": "*.py,*.js,*.ts",
  "excludePatterns": "node_modules/**,test/**"
}
```

## Description
Perform comprehensive code analysis and quality assessment across ACGS-2 projects, identifying issues, vulnerabilities, and improvement opportunities with actionable recommendations.

## Analysis Focus Areas

### Quality Focus
**Target:** Code maintainability and best practices
**Analyzes:**
- Code complexity and readability
- Naming conventions and consistency
- Documentation completeness
- Code duplication and refactoring opportunities
- Design pattern adherence

### Security Focus
**Target:** Vulnerability assessment and security issues
**Analyzes:**
- Common security vulnerabilities (XSS, SQL injection, etc.)
- Authentication and authorization flaws
- Data validation and sanitization
- Secure coding practices
- Dependency vulnerabilities

### Performance Focus
**Target:** Performance bottlenecks and optimization opportunities
**Analyzes:**
- Algorithm complexity and efficiency
- Memory usage and leaks
- Database query optimization
- Caching strategies
- Resource utilization patterns

### Architecture Focus
**Target:** System design and structural issues
**Analyzes:**
- Architectural pattern compliance
- Dependency management and coupling
- Component separation and modularity
- Scalability considerations
- Design consistency and patterns

## Analysis Depths

### Quick Analysis
**Duration:** 30 seconds - 2 minutes
**Coverage:** Surface-level issues and obvious problems
**Best For:** Fast feedback, CI/CD pipelines, routine checks

### Deep Analysis
**Duration:** 5-15 minutes
**Coverage:** Comprehensive analysis with detailed inspection
**Best For:** Code reviews, architecture assessment, thorough audits

## Output Formats

### Text Format (Default)
Human-readable output with color coding and structured display:
```
🔍 Code Analysis Report
Target: ./src
Focus: quality
Depth: quick
Files Analyzed: 45

📊 Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Critical: 2   High: 5   Medium: 12   Low: 8   Info: 15

🚨 Critical Issues
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Security vulnerability in authentication module
   File: src/auth.py:45
   Category: Security
   Recommendation: Implement proper input validation

2. Memory leak in data processing pipeline
   File: src/processor.py:123
   Category: Performance
   Recommendation: Use context managers for resource cleanup

🔧 Recommendations
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Implement comprehensive error handling
   Priority: High
   Effort: Medium (2-3 days)
   Benefits: Improved system reliability

2. Add input validation for API endpoints
   Priority: Critical
   Effort: Low (4-6 hours)
   Benefits: Enhanced security posture
```

### JSON Format
Structured data for programmatic processing:
```json
{
  "target": "./src",
  "focus": "quality",
  "depth": "quick",
  "timestamp": "2024-01-04T16:00:00Z",
  "summary": {
    "filesAnalyzed": 45,
    "findings": {
      "critical": 2,
      "high": 5,
      "medium": 12,
      "low": 8,
      "info": 15
    }
  },
  "findings": [
    {
      "severity": "critical",
      "message": "Security vulnerability in authentication module",
      "file": "src/auth.py",
      "line": 45,
      "category": "Security",
      "recommendation": "Implement proper input validation"
    }
  ],
  "recommendations": [
    {
      "description": "Implement comprehensive error handling",
      "priority": "High",
      "estimatedEffort": "Medium (2-3 days)",
      "benefits": "Improved system reliability"
    }
  ]
}
```

### Report Format
Detailed HTML/PDF-style report with charts and visualizations.

## File Pattern Controls

### Include Patterns (Default)
```
*.py,*.js,*.ts,*.java,*.go,*.rs,*.cpp,*.c,*.php,*.rb
```

### Exclude Patterns (Default)
```
node_modules/**,*.pyc,__pycache__/**,.git/**,build/**,dist/**,
*.log,*.tmp,.DS_Store/**,coverage/**,.pytest_cache/**
```

### Custom Patterns
```bash
# Analyze only Python files
npx claude-flow analyze --include-patterns "*.py"

# Exclude test files
npx claude-flow analyze --exclude-patterns "**/test/**,**/*test.py"

# Frontend analysis only
npx claude-flow analyze --include-patterns "*.js,*.ts,*.jsx,*.tsx" --exclude-patterns "node_modules/**"
```

## Examples

### Basic quality analysis
```bash
npx claude-flow analyze
```

### Security audit
```bash
npx claude-flow analyze --focus security --depth deep
```

### Performance analysis of specific directory
```bash
npx claude-flow analyze ./src --focus performance
```

### Architecture review with JSON output
```bash
npx claude-flow analyze --focus architecture --format json
```

### Quick scan for CI/CD
```bash
npx claude-flow analyze --depth quick --format json > analysis_results.json
```

### Custom file patterns
```bash
npx claude-flow analyze --include-patterns "*.py" --exclude-patterns "**/migrations/**"
```

### In Claude Code
```javascript
mcp__claude-flow__analyze({
  target: "./backend",
  focus: "security",
  depth: "deep",
  format: "json"
})
```

## Severity Levels

### Critical (🚨)
- Security vulnerabilities with exploitation potential
- Data corruption or loss risks
- System stability threats
- Compliance violations

### High (⚠️)
- Significant performance degradation
- Security weaknesses
- Major maintainability issues
- Reliability concerns

### Medium (📋)
- Moderate performance issues
- Code quality problems
- Minor security concerns
- Design improvements

### Low (📝)
- Code style violations
- Minor inefficiencies
- Documentation gaps
- Best practice deviations

### Info (ℹ️)
- Suggestions for improvement
- Code metrics information
- General observations
- Optimization opportunities

## Integration Workflows

### Development Workflow
```bash
# Quick analysis during development
npx claude-flow analyze --depth quick

# Detailed analysis before commits
npx claude-flow analyze --depth deep --focus quality

# Security check before deployment
npx claude-flow analyze --focus security --depth deep
```

### CI/CD Integration
```bash
# Quality gate in CI pipeline
npx claude-flow analyze --format json --depth quick > analysis.json

# Check for critical issues
cat analysis.json | jq '.summary.findings.critical'

# Fail build on critical issues
if [ $(cat analysis.json | jq '.summary.findings.critical') -gt 0 ]; then
  echo "Critical issues found, failing build"
  exit 1
fi
```

### Code Review Integration
```bash
# Analyze changed files
git diff --name-only | xargs npx claude-flow analyze --focus quality

# Pre-commit analysis
npx claude-flow analyze --depth quick --format text
```

## Performance Considerations

### Analysis Speed
- **Quick Analysis:** 100-500 files/minute
- **Deep Analysis:** 20-50 files/minute
- **Security Focus:** Additional 2-5 minutes for vulnerability scanning

### Resource Usage
- **Memory:** 256MB - 1GB depending on codebase size
- **CPU:** 1-2 cores during analysis
- **Disk I/O:** Read-only access to source files

### Scaling Guidelines
- **Small Projects (< 100 files):** Quick analysis recommended
- **Medium Projects (100-1000 files):** Quick for routine, deep for reviews
- **Large Projects (> 1000 files):** Targeted analysis with specific patterns

## Best Practices

### Regular Analysis
- Run quick analysis daily during development
- Perform deep analysis before major releases
- Include security focus in deployment pipelines
- Review analysis trends over time

### Issue Prioritization
- Address critical and high severity issues immediately
- Plan medium issues for next sprint
- Consider low/info items for technical debt cleanup
- Track issue resolution progress

### Tool Integration
- Integrate with code editors and IDEs
- Set up automated analysis in CI/CD
- Configure alerts for critical findings
- Generate reports for stakeholder review

### Continuous Improvement
- Review false positives and adjust patterns
- Update analysis rules based on project evolution
- Train team on common issue patterns
- Establish quality baselines and targets

## Troubleshooting

### Common Issues

#### Analysis Not Starting
```
Symptom: Command hangs or fails immediately
Check: ACGS-2 core running, target path exists
Action: Verify installation, check file permissions
```

#### No Files Analyzed
```
Symptom: "0 files analyzed" result
Check: Include/exclude patterns, file permissions
Action: Adjust patterns, verify file access
```

#### Slow Analysis
```
Symptom: Analysis takes unusually long
Check: Depth setting, file count, system resources
Action: Use quick depth, reduce scope, check resources
```

#### Incomplete Results
```
Symptom: Analysis exits early with partial results
Check: Memory limits, file parsing errors
Action: Increase memory, check file encodings
```

## Configuration

### Analysis Configuration File
```json
{
  "analysis": {
    "defaultFocus": "quality",
    "defaultDepth": "quick",
    "customRules": {
      "maxComplexity": 15,
      "maxFileSize": "1MB",
      "requiredCoverage": 80
    },
    "integrations": {
      "sonarQube": {
        "enabled": true,
        "url": "https://sonar.example.com"
      },
      "eslint": {
        "config": ".eslintrc.json"
      }
    }
  }
}
```

## See Also

- `coordination list` - View analysis-related coordination tasks
- `coordination execute` - Execute analysis coordination tasks
- `task orchestrate` - Coordinate complex analysis workflows
- `swarm monitor` - Monitor analysis task execution

--- End Command ---
