#!/bin/bash
#
# ACGS2 Policy Check Script for GitLab CI/CD
#
# This script validates resources against ACGS2 governance policies
# and provides detailed reporting with GitLab MR integration.
#
# Environment Variables:
#   ACGS2_API_URL          - ACGS2 Integration Service URL (required)
#   ACGS2_API_TOKEN        - API authentication token
#   ACGS2_POLICY_ID        - Specific policy to check (optional)
#   ACGS2_RESOURCE_TYPE    - Type of resources (code, kubernetes, terraform, docker, config)
#   ACGS2_RESOURCE_PATH    - Path to resources to validate
#   ACGS2_SEVERITY_THRESHOLD - Minimum severity to fail (critical, high, medium, low, info)
#   ACGS2_FAIL_ON_VIOLATION - Whether to fail on violations (true/false)
#   ACGS2_REPORT_FORMAT    - Output format (markdown, json, summary, codeclimate)
#   ACGS2_TIMEOUT          - API request timeout in seconds
#   ACGS2_INCLUDE_PATTERNS - Glob patterns to include
#   ACGS2_EXCLUDE_PATTERNS - Glob patterns to exclude
#
# GitLab CI Variables (auto-populated):
#   CI_PROJECT_PATH, CI_COMMIT_REF_NAME, CI_COMMIT_SHA, CI_PIPELINE_ID,
#   CI_JOB_ID, GITLAB_USER_LOGIN, CI_MERGE_REQUEST_IID, CI_API_V4_URL,
#   GITLAB_TOKEN (for MR comments)

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

# Default values
API_URL="${ACGS2_API_URL:-http://localhost:8100}"
API_TOKEN="${ACGS2_API_TOKEN:-}"
POLICY_ID="${ACGS2_POLICY_ID:-}"
RESOURCE_TYPE="${ACGS2_RESOURCE_TYPE:-code}"
RESOURCE_PATH="${ACGS2_RESOURCE_PATH:-.}"
SEVERITY_THRESHOLD="${ACGS2_SEVERITY_THRESHOLD:-high}"
FAIL_ON_VIOLATION="${ACGS2_FAIL_ON_VIOLATION:-true}"
REPORT_FORMAT="${ACGS2_REPORT_FORMAT:-markdown}"
TIMEOUT="${ACGS2_TIMEOUT:-30}"
INCLUDE_PATTERNS="${ACGS2_INCLUDE_PATTERNS:-**/*}"
EXCLUDE_PATTERNS="${ACGS2_EXCLUDE_PATTERNS:-node_modules/**,vendor/**,.git/**}"

# Severity levels (higher = more severe)
declare -A SEVERITY_LEVELS
SEVERITY_LEVELS=([critical]=5 [high]=4 [medium]=3 [low]=2 [info]=1)

# Output files
REPORT_MD="acgs2-policy-report.md"
REPORT_JSON="acgs2-policy-report.json"
ENV_FILE="acgs2-policy.env"
CODECLIMATE_FILE="gl-code-quality-report.json"

# Counters
CRITICAL_COUNT=0
HIGH_COUNT=0
MEDIUM_COUNT=0
LOW_COUNT=0
INFO_COUNT=0
TOTAL_VIOLATIONS=0

# =============================================================================
# Utility Functions
# =============================================================================

log_info() {
    echo "[INFO] $*"
}

log_warn() {
    echo "[WARN] $*" >&2
}

log_error() {
    echo "[ERROR] $*" >&2
}

log_debug() {
    if [[ "${ACGS2_DEBUG:-false}" == "true" ]]; then
        echo "[DEBUG] $*"
    fi
}

# Print section header
section() {
    echo ""
    echo "========================================"
    echo "$*"
    echo "========================================"
}

# Check if command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# =============================================================================
# Resource Gathering
# =============================================================================

# Get file type from extension
get_resource_type() {
    local file="$1"
    local ext="${file##*.}"

    case "${ext,,}" in
        yaml|yml)
            echo "kubernetes"
            ;;
        tf|tfvars)
            echo "terraform"
            ;;
        py|js|ts|go|java|rs|rb)
            echo "code"
            ;;
        json)
            echo "config"
            ;;
        dockerfile*)
            echo "docker"
            ;;
        sh|bash)
            echo "script"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

