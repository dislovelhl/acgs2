# Project Index: 

Generated: 2026-01-03T16:15:58.744982

---

## 📁 Project Structure

```
.github/
  workflows/
.semgrep/
  rules/
.serena/
  memories/
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
  .ruff_cache/
    0.14.10/
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
    bundle_cache/
    policy_bundles/
  rust/
    src/
    target/
      debug/
        examples/
      release/
        examples/
        incremental/
  sdpc/
  security/
  specs/
    fixtures/
    tests/
  symbolic/
  temporal/
  test_venv/
    include/
      python3.12/
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
    docs/
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
        data/
          reference/
          training/
        src/
          api/
          feedback/
          models/
          monitoring/
          online_learning/
          training/
          versioning/
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
      static/
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
      api/
      auth/
      config/
      integrations/
      webhooks/
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
      services/
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
        autonomous/
        customer_service/
        financial/
        healthcare/
        moderation/
    config/
    examples/
    k8s/
    storage/
      bundles/
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
```

---

## 🚀 Entry Points

| Type | Path | Purpose |
|------|------|---------|
| Application | `playground/app.py` | Core entry point |
| CLI | `services/hitl_approvals/main.py` | Core entry point |
| CLI | `services/api_gateway/main.py` | Core entry point |
| CLI | `services/hitl-approvals/main.py` | Core entry point |
| CLI | `services/policy_marketplace/app/main.py` | Core entry point |
| CLI | `services/integration_service/src/main.py` | Core entry point |
| CLI | `services/hitl_approvals/src/main.py` | Core entry point |
| CLI | `services/audit_service/app/main.py` | Core entry point |
| CLI | `services/compliance_docs/src/main.py` | Core entry point |
| CLI | `services/policy_registry/app/main.py` | Core entry point |

---

## 📦 Core Modules

### Module: benchmark_scorer
- **Path**: `testing/benchmark_scorer.py`
- **Language**: python
- **Exports**: benchmark_scorer
- **Purpose**: Testing utilities

### Module: run_10k_rps_validation
- **Path**: `testing/run_10k_rps_validation.py`
- **Language**: python
- **Exports**: PerformanceTargets:
- **Purpose**: Testing utilities

### Module: validate_performance
- **Path**: `testing/validate_performance.py`
- **Language**: python
- **Exports**: PerformanceThresholds:, PerformanceResults:
- **Purpose**: Testing utilities

### Module: fault_recovery_test
- **Path**: `testing/fault_recovery_test.py`
- **Language**: python
- **Exports**: FaultInjector:, __init__
- **Purpose**: Testing utilities

### Module: performance_10k_rps
- **Path**: `testing/performance_10k_rps.py`
- **Language**: python
- **Exports**: PerformanceMetrics:
- **Purpose**: Testing utilities

### Module: e2e_test
- **Path**: `testing/e2e_test.py`
- **Language**: python
- **Exports**: E2ETestClient:, __init__, create_test_message
- **Purpose**: Testing utilities

### Module: load_test
- **Path**: `testing/load_test.py`
- **Language**: python
- **Exports**: E2EUser, __init__, create_test_message
- **Purpose**: Testing utilities

### Module: validate_horizontal_scaling
- **Path**: `testing/validate_horizontal_scaling.py`
- **Language**: python
- **Exports**: HorizontalScalingResult:
- **Purpose**: Testing utilities

### Module: validate_cache_hit_rate
- **Path**: `testing/validate_cache_hit_rate.py`
- **Language**: python
- **Exports**: CacheMetrics:, total
- **Purpose**: Testing utilities

### Module: performance_test
- **Path**: `testing/performance_test.py`
- **Language**: python
- **Exports**: PerformanceTester:, __init__
- **Purpose**: Testing utilities

---

## 🔧 Configuration

- `ruff.toml` (Configuration)
- `.pre-commit-config.yaml` (Configuration)
- `docker-compose.dev.yml` (Docker)
- `docker-compose.production.yml` (Docker)
- `audit_anchor_production.json` (Configuration)

---

## 📚 Documentation

- `README.md` - ACGS-2: Advanced Constitutional Governance System (README)
- `docs/README.md` - ACGS-2 Documentation (README)
- `docs/CLAUDE.md` - CLAUDE.md (Documentation)
- `docs/AGENTS.md` - ACGS-2 Project Guide for AI Assistants (Documentation)
- `docs/SERVICE_DEVELOPMENT_GUIDELINES.md` - ACGS-2 Service Development Guidelines (Documentation)
- `docs/multi-tenant-deployment-guide.md` - ACGS-2 Multi-Tenant Deployment Guide (Deployment Guide)
- `docs/api_reference.md` - ACGS-2 API Reference (v2.3.0) (API Documentation)
- `docs/todo.md` - ACGS-2 架构重构计划 (Documentation)
- `docs/user_guide.md` - ACGS-2 User Guide (Documentation)
- `docs/README.en.md` - ACGS-2 (README)

---

## 📝 Quick Start

1. **Setup**: Install dependencies
2. **Configure**: Update configuration files
3. **Run**: Start development server
4. **Test**: Run test suite

---

**Index Size**: ~8KB | **Last Updated**: 2026-01-03
