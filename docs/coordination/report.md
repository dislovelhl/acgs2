--- Cursor Command: coordination/report.md ---
# coordination report

Generate a coordination progress report.

## Usage
```bash
npx claude-flow coordination report [options]
```

## Options
- `--format <type>` - Output format: text, json, markdown (default: text)
- `--period <days>` - Report period in days (default: 30)
- `--include-completed` - Include completed tasks in report

## MCP Tool Usage in Claude Code

**Tool:** `mcp__claude-flow__coordination_report`

## Parameters
```json
{
  "format": "markdown",
  "period": 30,
  "includeCompleted": true
}
```

## Description
Generate comprehensive progress reports for coordination tasks over a specified time period. Reports can be generated in multiple formats for different use cases and audiences.

## Output Formats

### Text Format (Default)
Human-readable plain text format for console output and basic documentation.

### JSON Format
Structured data format for programmatic processing and integration with other tools.

### Markdown Format
Rich text format with headers, tables, and formatting for documentation and reporting.

## Report Contents

### Executive Summary
- Total tasks processed
- Success rates and completion statistics
- Overall progress metrics
- Key achievements and challenges

### Task Breakdown
- Tasks grouped by priority (Critical, High, Medium, Low)
- Tasks categorized by type (Quality, Security, Architecture)
- Success/failure analysis
- Performance metrics

### Timeline Analysis
- Task completion trends over time
- Peak productivity periods
- Bottleneck identification
- Seasonal patterns

### Agent Performance
- Task assignment distribution
- Agent utilization rates
- Success rates by agent type
- Performance comparisons

## Time Periods

### Default Period (30 days)
- Monthly overview for regular reporting
- Balanced between detail and summary
- Suitable for most operational needs

### Custom Periods
- Weekly reports (7 days)
- Quarterly reviews (90 days)
- Annual summaries (365 days)
- Ad-hoc analysis (1-365 days)

## Report Sections

### Summary Statistics
```
ACGS-2 Coordination Report
Generated: 2024-01-04 15:00:00
Period: 30 days

EXECUTIVE SUMMARY
Total Tasks: 45
Completed: 38 (84.4%)
In Progress: 4 (8.9%)
Pending: 2 (4.4%)
Failed: 1 (2.2%)
Overall Progress: 87.3%
```

### Priority Analysis
- Critical tasks: completion rate, average time, success rate
- High priority: throughput metrics, bottleneck analysis
- Medium/Low: efficiency metrics, scheduling optimization

### Task Type Analysis
- Quality tasks: code improvement metrics, file counts
- Security tasks: vulnerability findings, compliance scores
- Architecture tasks: optimization gains, complexity reductions

## Integration Options

### CI/CD Integration
- Automated report generation in pipelines
- Quality gate integration
- Deployment readiness validation

### Dashboard Integration
- Real-time metrics feeds
- Historical trend analysis
- Predictive analytics input

### Documentation Systems
- Automatic wiki updates
- Report archiving
- Stakeholder notifications

## Examples

### Generate default text report
```bash
npx claude-flow coordination report
```

### Generate markdown report for documentation
```bash
npx claude-flow coordination report --format markdown
```

### Generate weekly report with completed tasks
```bash
npx claude-flow coordination report --period 7 --include-completed
```

### Generate JSON report for analysis
```bash
npx claude-flow coordination report --format json --period 90
```

### In Claude Code
```javascript
mcp__claude-flow__coordination_report({
  format: "markdown",
  period: 30,
  includeCompleted: true
})
```

## Report Customization

### Filtering Options
- Date range selection
- Task type filtering
- Agent type filtering
- Priority level filtering

### Content Options
- Include/exclude completed tasks
- Detail level adjustment
- Metric selection
- Custom sections

## Performance Insights

### Efficiency Metrics
- Task completion velocity
- Resource utilization rates
- Quality improvement trends
- Time-to-completion analysis

### Predictive Analytics
- Estimated completion times
- Resource requirement forecasting
- Bottleneck prediction
- Optimization recommendations

## Data Export

### JSON Export
```json
{
  "summary": {
    "totalTasks": 45,
    "completed": 38,
    "inProgress": 4,
    "pending": 2,
    "failed": 1,
    "overallProgress": 87.3
  },
  "tasks": [...],
  "timeline": {...},
  "agents": {...}
}
```

### CSV Export (via JSON)
Structured data can be converted to CSV for spreadsheet analysis and reporting.

## See Also

- `coordination list` - List available coordination tasks
- `coordination execute` - Execute specific coordination tasks
- `coordination status` - Check task execution status
- `task orchestrate` - Coordinate task execution across swarms

--- End Command ---