# Check if file should be excluded
should_exclude() {
    local file="$1"
    local IFS=','

    for pattern in $EXCLUDE_PATTERNS; do
        pattern=$(echo "$pattern" | xargs)  # Trim whitespace

        # Handle ** patterns
        if [[ "$pattern" == *"**"* ]]; then
            local prefix="${pattern%%/**}"
            if [[ "$file" == "$prefix"* || "$file" == *"/$prefix"* ]]; then
                return 0
            fi
        elif [[ "$file" == *"$pattern"* || "$(basename "$file")" == "$pattern" ]]; then
            return 0
        fi
    done

    return 1
}

# Gather resources to validate
gather_resources() {
    local base_path="$1"
    local resources=()

    if [[ -f "$base_path" ]]; then
        resources+=("$base_path")
    elif [[ -d "$base_path" ]]; then
        while IFS= read -r -d '' file; do
            if ! should_exclude "$file"; then
                resources+=("$file")
            fi
        done < <(find "$base_path" -type f -print0 2>/dev/null)
    fi

    printf '%s\n' "${resources[@]}"
}

# Build resources JSON for API request
build_resources_json() {
    local base_path="$1"
    local files
    files=$(gather_resources "$base_path")

    local json_array="["
    local first=true

    while IFS= read -r file; do
        [[ -z "$file" ]] && continue

        if [[ "$first" == "true" ]]; then
            first=false
        else
            json_array+=","
        fi

        local file_type
        file_type=$(get_resource_type "$file")

        # Read file content (with size limit)
        local content=""
        if [[ -f "$file" && -r "$file" ]]; then
            # Limit content to 100KB
            content=$(head -c 102400 "$file" 2>/dev/null | jq -Rs '.' 2>/dev/null || echo '""')
            content=${content:1:-1}  # Remove surrounding quotes from jq output
        fi

        json_array+="{\"path\":\"$file\",\"type\":\"$file_type\",\"content\":\"$content\"}"
    done <<< "$files"

    json_array+="]"
    echo "$json_array"
}

# =============================================================================
# API Communication
# =============================================================================

# Make API request
api_request() {
    local method="$1"
    local endpoint="$2"
    local data="${3:-}"

    local url="${API_URL}${endpoint}"
    local headers=(-H "Content-Type: application/json" -H "Accept: application/json")

    if [[ -n "$API_TOKEN" ]]; then
        headers+=(-H "Authorization: Bearer $API_TOKEN")
    fi

    local curl_opts=(
        -s
        -w "\n%{http_code}"
        --max-time "$TIMEOUT"
        "${headers[@]}"
    )

    if [[ "$method" == "POST" && -n "$data" ]]; then
        curl_opts+=(-X POST -d "$data")
    fi

    log_debug "API Request: $method $url"

    local response
    response=$(curl "${curl_opts[@]}" "$url" 2>&1) || {
        log_error "API request failed: $response"
        return 1
    }

    echo "$response"
}

# Validate policies against API
validate_policies() {
    local resources_json="$1"

    # Build request body
    local request_body
    request_body=$(cat <<EOF
{
    "resources": $resources_json,
    "resource_type": "$RESOURCE_TYPE",
    "policy_id": ${POLICY_ID:+\"$POLICY_ID\"}${POLICY_ID:-null},
    "context": {
        "gitlab_project": "${CI_PROJECT_PATH:-}",
        "gitlab_ref": "${CI_COMMIT_REF_NAME:-}",
        "gitlab_sha": "${CI_COMMIT_SHA:-}",
        "gitlab_pipeline_id": "${CI_PIPELINE_ID:-}",
        "gitlab_job_id": "${CI_JOB_ID:-}",
        "gitlab_user": "${GITLAB_USER_LOGIN:-}",
        "gitlab_mr_iid": "${CI_MERGE_REQUEST_IID:-}",
        "ci_platform": "gitlab"
    }
}
EOF
)

    log_debug "Request body: $request_body"

    local response
    response=$(api_request "POST" "/api/policy/validate" "$request_body") || {
        # Return mock response for testing/dry-run
        log_warn "Could not connect to ACGS2 API. Running in dry-run mode."
        echo '{"passed": true, "violations": [], "recommendations": ["Connect to ACGS2 Integration Service for full validation"], "dry_run": true}'
        return 0
    }

    # Extract HTTP status code (last line)
    local http_code
    http_code=$(echo "$response" | tail -n1)
    local body
    body=$(echo "$response" | sed '$d')

    log_debug "HTTP Status: $http_code"
    log_debug "Response body: $body"

    case "$http_code" in
        200|201)
            echo "$body"
            ;;
        401)
            log_error "Authentication failed: Invalid or missing API token"
            return 1
            ;;
        403)
            log_error "Authorization failed: Insufficient permissions"
            return 1
            ;;
        404)
            log_warn "Policy validation endpoint not found. Running in dry-run mode."
            echo '{"passed": true, "violations": [], "recommendations": ["Ensure ACGS2 Integration Service is running"], "dry_run": true}'
            ;;
        422)
            log_error "Validation error: $(echo "$body" | jq -r '.detail // "Invalid request"')"
            return 1
            ;;
        5*)
            log_error "Server error ($http_code): $body"
            return 1
            ;;
        *)
            log_error "Unexpected response ($http_code): $body"
            return 1
            ;;
    esac
}

