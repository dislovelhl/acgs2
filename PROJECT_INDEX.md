# Project Index: acgs2-root

Generated: 2026-01-03T16:00:25.546865

---

## 📁 Project Structure

```
.agent/
  workflows/
    base/
    constitutional/
    coordination/
    cyclic/
    dags/
    sagas/
    templates/
    tests/
.auto-claude/
  roadmap/
.cursor/
.dist/
  .claude/
    agents/
      neural/
.github/
  actions/
    acgs2-policy-check/
  workflows/
.kilocode/
  rules/
.kilocode-context/
.roo/
  rules-docs-specialist/
.serena/
  memories/
.swarm/
.vscode/
acgs2-core/
  .github/
    workflows/
  .semgrep/
    rules/
  C4-Documentation/
  breakthrough/
    context/
    governance/
    integrations/
    policy/
    symbolic/
    temporal/
    tests/
    verification/
  cert-manager/
  chaos/
    enterprise/
    experiments/
    monitors/
    recovery/
  cli/
  config/
  data/
  deploy/
    helm/
      acgs2/
        templates/
  docs/
    adr/
    api/
      specs/
    architecture/
    compliance/
      templates/
    design/
    istio/
    monitoring/
    operations/
    performance/
    reports/
    security/
    user-guides/
  enhanced_agent_bus/
    C4-Documentation/
      apis/
    acl_adapters/
      tests/
    ai_assistant/
      tests/
    benchmarks/
    components/
    context/
    data/
      reference/
    deliberation_layer/
      workflows/
    docs/
      guides/
      reports/
    examples/
    governance/
    integrations/
    mcp_server/
      adapters/
      protocol/
      resources/
      tests/
      tools/
    observability/
      tests/
    orchestration/
    policies/
    profiling/
    runtime/
      policy_bundles/
    rust/
      src/
    sdpc/
    security/
    specs/
      fixtures/
      tests/
    symbolic/
    temporal/
    tests/
      fixtures/
      runtime/
        policy_bundles/
    verification/
    workflows/
  examples/
    basic-governance/
    hitl-approval-workflow/
  infrastructure/
    governance/
      tests/
  integrations/
    nemo_agent_toolkit/
      .claude-flow/
        metrics/
      colang/
      tests/
  monitoring/
    alerts/
    collectors/
    connectors/
    dashboards/
      real_time/
      templates/
    grafana/
      provisioning/
        dashboards/
        datasources/
  notebooks/
  plans/
  playground/
    frontend/
  policies/
    rego/
      agent_bus/
      constitutional/
      deliberation/
      test_inputs/
    schema/
    templates/
  quantum_research/
    tests/
  runtime/
    policy_bundles/
  rust-perf/
    src/
  scripts/
  sdk/
    go/
      examples/
        comprehensive/
    python/
      acgs2_sdk/
        services/
      examples/
      tests/
    typescript/
      examples/
      src/
        client/
        services/
        types/
        utils/
  services/
    analytics-api/
      src/
        models/
        routes/
        services/
      tests/
        integration/
    analytics-engine/
      data/
      src/
      tests/
    api_gateway/
      routes/
      tests/
        integration/
        unit/
    audit_service/
      app/
        api/
        models/
        services/
        tasks/
        templates/
      blockchain/
        arweave/
        ethereum_l2/
        hyperledger_fabric/
        solana/
      cli/
      config/
        hyperledger/
      core/
        merkle_tree/
      reporters/
      tests/
        integration/
        unit/
      zkp/
        circuits/
    auth_sso/
    autonomous_governance/
    compliance_docs/
      src/
        api/
        generators/
        models/
        templates/
          euaiact/
          gdpr/
          iso27001/
          soc2/
      tests/
        unit/
    core/
      code-analysis/
        code_analysis_service/
          app/
            api/
              v1/
            core/
            middleware/
            services/
            utils/
          config/
        tests/
          integration/
          unit/
      constitutional-retrieval-system/
      constraint_generation_system/
      ml-governance/
        ml_governance_service/
          src/
            api/
            models/
    governance_federation/
    hitl-approvals/
      app/
        api/
        audit/
        core/
        notifications/
      tests/
    hitl_approvals/
      app/
        api/
        audit/
        config/
        core/
        models/
        notifications/
        schemas/
        services/
        tasks/
        templates/
      src/
        api/
        core/
      tests/
        unit/
    identity/
      connectors/
    integration/
      search_platform/
        tests/
    integration_service/
      src/
        integrations/
    metering/
      app/
      tests/
    ml_governance/
      src/
        api/
        core/
      tests/
    policy_marketplace/
      alembic/
        versions/
      app/
        api/
          v1/
        config/
        models/
        schemas/
      scripts/
      templates/
        verified/
      tests/
        e2e/
    policy_registry/
      advanced_rbac/
        delegation/
        models/
        policies/
      app/
        api/
          v1/
        middleware/
        models/
        services/
          tests/
        templates/
          financial/
          healthcare/
      config/
      examples/
      k8s/
      tests/
    shared/
      alembic/
        versions/
    tenant_management/
      onboarding/
      src/
      tests/
        unit/
  shared/
    auth/
      certs/
      tests/
    circuit_breaker/
    config/
    database/
    infrastructure/
    logging/
    metrics/
    middleware/
    models/
    security/
    tests/
  testing/
    tests/
  tests/
    ceos/
    cli/
    e2e/
    fixtures/
    infrastructure/
    integration/
    playground/
    security/
  tools/
    acgs2-cli/
      commands/
    sc/
acgs2-frontend/
  policy-marketplace/
    public/
    src/
      components/
      services/
      types/
acgs2-infra/
  cert-manager/
  deploy/
    gitops/
      argocd/
        applications/
        projects/
    helm/
      acgs2/
        templates/
          agent-bus/
          api-gateway/
          constitutional-service/
    terraform/
      aws/
        modules/
          ecr/
          eks/
          elasticache/
          msk/
          rds/
      gcp/
        modules/
          artifact-registry/
          cloudsql/
          gke/
          memorystore/
          pubsub/
  k8s/
  multi-region/
    compliance/
    database/
    docs/
    governance/
    istio/
    k8s/
    kafka/
    scripts/
  scripts/
  terraform/
    aws/
    gcp/
acgs2-neural-mcp/
  src/
    __tests__/
      config/
    config/
    neural/
    utils/
acgs2-observability/
  monitoring/
    collectors/
    connectors/
    dashboard/
      src/
        components/
        hooks/
        types/
        utils/
    grafana/
      dashboards/
    kibana/
    logstash/
      config/
      pipeline/
  tests/
    monitoring/
acgs2-research/
  configs/
  docs/
    research/
      breakthrough_2025/
  governance-experiments/
    data/
      tasks/
    notebooks/
    policies/
      rego/
    policy-watch/
    reports/
    scripts/
    src/
      crypto/
      evaluators/
    tests/
adaptive-learning-engine/
  src/
    api/
    models/
    monitoring/
    registry/
    safety/
  tests/
    e2e/
    integration/
    unit/
analytics-dashboard/
  docs/
  src/
    components/
      __tests__/
      widgets/
        __tests__/
    layouts/
      __tests__/
    test/
      e2e/
      integration/
      mocks/
architecture/
archive/
  services/
    agent_inventory/
    constitutional_ai/
assets/
ci/
claude-flow/
  docs/
  src/
    __tests__/
      config/
    commands/
    config/
    services/
    types/
    utils/
  storage/
claudedocs/
compliance-docs-service/
config/
docs/
  api/
    generated/
      enhanced_specs/
    specs/
  coverage/
    enhanced/
  data/
  deployment/
    air-gapped/
    high-availability/
    multi-region/
  due-diligence/
  observability/
  postman/
  quickstart/
    video-scripts/
  summaries/
  tutorials/
examples/
  01-basic-policy-evaluation/
    policies/
  02-ai-model-approval/
    policies/
  03-data-access-control/
    policies/
integration-service/
  scripts/
  src/
    api/
    config/
    consumers/
    integrations/
    webhooks/
  templates/
  tests/
    integrations/
    webhooks/
notebooks/
policies/
  vertical-templates/
    finance/
    healthcare/
reports/
  monitoring/
runtime/
  policy_bundles/
scripts/
sdk/
  go/
    internal/
      http/
    pkg/
      auth/
      client/
      models/
  typescript/
    src/
      auth/
      core/
      utils/
```

