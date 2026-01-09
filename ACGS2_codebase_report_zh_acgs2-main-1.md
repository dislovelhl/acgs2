# ACGS-2（acgs2-main-1）代码库全面分析报告（中文）

- 分析对象：`acgs2-main-1.zip`（解压根目录：`acgs2-main/`）
- 分析日期：2026-01-08
- ZIP SHA256：`c8df4d006b1d789ac7bbf10a471ecbd0c3cf7176dcca78e33c94a47e0c384ba4`

---

## 1. 规模画像与技术栈

### 1.1 规模

- 目录数：**1,385**
- 文件数：**3,816**
- 体积：约 **108.5 MB**

### 1.2 主要语言/配置体量（文本行数估算）

> 已跳过常见构建/缓存目录（如 `node_modules/`、`target/`、`__pycache__/`、`mlruns/` 等）以及单文件 >5MB 的二进制/大文件。

- Python：约 **491,036 行**
- Markdown：约 **373,251 行**
- TypeScript：约 **40,931 行**
- YAML：约 **40,270 行**
- JSON：约 **56,212 行**
- Rego：约 **4,423 行**
- Shell：约 **15,380 行**

---

## 2. 顶层目录结构（面向快速定位）

### 2.1 仓库根目录要点

- `src/`：主要实现（含 core、frontend、agents、observability 等）
- `policies/`：策略/规则相关资产（含 Rego）
- `runtime/`：运行时策略 bundle、合规/治理相关运行资产
- `scripts/`：治理脚本、门禁脚本、工具链脚本
- `docs/`：文档与模板（含较大二进制）
- `mlruns/`：MLflow 运行产物（建议明确策略，见风险项）
- `.github/workflows/`：CI/CD、质量门禁、安全扫描、性能回归等 workflow

### 2.2 `src/` 子模块概览

`src/` 下主要模块：

- `src/core/`：核心后端与服务实现（多服务分目录）
- `src/frontend/`：前端（含 analytics-dashboard）
- `src/agents/`、`src/neural-mcp/`、`src/integration-service/`：代理/集成/MCP 相关
- `src/observability/`：可观测性（OTel/日志/指标等）
- `src/adaptive-learning/`：自适应学习与漂移监测等（与 MLflow/模型治理相关）

---

## 3. 运行时架构与本地开发启动（基于 docker-compose.dev.yml）

### 3.1 关键服务与端口

开发环境 Compose 服务（共 11 个）：

- 基础依赖：OPA、PostgreSQL、Redis、Kafka/Zookeeper、Postgres-ML、MLflow
- 业务服务：Agent Bus、API Gateway、Analytics API、Analytics Dashboard

端口映射（摘录）：

- `postgres`：${POSTGRES_PORT:-5432}:5432
- `redis`：${REDIS_PORT:-6379}:6379
- `kafka`：19092:19092
- `zookeeper`：2181:2181
- `mlflow`：${MLFLOW_PORT:-5000}:5000
- `agent-bus`：8000:8000
- `api-gateway`：8080:8080
- `analytics-api`：8082:8082
- `analytics-dashboard`：5173:5173

### 3.2 推荐的开发启动方式

- 使用仓库提供的 `.env.dev`：
  - `docker compose -f docker-compose.dev.yml --env-file .env.dev up -d`
- 单元测试/静态检查：
  - `make test`
  - `make lint`

---

## 4. Core 服务域划分（src/core/services）

`src/core/services/` 下存在多个治理域服务目录（节选）：

- `api_gateway/`：API 网关
- `audit_service/`：审计服务
- `policy_registry/`、`policy_marketplace/`：策略注册与市场化
- `tenant_management/`：租户管理
- `hitl_approvals/`：HITL 审批
- `ml_governance/`：模型治理
- `analytics-api/`、`analytics-engine/`：分析相关
- `integration_service/`：集成服务（与 `src/integration-service/` 并存，需要留意边界与归属）
- `shared/`：共享组件（含 secrets_manager 等）

---

## 5. 质量门禁与安全体系（现状评估）

### 5.1 pre-commit（本地门禁）

- 配置文件：`.pre-commit-config.yaml`
- 关键能力：
  - 格式/静态：ruff、ruff-format、mypy
  - 体积：check-added-large-files
  - 自定义 secrets 检测：`scripts/security/check_secrets_pre_commit.py`（hook id：`check-secrets-acgs2`）

### 5.2 CI 安全扫描

- 工作流：`.github/workflows/reusable-security.yml` 使用 `gitleaks/gitleaks-action@v2` 进行 secrets 扫描（面向仓库/提交历史/变更）。

> 备注：CI 扫描主要覆盖“被提交/被追踪”的内容；对本地工作区中未追踪文件（例如 `.env`）通常不覆盖，因此仍需要流程治理（例如统一用 `git archive` 导出源码包）。

---

## 6. 阻断级与高风险问题（本次快照）

### 6.1 P0：共享 ZIP 中包含真实密钥（高风险外泄）

- 位置：`/.auto-claude/.env`
- 发现：存在非空敏感变量（仅列变量名）：
  - `LINEAR_API_KEY`
  - `GITHUB_TOKEN`
  - `OPENAI_API_KEY`

**建议**：按“已泄露”执行轮换/撤销，并建立**干净导出/打包流程**（见《可直接开工 PR 清单》中的 PR-SEC-001）。

### 6.2 P1：secrets 单测路径漂移

- 文件：`tests/unit/test_secrets_detection.py`
- 问题（已修复）：在 Phase 2 中已完成 `src/core` 路径标准化。
- 状态：[FIXED] 修复了 `tests/unit/test_secrets_detection.py` 的 repo root 推导，删除了所有 `acgs2-core` 硬编码路径，确保测试在 CI/CD 环境下稳定运行。

### 6.3 P2：仓库卫生（体积与噪声）

- `docs/templates/nvidia/` 存在 ~44MB 的 PPTX 与 EPS/AI 等设计资产。
- `mlruns/` 为运行产物目录（本快照约 6MB），建议明确版本化策略。

---

## 7. 快速可执行整改建议（摘要）

- **P0**：轮换 `.auto-claude/.env` 中所有非空密钥；提交 `.env.example` 与干净导出脚本；禁止直接压目录分发源码。
- **P1**：修复 secrets 单测 root 与 sys.path；加固 pre-commit secrets hook exclude（避免绕过）。
- **P2**：二进制资产迁移 LFS/外置；治理 `mlruns/`。

---

## 8. 附录：本次静态检查

- Python 语法编译检查（`compileall`）：`src/core`、`src/acgs2`、`tests` 均通过（未发现语法级错误）。
