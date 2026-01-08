# ACGS-2 可直接开工材料：PR 拆分与执行清单

- 适用仓库快照：`acgs2-main.zip`（解压根目录：`acgs2-main/`）
- 生成日期（UTC）：2026-01-08
- 目标读者：研发（含 CI/DevOps/SecOps）

---

## 0. 总体目标与“完成定义”

### 总体目标
1. **移除仓库中的敏感密钥材料**，恢复 Secrets 扫描门禁的可信度。
2. **修复配置/测试中对历史目录 `acgs2-core/` 的硬编码引用**，保证 CI、覆盖率、依赖更新工具可用。
3. **明确并固化仓库卫生策略**（生成物、二进制大文件、实验产物），降低审计/构建噪声。
4. **将关键开发入口（Makefile/Quickstart）与真实结构对齐**，提升可维护性与上手效率。

### 完成定义（DoD）
- Git 历史与工作区中不再包含未加密私钥文件（至少当前 HEAD 不包含；如需历史清理，按本清单执行）。
- GitHub Actions 安全工作流中的 **gitleaks** 扫描通过（不依赖“错误路径”的忽略规则）。
- `pytest src/core/tests/security/test_service_cors_integration.py -q` 可执行（不再因路径不存在而失败）。
- `codecov.yml` 与 `.github/dependabot.yml` 中不再引用不存在的目录。
- `.gitignore` / LFS（若启用）策略明确：`mlruns/`、本地构建产物、临时目录不入库。

---

## 1. 关键发现（用于立刻落地的证据链）

### P0：未加密私钥入库
- 文件：`src/core/shared/auth/certs/sp.key`
- 特征：PEM 头为 `-----BEGIN RSA PRIVATE KEY-----`（未加密私钥）
- 同目录：`src/core/shared/auth/certs/sp.crt`（证书，非密钥但可能触发扫描规则）
- 相关文档/脚本：
  - `src/core/shared/auth/certs/README.md`
  - `src/core/shared/auth/certs/generate_certs.py`

### P0/P1：工具配置仍引用不存在的 `acgs2-core/`
- `.github/dependabot.yml`：`directory: "/acgs2-core"`（pip/docker/cargo）
- `codecov.yml`：服务路径与 flags 指向 `acgs2-core/**`
- `.gitleaksignore`：对 `acgs2-core/shared/auth/certs/*` 的忽略条目（路径已漂移）

### P1：测试文件硬编码旧路径导致失败
- `src/core/tests/security/test_service_cors_integration.py`：
  - `repo_root / "acgs2-core"`（目录不存在）
  - 服务源码路径列表以 `acgs2-core/services/...` 开头（应改为 `src/core/services/...`）
  - inline 服务路径（integration/adaptive-learning）同样存在路径漂移

### P1：开发入口存在“可运行性”风险
- 根目录 `Makefile` 的 `setup` 目标尝试 `pip install -r requirements.txt`，但根目录缺少 `requirements.txt`（会退化为 `pip install .`，不一定满足 dev/test 工具链）。

---

## 2. 推荐 PR 顺序总览（可直接开工）

> 建议按“安全 → 门禁/一致性 → 卫生/体验”的顺序提交，避免返工与门禁阻塞。

| PR 编号 | 优先级 | 主题 | 主要目标 | 主要改动范围 |
| --- | --- | --- | --- | --- |
| PR-SEC-001 | P0 | 移除私钥 + 轮换策略落地 | 从仓库移除 `sp.key`（必要时也移除 `sp.crt`），补齐忽略/文档/运行时加载策略 | `src/core/shared/auth/certs/*`、`.gitignore`、文档 |
| PR-CI-001 | P0/P1 | 修复 `acgs2-core/` 路径漂移（CI/工具） | dependabot、codecov、gitleaksignore 对齐 `src/core` | `.github/dependabot.yml`、`codecov.yml`、`.gitleaksignore` |
| PR-TEST-001 | P1 | 修复 CORS 安全集成测试路径 | 使测试在当前目录结构下可运行 | `src/core/tests/security/test_service_cors_integration.py` |
| PR-DX-001 | P1 | 修复 Makefile/Quickstart 的上手路径 | `make setup`、Quickstart 与真实目录一致 | `Makefile`、`src/core/QUICKSTART.md`、`src/core/README.md` |
| PR-HYGIENE-001 | P1 | 仓库卫生：生成物/大文件策略 | 明确 `mlruns/`、PPTX 模板等的归属（忽略/LFS/外置） | `.gitignore`、`docs/templates/*`、README/贡献指南 |