---

## 🚀 Entry Points

| Type | Path | Purpose |
|------|------|---------|
| Application | `examples/02-ai-model-approval/app.py` | Core entry point |
| Application | `acgs2-core/playground/app.py` | Core entry point |
| CLI | `acgs2-core/enhanced_agent_bus/mcp_server/cli.py` | Core entry point |
| CLI | `acgs2-core/tools/acgs2-cli/main.py` | Core entry point |
| CLI | `acgs2-core/services/hitl-approvals/main.py` | Core entry point |
| CLI | `acgs2-core/services/api_gateway/main.py` | Core entry point |
| CLI | `acgs2-core/services/hitl_approvals/main.py` | Core entry point |
| CLI | `acgs2-core/services/tenant_management/src/main.py` | Core entry point |
| CLI | `acgs2-core/services/ml_governance/src/main.py` | Core entry point |
| CLI | `acgs2-core/services/analytics-api/src/main.py` | Core entry point |

---

## 📦 Core Modules

### Module: fix_lints
- **Path**: `fix_lints.py`
- **Language**: python
- **Exports**: fix_b904
- **Purpose**: Core functionality

### Module: test_performance_fix
- **Path**: `test_performance_fix.py`
- **Language**: python
- **Exports**: MockConfig:, __init__
- **Purpose**: Testing utilities

