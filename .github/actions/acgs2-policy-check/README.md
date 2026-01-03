# ACGS2 Policy Check GitHub Action

Validates resources against ACGS2 governance policies in CI/CD pipelines. This action integrates with the ACGS2 Integration Service to perform policy validation and can block merges when violations are detected.

## Features

- **Policy Validation**: Check resources against ACGS2 governance policies
- **PR Annotations**: Automatically annotate PRs with violation details
- **Configurable Severity**: Set thresholds for what severity level fails the check
- **Multiple Resource Types**: Supports Kubernetes, Terraform, code files, and more
- **Detailed Reports**: Generate markdown or JSON reports in job summaries
- **Flexible Configuration**: Include/exclude patterns, custom policies, timeouts

## Usage

### Basic Usage

```yaml
name: Policy Check

on:
  pull_request:
    branches: [main]

jobs:
  policy-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: ACGS2 Policy Check
        uses: ./.github/actions/acgs2-policy-check
        with:
          api-url: ${{ secrets.ACGS2_API_URL }}
          api-token: ${{ secrets.ACGS2_API_TOKEN }}
```

### Advanced Usage

```yaml
name: Governance Check

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main]

jobs:
  policy-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: ACGS2 Policy Check
        id: policy
        uses: ./.github/actions/acgs2-policy-check
        with:
          api-url: ${{ secrets.ACGS2_API_URL }}
          api-token: ${{ secrets.ACGS2_API_TOKEN }}
          policy-id: 'security-baseline'
          resource-type: 'kubernetes'
          resource-path: './k8s/'
          fail-on-violation: 'true'
          severity-threshold: 'high'
          annotations: 'true'
          report-format: 'markdown'
          timeout: '60'
          include-patterns: '**/*.yaml,**/*.yml'
          exclude-patterns: '**/test/**,**/mock/**'

      - name: Upload Report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: policy-report
          path: policy-report.md

      - name: Comment on PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const result = '${{ steps.policy.outputs.result }}';
            const violations = '${{ steps.policy.outputs.violations-count }}';
            github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: `## Policy Check ${result === 'pass' ? ':white_check_mark:' : ':x:'}\n\nFound ${violations} violation(s).`
            });
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `api-url` | ACGS2 Integration Service API URL | Yes | `http://localhost:8100` |
| `api-token` | ACGS2 API authentication token | No | - |
| `policy-id` | Specific policy ID to check (checks all if not specified) | No | - |
| `resource-type` | Type of resource (deployment, config, code) | No | `code` |
| `resource-path` | Path to resource file or directory | No | `.` |
| `fail-on-violation` | Fail workflow on policy violations | No | `true` |
| `severity-threshold` | Minimum severity to fail on | No | `high` |
| `annotations` | Create PR annotations for violations | No | `true` |
| `report-format` | Output format (json, markdown, summary) | No | `markdown` |
| `timeout` | API request timeout in seconds | No | `30` |
| `include-patterns` | Glob patterns of files to include | No | `**/*` |
| `exclude-patterns` | Glob patterns of files to exclude | No | `node_modules/**,vendor/**,.git/**` |

## Outputs

| Output | Description |
|--------|-------------|
| `result` | Policy check result (`pass` or `fail`) |
| `violations-count` | Total number of policy violations |
| `critical-count` | Number of critical severity violations |
| `high-count` | Number of high severity violations |
| `medium-count` | Number of medium severity violations |
| `low-count` | Number of low severity violations |
| `report` | Full policy check report |
| `report-url` | URL to view full report (if applicable) |

## Severity Levels

Violations are categorized by severity:

| Severity | Description |
|----------|-------------|
| `critical` | Security vulnerabilities, compliance violations that must be fixed immediately |
| `high` | Significant policy violations that should block deployment |
| `medium` | Important issues that should be addressed soon |
| `low` | Minor issues, best practice recommendations |
| `info` | Informational messages, style suggestions |

## Resource Types

Supported resource types:

- `code` - Source code files (Python, JavaScript, Go, etc.)
- `kubernetes` - Kubernetes YAML manifests
- `terraform` - Terraform configuration files
- `docker` - Dockerfiles
- `config` - Configuration files (JSON, YAML)
- `script` - Shell scripts

## Error Handling

The action handles various error conditions:

- **API Unavailable**: Logs a warning and runs in dry-run mode
- **Authentication Failure**: Fails with clear error message
- **Timeout**: Fails if API doesn't respond within configured timeout
- **Invalid Response**: Fails with details about the unexpected response

## Examples

### Kubernetes Manifest Validation

```yaml
- name: Validate K8s Manifests
  uses: ./.github/actions/acgs2-policy-check
  with:
    api-url: ${{ secrets.ACGS2_API_URL }}
    resource-type: kubernetes
    resource-path: ./kubernetes/
    severity-threshold: high
```

### Terraform Plan Validation

```yaml
- name: Validate Terraform
  uses: ./.github/actions/acgs2-policy-check
  with:
    api-url: ${{ secrets.ACGS2_API_URL }}
    resource-type: terraform
    resource-path: ./infrastructure/
    policy-id: cloud-security-baseline
```

### Security-Only Check (Non-Blocking)

```yaml
- name: Security Scan
  uses: ./.github/actions/acgs2-policy-check
  with:
    api-url: ${{ secrets.ACGS2_API_URL }}
    fail-on-violation: 'false'
    severity-threshold: critical
    annotations: 'true'
```

## Integration with ACGS2

This action communicates with the ACGS2 Integration Service's policy validation endpoint:

```
POST /api/policy/validate
```

The request includes:
- Resources to validate
- Resource type
- Policy ID (optional)
- GitHub context (repository, ref, sha, actor)

The response includes:
- Pass/fail status
- List of violations with severity, file, line, and message
- Recommendations for remediation

## License

MIT