---

## 3. PR 详细执行清单

### PR-SEC-001（P0）：移除私钥 + 轮换策略落地

#### 目标
- 将 `src/core/shared/auth/certs/sp.key` 从仓库中移除（建议同时评估是否保留 `sp.crt`）。
- 使开发与部署在**不依赖“入库私钥”**的前提下仍可配置 SAML SP 证书/密钥。
- 确保 secrets 扫描门禁可用（避免“忽略规则掩盖真实风险”）。

#### 变更建议（按最小可行集）
1. **从 Git 追踪中移除密钥文件**
   - 若已被 Git 跟踪：`git rm --cached src/core/shared/auth/certs/sp.key`
   - 工作区删除：`rm -f src/core/shared/auth/certs/sp.key`
2. **（建议）同时移除 `sp.crt` 或明确其性质**
   - 若 gitleaks 将证书也判定为敏感：建议同样移除并改为部署时生成/注入。
3. **补齐忽略与示例**
   - 在 `.gitignore` 中增加（至少）：
     - `src/core/shared/auth/certs/*.key`
     - （可选）`src/core/shared/auth/certs/*.crt`
   - 提供开发示例：`src/core/shared/auth/certs/.gitkeep` 或 `README.md` 指导生成到本地未追踪路径。
4. **运行时加载策略（不破坏现有代码结构）**
   - 优先通过环境变量/Secrets Manager 指定 `cert_file`、`key_file`（代码已有 `cert_file/key_file` 字段）。
   - 文档强调：生产必须从密钥管理系统注入，禁止入库。
5. **更新文档**
   - 更新 `src/core/shared/auth/certs/README.md`：明确“证书/私钥不入库”、生成位置、权限建议（chmod 600）。
   - 在 `docs/SECRETS_QUICK_FIX.md` 增补“私钥误入库”的处置 SOP（轮换 + 历史清理）。

#### 验证清单
- 运行（本地）：
  - `python -m compileall src/core -q`
  - `python scripts/check-secrets-pre-commit.py --verbose $(git diff --name-only --cached)`
- CI 侧：
  - 触发 `reusable-security.yml`（包含 gitleaks）应通过。

#### 风险与回滚
- 风险：开发环境若依赖固定 `sp.key` 可能在启用 SAML 时失败。
- 回滚策略：不回滚私钥入库；若需恢复开发体验，改为提供“本地生成脚本 + .env 配置”而不是提交密钥。

#### 备注（强烈建议）
- **历史清理（如该仓库已对外）**：使用 `git filter-repo` 或 BFG 清理历史中的私钥，并进行密钥轮换。

---

### PR-CI-001（P0/P1）：修复 `acgs2-core/` 路径漂移（CI/工具）

#### 目标
- `dependabot`、`codecov`、`gitleaksignore` 全部与当前结构对齐（以 `src/core` 为核心目录）。
- 避免工具“静默失效”（如 dependabot 不更新、codecov 不归因）。

#### 具体修改点
1. `.github/dependabot.yml`
   - 将：
     - `directory: "/acgs2-core"` → 建议改为 `"/"`（若需要扫描根目录 Docker/Actions）或 `"/src/core"`（若只扫描核心）。
     - `directory: "/acgs2-core/enhanced_agent_bus/rust"` → `"/src/core/enhanced_agent_bus/rust"`
2. `codecov.yml`
   - 将 `acgs2-core` 服务块中的：
     - `paths: ["acgs2-core/**"]` → `["src/core/**"]`
     - `flags: [acgs2-core]` → 统一为 `core` 或 `src-core`（避免历史命名误导）
3. `.gitleaksignore`
   - 删除或更新旧路径条目：
     - `acgs2-core/shared/auth/certs/sp.key...`
     - `acgs2-core/shared/auth/certs/sp.crt...`
   - 若保留证书文件且仍触发扫描，再按新路径添加“最小必要”的 ignore（推荐只对证书而非私钥）。