# =============================================================================
# Violation Processing
# =============================================================================

# Process violations and update counters
process_violations() {
    local violations_json="$1"

    TOTAL_VIOLATIONS=$(echo "$violations_json" | jq 'length')
    CRITICAL_COUNT=$(echo "$violations_json" | jq '[.[] | select(.severity == "critical")] | length')
    HIGH_COUNT=$(echo "$violations_json" | jq '[.[] | select(.severity == "high")] | length')
    MEDIUM_COUNT=$(echo "$violations_json" | jq '[.[] | select(.severity == "medium")] | length')
    LOW_COUNT=$(echo "$violations_json" | jq '[.[] | select(.severity == "low")] | length')
    INFO_COUNT=$(echo "$violations_json" | jq '[.[] | select(.severity == "info" or .severity == null)] | length')

    log_info "Violations found: Total=$TOTAL_VIOLATIONS (Critical=$CRITICAL_COUNT, High=$HIGH_COUNT, Medium=$MEDIUM_COUNT, Low=$LOW_COUNT, Info=$INFO_COUNT)"
}

# Check if violations exceed threshold
exceeds_threshold() {
    local threshold="${SEVERITY_LEVELS[$SEVERITY_THRESHOLD]:-4}"

    if [[ $CRITICAL_COUNT -gt 0 && ${SEVERITY_LEVELS[critical]} -ge $threshold ]]; then
        return 0
    fi
    if [[ $HIGH_COUNT -gt 0 && ${SEVERITY_LEVELS[high]} -ge $threshold ]]; then
        return 0
    fi
    if [[ $MEDIUM_COUNT -gt 0 && ${SEVERITY_LEVELS[medium]} -ge $threshold ]]; then
        return 0
    fi
    if [[ $LOW_COUNT -gt 0 && ${SEVERITY_LEVELS[low]} -ge $threshold ]]; then
        return 0
    fi
    if [[ $INFO_COUNT -gt 0 && ${SEVERITY_LEVELS[info]} -ge $threshold ]]; then
        return 0
    fi

    return 1
}

# =============================================================================
# Report Generation
# =============================================================================

