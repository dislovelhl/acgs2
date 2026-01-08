# ACGS-2 代码库风险与整改一页纸（可直接用于立项/审批）

- 适用仓库快照：`acgs2-main.zip`
- 生成日期（UTC）：2026-01-08

---

## 现状概览
ACGS-2 仓库包含核心治理服务（`src/core`）、Agent Bus、API Gateway、分析模块、以及配套的策略（OPA/Rego）、CI 工作流与安全门禁。开发 Compose（`docker-compose.dev.yml`）包含 OPA、Redis、Kafka/Zookeeper、PostgreSQL、MLflow 以及核心服务编排。

---

## 关键风险（按优先级）

### P0：敏感密钥材料入库（阻断级）
- 发现 `src/core/shared/auth/certs/sp.key` 为**未加密 RSA 私钥**（PEM 格式）。
- 该问题会直接触发 secrets 扫描/供应链审计失败，并带来密钥被复用/滥用的风险。
- 同目录存在 `sp.crt`（证书），可能被扫描规则误判为敏感文件，需明确策略。

### P0/P1：CI/工具链配置与当前结构不一致（会导致门禁失效或误失败）
- `.github/dependabot.yml`、`codecov.yml`、`.gitleaksignore` 仍引用不存在的 `acgs2-core/` 路径，导致：
  - 依赖更新工具可能“静默不工作”
  - 覆盖率归因/阈值策略不准确
  - secrets 忽略规则与实际路径不匹配（进一步加剧 P0 风险）

### P1：测试/文档存在历史路径硬编码（影响可维护性与交付速度）
- `src/core/tests/security/test_service_cors_integration.py` 直接依赖 `repo_root/acgs2-core`，在当前结构下会失败。
- `src/core/QUICKSTART.md`、`src/core/README.md` 仍引导用户 clone/cd `acgs2-core`，影响上手与对外一致性。

### P1：仓库卫生与体积控制风险
- `docs/templates/nvidia/*.pptx` 存在 40MB+ 大二进制模板文件；若不采用 LFS/外置，会持续拖慢 clone/CI。
- `mlruns/` 为典型运行产物目录，未见统一忽略策略，存在“实验产物入库”的持续风险。

---

## 建议的整改路线（分阶段交付）

### 阶段 A（立即）：安全止血 + 门禁恢复
- 移除 `sp.key`（必要时移除 `sp.crt`），并执行密钥轮换策略（生产/测试环境分别处理）。
- 修复 `.gitleaksignore` 旧路径例外；避免用 ignore 掩盖真实密钥风险。

**成功标准**：gitleaks 门禁通过；仓库 HEAD 不含私钥文件；SAML 密钥从环境/密钥管理系统注入。

### 阶段 B（短周期）：CI/工具链一致性修复
- dependabot：目录对齐到 `src/core`（以及 `src/core/enhanced_agent_bus/rust`）。
- codecov：覆盖率 paths/flags 对齐到 `src/core/**`。
- 修复 CORS 集成测试路径漂移，保证安全测试可执行。

**成功标准**：工具“可用且可信”（依赖更新/覆盖率/关键安全测试均正常运行）。

### 阶段 C（持续）：仓库卫生与开发体验提升
- 明确大二进制模板管理策略（Git LFS 或外置）。
- 将 `mlruns/` 等运行产物纳入忽略策略并清理追踪。
- 修复 Makefile/Quickstart，使新成员按文档即可运行 lint/test 与核心 compose。

**成功标准**：repo 体积增长可控、CI 更快、上手路径无历史漂移。

---

## 需要管理层/安全负责人决策的事项
1. **开发用证书是否允许入库**：建议仅允许证书（crt）且必须注明用途；私钥（key）一律禁止。
2. **大二进制模板存放策略**：Git LFS vs 外置对象存储（影响成本、审计与开发效率）。
3. **实验数据（mlruns）策略**：是否允许入库作为示例；若允许，需脱敏与体积上限。

---

## 建议输出物（对齐研发执行）
- 《PR 拆分与执行清单》（已单独提供）：按 P0→P1 顺序可直接开工。
- 变更完成后建议固化为：PR 模板 + 安全门禁 checklist（避免回归）。