#### 验证清单
- 运行 `python -m compileall -q src/core`
- 在 PR 中检查：
  - dependabot 配置目录存在且包含对应生态文件（如 `pyproject.toml`、`Cargo.toml`、`Dockerfile`）

---

### PR-TEST-001（P1）：修复 CORS 安全集成测试路径

#### 目标
- 使 `src/core/tests/security/test_service_cors_integration.py` 不再依赖不存在的 `acgs2-core/` 目录。
- 更新其“源码路径白名单”，覆盖当前 repo 的真实服务入口。

#### 建议修改
1. 更新 `SHARED_MODULE_SERVICES`
   - 从 `acgs2-core/services/...` → `src/core/services/...`
2. 更新 `INLINE_CORS_SERVICES`
   - `integration-service/src/main.py` → `src/integration-service/integration-service/src/main.py`
   - `adaptive-learning-engine/src/main.py` → `src/adaptive-learning/adaptive-learning-engine/src/main.py`
3. 删除或修正 sys.path 注入
   - 将 `repo_root / "acgs2-core"` 改为 `repo_root`（保证 `import src.core...` 可用）
   - 或直接移除 sys.path 注入（pytest 从 repo root 执行时通常不需要）

#### 验证清单
- `pytest src/core/tests/security/test_service_cors_integration.py -q`

---

### PR-DX-001（P1）：修复 Makefile/Quickstart 的上手路径

#### 目标
- `make setup` 能安装基础 dev/test 工具链（ruff/black/mypy/pytest/pre-commit）。
- Quickstart/README 不再引导用户进入不存在的 `acgs2-core` 目录。

#### 建议修改
1. `Makefile`：
   - 将 `pip install -r requirements.txt || pip install .` 改为：
     - `pip install -e ".[dev,test]"`（或不使用 editable：`pip install ".[dev,test]"`）
   - 明确 Python 版本（3.11+）与 venv 建议。
2. `src/core/QUICKSTART.md`、`src/core/README.md`：
   - 将 clone/cd 示例与目录结构替换为当前仓库结构（例如进入 `src/core` 或从 repo root 执行 compose）。

#### 验证清单
- `make lint` / `make test`（至少不因缺失 requirements 而失败）
- `pre-commit run --all-files`（若团队要求）

---

### PR-HYGIENE-001（P1）：仓库卫生（生成物/大文件策略）

#### 目标
- 避免实验/运行产物进入版本库，降低 repo 体积与审计噪声。
- 明确大二进制（如模板 pptx）的管理方式（LFS/外置存储/Release asset）。

#### 建议策略
1. `mlruns/`：
   - 明确为运行产物：建议加入 `.gitignore` 并清理已追踪文件（如有）。
2. 大二进制模板：
   - `docs/templates/nvidia/*.pptx`（含 40MB+ 文件）建议：
     - 方案 A：Git LFS
     - 方案 B：迁移至外部对象存储，repo 中仅保留下载脚本与校验和
3. AI 工具元数据目录：
   - `.auto-claude/`、`.agent/` 等：明确哪些应入库（规则/索引）哪些应忽略（临时产物/日志）

#### 验证清单
- `git status` 无大量生成物变更
- repo 体积趋势可控（可在 PR 描述中附对比）

---

## 4. 全局验证命令（建议写入 PR 模板）

```bash
# 1) 快速语法检查（不依赖第三方包导入）
python -m compileall src/core -q

# 2) 关键测试（路径与安全配置）
pytest src/core/tests/security/test_service_cors_integration.py -q

# 3) 本地 secrets 检查（自定义脚本）
python scripts/check-secrets-pre-commit.py --verbose $(git diff --name-only --cached)
```

---

## 5. 需要产品/安全负责人拍板的决策点（避免反复）

1. **SAML SP 证书/密钥的开发策略**：是否允许提交“开发用证书（crt）”？私钥（key）一律禁止。
2. **大二进制模板管理**：Git LFS vs 外置（对象存储/Release assets）。
3. **实验产物（mlruns）**：是否允许入库作为示例数据？若允许，需要脱敏与体积上限策略。
