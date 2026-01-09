# ACGS-2（acgs2-main-1）代码库风险与整改一页纸（中文）

- 分析对象：`acgs2-main-1.zip`（解压根目录：`acgs2-main/`）
- 分析日期：2026-01-08
- ZIP SHA256：`c8df4d006b1d789ac7bbf10a471ecbd0c3cf7176dcca78e33c94a47e0c384ba4`
- 规模：目录 **1,385**；文件 **3,816**；约 **108.5 MB**

---

## 一、当前最关键风险（按优先级）

### P0：密钥泄露风险（需要“应急处置”）
**现象**
- 在 `/.auto-claude/.env` 中发现**非空**敏感变量（仅列变量名）：
  - `LINEAR_API_KEY`、`GITHUB_TOKEN`、`OPENAI_API_KEY`
- 该文件通常应被 `.gitignore` 排除，但它出现在共享 ZIP 中，说明存在“通过源码包/工件”外泄的风险。

**影响**
- 第三方系统账户被滥用、数据泄露、API 调用费用损失、合规审计失败（供应链/密钥管理）。

**处置建议（48 小时内完成）**
- 将相关密钥视为已泄露：**撤销/轮换**并审计访问日志。
- 在仓库提供 `.env.example` 与“干净导出源码”的脚本（`git archive`/`git ls-files`），禁止直接压目录分发。

---

### P1：质量门禁与测试可靠性（影响交付节奏）
**现象**
- `tests/unit/test_secrets_detection.py` 仍注入历史路径 `acgs2-core`，并且 repo root 推导指向 `tests/`，导致测试在不同环境下可能被跳过或不稳定。
- `.pre-commit-config.yaml` 中 `check-secrets-acgs2` 的 exclude 包含 `\.auto-claude/`，存在仅提交该目录文件时的潜在绕过路径。

**影响**
- secrets 相关的“质量门禁”在边界场景下失效；测试信号变弱，问题进入主干的概率上升。

**处置建议（本周内完成）**
- 修复测试 root 与 sys.path 注入，确保单测可在 CI 稳定执行。
- 调整 secrets hook exclude：不要目录级排除 `.auto-claude/`，改为精准排除本地 env 文件或完全依赖 staged 文件集。

---

### P2：仓库卫生与成本
**现象**
- `docs/templates/nvidia/` 存在大体积二进制（PPTX 单文件 ~44MB）。
- `mlruns/` 为运行产物目录（约 6MB），需要明确是否属于可版本化示例。

**影响**
- clone/CI 成本提升；审计噪声增加；对外发布时易夹带无关内容。

**处置建议（按发布节奏）**
- PPTX/EPS/AI：迁移 Git LFS 或外置 artifact。
- `mlruns/`：改为生成或示例化，避免运行产物入库。

---

## 二、建议整改路线图（可用于排期）

| 时间窗 | 交付物 | 负责人建议 |
|---|---|---|
| T+0～T+2 天 | 密钥轮换、`.env.example`、干净导出脚本 | 安全负责人/平台负责人 |
| T+3～T+5 天 | 修复 secrets 单测 + secrets hook exclude 加固 | 研发负责人/CI Owner |
| T+1～T+2 周 | 二进制与运行产物治理（LFS/外置/生成） | 文档/平台协作 |

---

## 三、需要管理层拍板的事项
1. **密钥管理策略**：是否统一采用 Vault/云密钥管理服务，禁止在本地 `.env` 长期保存真实密钥。
2. **二进制资产策略**：Git LFS vs 外部对象存储（含访问控制与合规要求）。
3. **源码分发方式**：统一采用 `git archive` 导出（只含受控 tracked 内容），禁止“直接压目录”。