### Module: run_unified_tests
- **Path**: `scripts/run_unified_tests.py`
- **Language**: python
- **Exports**: UnifiedTestRunner:, __init__
- **Purpose**: Testing utilities

### Module: validate-sdk-publishing
- **Path**: `scripts/validate-sdk-publishing.py`
- **Language**: python
- **Exports**: Colors:, print_header, print_success
- **Purpose**: Core functionality

### Module: import_health_check
- **Path**: `scripts/import_health_check.py`
- **Language**: python
- **Exports**: get_python_files, extract_module_name, check_module_imports
- **Purpose**: Core functionality

### Module: import_simplifier
- **Path**: `scripts/import_simplifier.py`
- **Language**: python
- **Exports**: simplify_imports_in_file
- **Purpose**: Core functionality

### Module: import_refactor
- **Path**: `scripts/import_refactor.py`
- **Language**: python
- **Exports**: ImportRefactorer, __init__, visit_Try
- **Purpose**: Core functionality

### Module: profile_message_processor
- **Path**: `scripts/profile_message_processor.py`
- **Language**: python
- **Exports**: ProfilingResult:
- **Purpose**: Core functionality

### Module: fix_typescript_console_logs
- **Path**: `scripts/fix_typescript_console_logs.py`
- **Language**: python
- **Exports**: find_console_logs
- **Purpose**: Core functionality

### Module: deliberation_layer_profiler
- **Path**: `scripts/deliberation_layer_profiler.py`
- **Language**: python
- **Exports**: ProfilingResult:, DeliberationLayerProfiler:, __init__
- **Purpose**: Testing utilities

---

## 🔧 Configuration

- `pyproject.toml` (Python Project)
- `.pre-commit-config.yaml` (Configuration)
- `compose.yaml` (Configuration)
- `codecov.yml` (Configuration)
- `docker-compose.horizontal-scaling.yml` (Docker)

---

## 📚 Documentation

- `README.md` - ACGS-2: Advanced Constitutional Governance System (README)
- `docs/workflows_reference.md` - ACGS-2 Workflow Reference (Documentation)
- `docs/CONFIGURATION_TROUBLESHOOTING.md` - ACGS-2 Configuration Troubleshooting Runbook (Documentation)
- `docs/CI-MIGRATION.md` - ACGS2 CI/CD Migration Summary (Documentation)
- `docs/getting-started.md` - 🚀 Getting Started with ACGS-2 (Documentation)
- `docs/validation_report.md` - Developer Onboarding Validation Report (Documentation)
- `docs/feedback.md` - ACGS-2 Developer Feedback (Documentation)
- `docs/DEVELOPMENT.md` - ACGS-2 Development Guide (Documentation)
- `docs/testing-guide.md` - ACGS-2 Testing Guide (Documentation)
- `docs/cross-platform-testing.md` - Cross-Platform Testing Guide (Documentation)

---

## 📝 Quick Start

1. **Setup**: Install dependencies
2. **Configure**: Update configuration files
3. **Run**: Start development server
4. **Test**: Run test suite

---

**Index Size**: ~12KB | **Last Updated**: 2026-01-03
