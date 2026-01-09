# ACGS-2（acgs2-main-1）可直接开工：PR 拆分与执行清单（中文）

- 适用仓库快照：`acgs2-main-1.zip`（解压根目录：`acgs2-main/`）
- 分析日期：2026-01-08
- 输入 ZIP SHA256：`c8df4d006b1d789ac7bbf10a471ecbd0c3cf7176dcca78e33c94a47e0c384ba4`
- 代码库规模：目录 **1,385** 个；文件 **3,816** 个；体积约 **108.5 MB**

> 说明：本清单面向“直接开工”。每个 PR 给出**目标、改动范围（精确到文件/目录）、实施步骤、验证命令、回滚策略**。优先级以 **P0（阻断/安全/合规）→ P1（高价值稳定性）→ P2（卫生与降噪）** 排序。

---

## 0. Triage 结论（先做什么）

### P0（立即处理：安全泄露/合规阻断）
1. **本地工具环境文件泄露真实密钥风险**：`/.auto-claude/.env` 中存在**非空**敏感变量（仅列变量名，不展示值）：
   - `LINEAR_API_KEY`
   - `GITHUB_TOKEN`
   - `OPENAI_API_KEY`

   该文件虽然通常应被 `.gitignore` 排除，但**出现在分享/打包的 ZIP 中**，意味着存在“以源码包/工件形式外泄”的现实风险。建议视为**已泄露**处理并立即轮换。

### P1（尽快处理：测试可靠性与门禁有效性）
2. **Secrets 检测单测仍引用历史目录**：`tests/unit/test_secrets_detection.py` 含 `sys.path.insert(... "acgs2-core")`，并且“项目根目录”推导偏差（指向 `tests/` 而非 repo root），导致测试易被跳过或在不同环境下不稳定。
3. **pre-commit 中 secrets hook 存在可绕过点**：`.pre-commit-config.yaml` 的 `check-secrets-acgs2` hook `exclude` 规则包含 `\.auto-claude/`，当**仅提交/暂存**该目录文件时，存在 hook 不执行的可能（取决于 staged files 组合）。建议移除该排除或改为“仅排除本地 env 文件”。

### P2（卫生治理）
4. **大二进制资产入库**：`docs/templates/nvidia/*.pptx`（单文件 ~44MB）等设计资产显著膨胀仓库与 clone 成本；建议 Git LFS 或外置 artifact。
5. **MLflow 运行产物目录 `mlruns/`**：体积不大（~6MB），但属于典型运行时产物，建议明确策略：忽略/外置/示例化。

---

## 1. PR 拆分总览（建议顺序）

| PR ID | 优先级 | 标题 | 主要影响面 |
|---|---|---|---|
| PR-SEC-001 | P0 | 清理/轮换 `.auto-claude/.env` 中的真实密钥，并提供可复用的本地配置模板与“干净打包”脚本 | 安全、合规、交付工件 |
| PR-SEC-002 | P1 | 加固 secrets 门禁：修正 `check-secrets-acgs2` 的 exclude，避免 `.auto-claude/` 绕过 | pre-commit / 质量门禁 |
| PR-TEST-001 | P1 | 修复 `test_secrets_detection.py` 的 repo root 推导与 `acgs2-core` 路径漂移 | 单元测试稳定性 |
| PR-REPO-001 | P2 | 大二进制与运行产物治理（PPTX/EPS/AI、`mlruns/`） | 仓库体积、开发体验 |

---

## PR-SEC-001（P0）：清理/轮换 `.auto-claude/.env` 中的真实密钥，并提供本地配置模板与“干净打包”脚本

### 目标
- 立即降低密钥泄露风险：**轮换**相关第三方密钥，并确保仓库与分发工件不再携带真实密钥。
- 将本地工具配置标准化：提供 **`.env.example`** 或 **`.env.template`**，并以文档说明如何在本地注入。
- 提供“只导出受控内容”的打包方式（避免把 ignored/untracked 文件打入源码包）。