# Generate markdown report
generate_markdown_report() {
    local result_json="$1"
    local violations_json
    violations_json=$(echo "$result_json" | jq '.violations // []')
    local passed
    passed=$(echo "$result_json" | jq -r '.passed // false')
    local dry_run
    dry_run=$(echo "$result_json" | jq -r '.dry_run // false')

    local status_icon
    local status_text
    if [[ "$passed" == "true" ]]; then
        status_icon=":white_check_mark:"
        status_text="PASSED"
    else
        status_icon=":x:"
        status_text="FAILED"
    fi

    cat <<EOF
## ACGS2 Policy Check Report $status_icon

### Summary

| Metric | Value |
|--------|-------|
| **Status** | $status_text |
| **Total Violations** | $TOTAL_VIOLATIONS |
| **Critical** | $CRITICAL_COUNT |
| **High** | $HIGH_COUNT |
| **Medium** | $MEDIUM_COUNT |
| **Low** | $LOW_COUNT |
| **Info** | $INFO_COUNT |

EOF

    if [[ "$dry_run" == "true" ]]; then
        cat <<EOF
> :warning: **Dry Run Mode**: Could not connect to ACGS2 API. Results may not reflect actual policy compliance.

EOF
    fi

    if [[ $TOTAL_VIOLATIONS -gt 0 ]]; then
        cat <<EOF
### Violations

| Severity | Policy | File | Line | Message |
|----------|--------|------|------|---------|
EOF

        echo "$violations_json" | jq -r '.[] | "| \(.severity // "info" | ascii_upcase) | \(.policy_name // .policy_id // "N/A") | \(.file // .resource_path // "N/A") | \(.line // "N/A") | \(.message // .description // "No description") |"'
        echo ""
    fi

    # Recommendations
    local recommendations
    recommendations=$(echo "$result_json" | jq -r '.recommendations // [] | .[]')
    if [[ -n "$recommendations" ]]; then
        cat <<EOF

### Recommendations

EOF
        echo "$recommendations" | while read -r rec; do
            echo "- $rec"
        done
        echo ""
    fi

    cat <<EOF

---
_Report generated by ACGS2 Policy Check at $(date -u +"%Y-%m-%dT%H:%M:%SZ")_

**Pipeline**: [#${CI_PIPELINE_ID:-N/A}](${CI_PIPELINE_URL:-#})
**Commit**: ${CI_COMMIT_SHORT_SHA:-N/A}
**Branch**: ${CI_COMMIT_REF_NAME:-N/A}

_Powered by [ACGS2 Governance Platform](https://github.com/your-org/acgs2)_
EOF
}

# Generate JSON report
generate_json_report() {
    local result_json="$1"

    cat <<EOF
{
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "status": $(echo "$result_json" | jq '.passed // false'),
    "summary": {
        "total_violations": $TOTAL_VIOLATIONS,
        "critical": $CRITICAL_COUNT,
        "high": $HIGH_COUNT,
        "medium": $MEDIUM_COUNT,
        "low": $LOW_COUNT,
        "info": $INFO_COUNT
    },
    "violations": $(echo "$result_json" | jq '.violations // []'),
    "recommendations": $(echo "$result_json" | jq '.recommendations // []'),
    "metadata": {
        "project": "${CI_PROJECT_PATH:-}",
        "ref": "${CI_COMMIT_REF_NAME:-}",
        "sha": "${CI_COMMIT_SHA:-}",
        "pipeline_id": "${CI_PIPELINE_ID:-}",
        "job_id": "${CI_JOB_ID:-}",
        "user": "${GITLAB_USER_LOGIN:-}"
    },
    "configuration": {
        "api_url": "$API_URL",
        "policy_id": "${POLICY_ID:-null}",
        "resource_type": "$RESOURCE_TYPE",
        "severity_threshold": "$SEVERITY_THRESHOLD",
        "fail_on_violation": $FAIL_ON_VIOLATION
    }
}
EOF
}

# Generate CodeClimate-compatible report for GitLab Code Quality
generate_codeclimate_report() {
    local result_json="$1"
    local violations_json
    violations_json=$(echo "$result_json" | jq '.violations // []')

    echo "$violations_json" | jq '[.[] | {
        type: "issue",
        check_name: (.policy_name // .policy_id // "policy-violation"),
        description: (.message // .description // "Policy violation detected"),
        content: {
            body: (.details // .message // "No additional details")
        },
        categories: ["Security"],
        severity: (
            if .severity == "critical" then "blocker"
            elif .severity == "high" then "critical"
            elif .severity == "medium" then "major"
            elif .severity == "low" then "minor"
            else "info"
            end
        ),
        location: {
            path: (.file // .resource_path // "unknown"),
            lines: {
                begin: (.line // 1)
            }
        },
        fingerprint: ((.policy_id // "") + "-" + (.file // "") + "-" + ((.line // 1) | tostring))
    }]'
}

# Generate summary report
generate_summary_report() {
    local result_json="$1"
    local passed
    passed=$(echo "$result_json" | jq -r '.passed // false')

    local status
    if [[ "$passed" == "true" ]]; then
        status="PASSED"
    else
        status="FAILED"
    fi

    cat <<EOF
ACGS2 Policy Check: $status
Violations: $TOTAL_VIOLATIONS (Critical: $CRITICAL_COUNT, High: $HIGH_COUNT, Medium: $MEDIUM_COUNT, Low: $LOW_COUNT, Info: $INFO_COUNT)
Threshold: $SEVERITY_THRESHOLD | Fail on Violation: $FAIL_ON_VIOLATION
EOF
}

# Write environment file for GitLab CI artifacts
write_env_file() {
    local passed="$1"

    cat > "$ENV_FILE" <<EOF
ACGS2_RESULT=$passed
ACGS2_TOTAL_VIOLATIONS=$TOTAL_VIOLATIONS
ACGS2_CRITICAL_COUNT=$CRITICAL_COUNT
ACGS2_HIGH_COUNT=$HIGH_COUNT
ACGS2_MEDIUM_COUNT=$MEDIUM_COUNT
ACGS2_LOW_COUNT=$LOW_COUNT
ACGS2_INFO_COUNT=$INFO_COUNT
ACGS2_SEVERITY_THRESHOLD=$SEVERITY_THRESHOLD
EOF
}

# =============================================================================
# GitLab MR Integration
# =============================================================================

# Post comment to GitLab MR
post_mr_comment() {
    local comment="$1"

    # Check if we're in an MR context
    if [[ -z "${CI_MERGE_REQUEST_IID:-}" ]]; then
        log_debug "Not in MR context, skipping MR comment"
        return 0
    fi

    # Check if we have GitLab token
    local token="${GITLAB_TOKEN:-${CI_JOB_TOKEN:-}}"
    if [[ -z "$token" ]]; then
        log_warn "No GitLab token available, skipping MR comment"
        return 0
    fi

    local api_url="${CI_API_V4_URL:-https://gitlab.com/api/v4}"
    local project_id="${CI_PROJECT_ID:-}"
    local mr_iid="${CI_MERGE_REQUEST_IID:-}"

    if [[ -z "$project_id" || -z "$mr_iid" ]]; then
        log_warn "Missing project ID or MR IID, skipping MR comment"
        return 0
    fi

    # Escape comment for JSON
    local escaped_comment
    escaped_comment=$(echo "$comment" | jq -Rs '.')

    local endpoint="${api_url}/projects/${project_id}/merge_requests/${mr_iid}/notes"

    log_info "Posting policy check report to MR #${mr_iid}"

    local response
    response=$(curl -s -w "\n%{http_code}" \
        --request POST \
        --header "PRIVATE-TOKEN: $token" \
        --header "Content-Type: application/json" \
        --data "{\"body\": $escaped_comment}" \
        "$endpoint" 2>&1) || {
        log_warn "Failed to post MR comment: $response"
        return 0
    }

    local http_code
    http_code=$(echo "$response" | tail -n1)

    if [[ "$http_code" == "201" ]]; then
        log_info "Successfully posted report to MR"
    else
        log_warn "Failed to post MR comment (HTTP $http_code)"
    fi
}

# Update existing MR comment or create new one
update_or_create_mr_comment() {
    local comment="$1"
    local marker="<!-- ACGS2 Policy Check Report -->"

    # Check if we're in an MR context
    if [[ -z "${CI_MERGE_REQUEST_IID:-}" ]]; then
        return 0
    fi

    local token="${GITLAB_TOKEN:-${CI_JOB_TOKEN:-}}"
    if [[ -z "$token" ]]; then
        log_warn "No GitLab token available, skipping MR comment"
        return 0
    fi

    local api_url="${CI_API_V4_URL:-https://gitlab.com/api/v4}"
    local project_id="${CI_PROJECT_ID:-}"
    local mr_iid="${CI_MERGE_REQUEST_IID:-}"

    # Add marker to comment for identification
    local marked_comment="${marker}
${comment}"

    # Try to find existing comment
    local notes_response
    notes_response=$(curl -s \
        --header "PRIVATE-TOKEN: $token" \
        "${api_url}/projects/${project_id}/merge_requests/${mr_iid}/notes?per_page=100" 2>&1) || {
        # If listing fails, just create new comment
        post_mr_comment "$marked_comment"
        return 0
    }

    # Find existing ACGS2 comment
    local existing_note_id
    existing_note_id=$(echo "$notes_response" | jq -r '.[] | select(.body | contains("ACGS2 Policy Check Report")) | .id' | head -n1)

    if [[ -n "$existing_note_id" && "$existing_note_id" != "null" ]]; then
        log_info "Updating existing MR comment (note #$existing_note_id)"

        local escaped_comment
        escaped_comment=$(echo "$marked_comment" | jq -Rs '.')

        curl -s \
            --request PUT \
            --header "PRIVATE-TOKEN: $token" \
            --header "Content-Type: application/json" \
            --data "{\"body\": $escaped_comment}" \
            "${api_url}/projects/${project_id}/merge_requests/${mr_iid}/notes/${existing_note_id}" > /dev/null 2>&1 || {
            log_warn "Failed to update existing comment, creating new one"
            post_mr_comment "$marked_comment"
        }
    else
        post_mr_comment "$marked_comment"
    fi
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    section "ACGS2 Policy Check - Configuration"

    log_info "API URL: $API_URL"
    log_info "Policy ID: ${POLICY_ID:-<all policies>}"
    log_info "Resource Type: $RESOURCE_TYPE"
    log_info "Resource Path: $RESOURCE_PATH"
    log_info "Severity Threshold: $SEVERITY_THRESHOLD"
    log_info "Fail on Violation: $FAIL_ON_VIOLATION"
    log_info "Report Format: $REPORT_FORMAT"
    log_info "Timeout: ${TIMEOUT}s"

    # Validate dependencies
    if ! command_exists curl; then
        log_error "curl is required but not installed"
        exit 1
    fi
    if ! command_exists jq; then
        log_error "jq is required but not installed"
        exit 1
    fi

    section "Gathering Resources"

    local resources_json
    resources_json=$(build_resources_json "$RESOURCE_PATH")
    local resource_count
    resource_count=$(echo "$resources_json" | jq 'length')
    log_info "Found $resource_count resource(s) to validate"

    section "Validating Policies"

    local result_json
    result_json=$(validate_policies "$resources_json") || {
        log_error "Policy validation failed"
        exit 1
    }

    section "Processing Results"

    local violations_json
    violations_json=$(echo "$result_json" | jq '.violations // []')
    process_violations "$violations_json"

    local passed
    passed=$(echo "$result_json" | jq -r '.passed // false')

    section "Generating Reports"

    # Generate markdown report (always)
    local markdown_report
    markdown_report=$(generate_markdown_report "$result_json")
    echo "$markdown_report" > "$REPORT_MD"
    log_info "Markdown report saved to $REPORT_MD"

    # Generate JSON report (always)
    local json_report
    json_report=$(generate_json_report "$result_json")
    echo "$json_report" > "$REPORT_JSON"
    log_info "JSON report saved to $REPORT_JSON"

    # Generate CodeClimate report if requested
    if [[ "$REPORT_FORMAT" == "codeclimate" ]]; then
        local codeclimate_report
        codeclimate_report=$(generate_codeclimate_report "$result_json")
        echo "$codeclimate_report" > "$CODECLIMATE_FILE"
        log_info "CodeClimate report saved to $CODECLIMATE_FILE"
    fi

    # Write environment file
    write_env_file "$passed"
    log_info "Environment file saved to $ENV_FILE"

    # Print summary
    section "Summary"
    generate_summary_report "$result_json"

    # Print full report based on format
    if [[ "$REPORT_FORMAT" == "json" ]]; then
        echo ""
        echo "$json_report" | jq '.'
    elif [[ "$REPORT_FORMAT" != "summary" && "$REPORT_FORMAT" != "codeclimate" ]]; then
        echo ""
        echo "$markdown_report"
    fi

    # Post to MR if in MR context
    if [[ -n "${CI_MERGE_REQUEST_IID:-}" ]]; then
        update_or_create_mr_comment "$markdown_report"
    fi

    section "Result"

    # Determine exit code
    if [[ "$FAIL_ON_VIOLATION" == "true" ]] && exceeds_threshold; then
        log_error "Policy check FAILED: Found violations at or above '$SEVERITY_THRESHOLD' severity"
        log_error "Critical: $CRITICAL_COUNT, High: $HIGH_COUNT, Medium: $MEDIUM_COUNT, Low: $LOW_COUNT, Info: $INFO_COUNT"
        exit 1
    elif [[ $TOTAL_VIOLATIONS -gt 0 ]]; then
        log_warn "Policy check completed with $TOTAL_VIOLATIONS violation(s), but none met the '$SEVERITY_THRESHOLD' severity threshold"
        exit 0
    else
        log_info "Policy check PASSED: No violations found"
        exit 0
    fi
}

# Run main function
main "$@"