### 改动范围（建议）
- **新增**：`.auto-claude/.env.example`（只保留键名，值留空或使用明确 placeholder）
- **新增**：`.auto-claude/README.md`（说明本地配置方式、禁入库约束、推荐用法）
- **新增**：`scripts/release/export_clean_source.sh`（或等价脚本）
  - 推荐基于 `git archive` 或 `git ls-files` 打包，确保仅包含 tracked 文件
- **可选增强**：在 `.gitignore` 中加入更显式规则（即使目录已忽略，也建议显式列出文件避免误解）
  - `/.auto-claude/.env`
- **不要提交**：`.auto-claude/.env`（真实密钥文件）

### 实施步骤
1. **安全处置（不可延后）**
   - 在相关平台上**立刻轮换/撤销**：
     - Linear：`LINEAR_API_KEY`
     - GitHub：`GITHUB_TOKEN`（或对应 OAuth/Pat）
     - OpenAI/其他：`OPENAI_API_KEY`（当前值形态类似 `sk-ant-...`，如实际用于 Anthropic/OpenAI/OpenRouter 也应一并轮换）
   - 如果该 ZIP 已发送给第三方或上传到任何共享位置：按“密钥已泄露”处理。

2. **仓库层面整改**
   - 确认 `.auto-claude/.env` 是否被 git 跟踪（若被跟踪必须移除）：
     - `git ls-files .auto-claude/.env`
     - 若有输出：`git rm --cached .auto-claude/.env`
   - 新增 `.auto-claude/.env.example`（键名齐全、值为空/placeholder）。
   - 新增 `.auto-claude/README.md`：
     - 强制说明：`.env` 仅用于本地，严禁提交；推荐用 `.env.local` + ignore。
   - 新增 `scripts/release/export_clean_source.sh`：
     - 方案 A：`git archive --format=zip -o dist/acgs2-source.zip HEAD`
     - 方案 B：`git ls-files -z | xargs -0 tar ...`（更易定制排除/包含策略）

3. **针对“ZIP 外泄”的组织流程约束**
   - 文档补充：禁止用“直接压目录”的方式分发源码；统一使用 export 脚本或 `git archive`。

### 验证方法（本地）
- 确认真实密钥不再出现于工作区（仅示例命令，输出需自行审查）：
  - `grep -R --line-number "LINEAR_API_KEY=" .auto-claude/.env || true`
  - `grep -R --line-number "OPENAI_API_KEY=" .auto-claude/.env || true`
  - `grep -R --line-number "GITHUB_TOKEN=" .auto-claude/.env || true`
- 确认 `.auto-claude/.env` 未被跟踪：
  - `git ls-files .auto-claude/.env` 应无输出
- 验证导出包不含 `.auto-claude/.env`：
  - 执行 `scripts/release/export_clean_source.sh`
  - 解压后 `find . -name ".env" -path "*auto-claude*" -print` 应无结果（或仅出现 `.env.example`）

### 回滚策略
- 该 PR 主要是新增模板/脚本与文档，回滚风险低。
- 若导出脚本引入 CI 依赖，可先以可选工具形式合入，不绑定主构建链路。

---

## PR-SEC-002（P1）：加固 secrets 门禁，修正 `check-secrets-acgs2` exclude，避免 `.auto-claude/` 绕过

### 目标
- 避免“仅提交 `.auto-claude/` 内文件时 secrets hook 不执行”的潜在绕过路径。
- 让 secrets 检测逻辑与 repo 的 ignore 策略一致：**未跟踪文件不必扫描，但一旦被暂存/跟踪必须扫描**。

### 改动范围（建议）
- `.pre-commit-config.yaml`
  - `check-secrets-acgs2` 的 `exclude` 正则：移除 `|\.auto-claude/`
  - 或改为只排除本地 env 文件：例如 `|\.auto-claude/\.env$`（保留对 `.auto-claude/project_index.json` 等被显式 unignore 文件的覆盖）
- （可选）`.secrets-allowlist.yaml`：如需降低误报，可增加“更精确的 placeholder 标记”，而不是粗暴排除目录。

### 实施步骤
1. 定位 hook 配置：
   - 文件：`.pre-commit-config.yaml`
   - hook：`id: check-secrets-acgs2`
2. 修改 exclude：
   - 推荐最小改动：将 `\.auto-claude/` 从 exclude 列表中移除
   - 或精准排除 `.env`：`\.auto-claude/\.env$`
3. 本地验证（两组场景）：
   - 场景 A：仅暂存 `.auto-claude/` 内的一个**被跟踪**文件（例如 `project_index.json`），确认 hook 会执行
   - 场景 B：暂存正常业务代码文件，确认无额外噪声/误报

### 验证命令（示例）
- `pre-commit run check-secrets-acgs2 --all-files`
- `pre-commit run check-secrets-acgs2 --hook-stage commit`
- 或模拟暂存文件后直接 `git commit --dry-run`（视你本地 git 配置）

### 回滚策略
- 若误报增多：优先通过 `.secrets-allowlist.yaml` 增加更精确的 placeholder/known-safe 值，而不是恢复“目录级排除”。

---

## PR-TEST-001（P1）：修复 `test_secrets_detection.py` 的 repo root 推导与 `acgs2-core` 路径漂移

### 目标
- 保证 secrets 检测单元测试在不同工作目录/CI 环境下稳定运行，不被误 skip。
- 移除历史遗留 `acgs2-core` 路径注入，统一以当前目录结构为准。

### 改动范围
- `tests/unit/test_secrets_detection.py`
  - 修复 `project_root` 推导：从当前的 `Path(__file__).parent.parent` 改为 repo root（建议 `Path(__file__).resolve().parents[2]`）
  - 删除或修正：`sys.path.insert(0, str(project_root / "acgs2-core"))`
  - 如需要脚本导入：将 `scripts/` 插入基于 repo root 的路径

### 建议修改示例（文字级）
- 现状（问题点）：
  - `project_root = Path(__file__).parent.parent` 实际指向 `tests/`
  - 插入不存在目录：`tests/acgs2-core`
- 建议：
  - `repo_root = Path(__file__).resolve().parents[2]`
  - `sys.path.insert(0, str(repo_root))`
  - `sys.path.insert(0, str(repo_root / "scripts"))`

### 验证命令
- `pytest -q tests/unit/test_secrets_detection.py`
- `pytest -q tests/unit/test_secrets_detection.py -k secrets`
- `make test`（如果你的环境具备依赖）

### 回滚策略
- 若测试依赖较重导致 CI 不稳定：可先将其标记为“可选/慢测”，但不建议继续 skip（会掩盖门禁问题）。

---

## PR-REPO-001（P2）：大二进制与运行产物治理（PPTX/EPS/AI、`mlruns/`）

### 目标
- 降低仓库体积与 clone/CI 成本，避免把运行产物当作源码版本化。
- 对文档模板类二进制提供可持续的存放方式（Git LFS 或外部存储）。

### 改动范围（建议）
- `docs/templates/nvidia/`（PPTX/EPS/AI）
  - 方案 A：Git LFS（推荐）
  - 方案 B：移出 repo，仅保留下载/同步脚本与校验和
- `mlruns/`
  - 若为示例：迁移到 `examples/` 并缩减；或改为生成脚本
  - 若为运行产物：加入 `.gitignore` 并从历史移除（如果曾入库）

### 验证
- `git status` 确认无运行产物被追踪
- `du -sh docs/templates/nvidia mlruns` 作为对比基线

---

## 2. 建议并行策略（最省时间）
- **一个人立即做 PR-SEC-001**（同时完成密钥轮换与模板/导出脚本）。
- **另一个人并行做 PR-TEST-001 + PR-SEC-002**（门禁与测试稳定性）。
- PR-REPO-001 可放到后续迭代窗口处理，但建议在对外发布前完成。
