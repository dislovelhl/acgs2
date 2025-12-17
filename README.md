# ACGS-2: 高级宪法治理系统 (Advanced Constitutional Governance System)

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](#)
[![Coverage](https://img.shields.io/badge/coverage-80%2B%25-brightgreen.svg)](#)
[![Constitutional Hash](https://img.shields.io/badge/constitutional--hash-cdd01ef066bc6cf2-orange.svg)](#)

ACGS-2 是一个专为企业级 AI 代理设计的增强型代理总线平台。它集成了宪法合规性验证、高性能消息传递、多租户隔离以及 AI 驱动的高风险决策审议功能，确保 AI 代理的行为始终符合预定义的治理原则。

---

## 📖 关于项目

在复杂的 AI 生态系统中，确保多个自主代理之间的协作既高效又合规是一项重大挑战。**ACGS-2** 通过引入“宪法治理”概念解决了这一问题：

- **合规性鸿沟**: 传统的代理通信缺乏统一的治理框架。ACGS-2 通过强制性的宪法哈希验证确保每条消息都符合治理标准。
- **性能瓶颈**: 针对高吞吐量场景，ACGS-2 提供 Rust 编写的高性能后端。
- **风险控制**: 引入审议层（Deliberation Layer），对高影响决策进行自动识别并路由至 AI/人工审查队列。

### 核心价值
- **安全性**: 物理级多租户隔离与不可篡改的审计账本。
- **透明度**: 每一项决策及其背后的治理逻辑均可追溯。
- **灵活性**: 支持动态策略加载（基于 OPA）和自适应风险阈值调整。

---

## 🖼️ 系统架构

![ACGS-2 Architecture Placeholder](https://via.placeholder.com/800x400?text=ACGS-2+System+Architecture)

---

## ✨ 关键特性

| 类别 | 特性 | 描述 |
| :--- | :--- | :--- |
| **核心总线** | 高性能通信 | 支持 Python (默认) 和 Rust (10-100x 加速) 双后端。 |
| | 宪法验证 | 所有操作必须携带 \`constitutional_hash="cdd01ef066bc6cf2"\`。 |
| **治理层** | 审议队列 | 影响得分 ≥0.8 的消息自动进入审议流程。 |
| | 动态策略 | 集成 Open Policy Agent (OPA) 实现细粒度访问控制。 |
| **安全审计** | 多租户隔离 | 基于 \`tenant_id\` 的消息和资源严格隔离。 |
| | 区块链审计 | 关键决策记录在基于 Merkle Tree 的不可变账本中。 |
| **运维监控** | 蓝绿部署 | 支持 Kubernetes 零停机更新与快速回滚。 |
| | 全栈监控 | 集成 Prometheus 指标与 ELK 日志分析。 |

---

## 🛠️ 技术栈

- **语言**: [Python 3.11+](https://python.org), [Rust](https://rust-lang.org)
- **消息/存储**: [Redis](https://redis.io)
- **策略引擎**: [Open Policy Agent (OPA)](https://www.openpolicyagent.org/)
- **基础设施**: [Docker](https://docker.com), [Kubernetes](https://kubernetes.io)
- **监控**: [Prometheus](https://prometheus.io), [Grafana](https://grafana.com), [ELK Stack](https://www.elastic.co/elastic-stack)
- **安全**: [HashiCorp Vault](https://www.vaultproject.io/)

---

## 🚀 快速入门

### 前置条件

- Python 3.11 或更高版本
- Redis 6.2+
- Rust 工具链 (可选，用于构建高性能扩展)
- Docker & Docker Compose (推荐)

### 安装步骤

1. **克隆仓库**
   \`\`\`bash
   git clone https://github.com/your-org/acgs2.git
   cd acgs2
   \`\`\`

2. **安装 Python 依赖**
   \`\`\`bash
   pip install -e enhanced_agent_bus[dev]
   \`\`\`

3. **构建 Rust 扩展 (可选)**
   \`\`\`bash
   cd enhanced_agent_bus/rust
   cargo build --release
   pip install -e .
   cd ../..
   \`\`\`

4. **启动基础服务**
   \`\`\`bash
   docker-compose up -d redis opa
   \`\`\`

---

## 💻 使用示例

### 基础消息发送 (带宪法验证)

\`\`\`python
from enhanced_agent_bus.core import AgentBus
from enhanced_agent_bus.models import AgentMessage, CONSTITUTIONAL_HASH

async def send_governed_message():
    bus = AgentBus(tenant_id="tenant_alpha")
    await bus.connect()

    message = AgentMessage(
        sender_id="agent_001",
        receiver_id="agent_002",
        content={"action": "update_config", "value": 42},
        constitutional_hash=CONSTITUTIONAL_HASH  # 必须匹配 cdd01ef066bc6cf2
    )

    result = await bus.send(message)
    print(f"Message sent: {result.message_id}, Status: {result.status}")

    await bus.disconnect()
\`\`\`

### 策略评估示例

\`\`\`bash
# 使用 CLI 工具检查宪法合规性
python -m enhanced_agent_bus.tools.validate_hash --hash cdd01ef066bc6cf2
\`\`\`

---

## ⚙️ 配置指南

系统支持通过环境变量进行配置。主要变量如下：

| 变量名 | 默认值 | 描述 |
| :--- | :--- | :--- |
| \`REDIS_URL\` | \`redis://localhost:6379/0\` | Redis 连接字符串 |
| \`OPA_URL\` | \`http://localhost:8181\` | OPA 服务地址 |
| \`LOG_LEVEL\` | \`INFO\` | 日志级别 (DEBUG, INFO, WARNING, ERROR) |
| \`VAULT_ADDR\` | \`http://localhost:8200\` | HashiCorp Vault 地址 |
| \`TEST_WITH_RUST\` | \`0\` | 是否在测试中使用 Rust 后端 (1=是, 0=否) |

---

## 🗺️ 路线图

- [x] **Phase 1**: 核心代理总线与 Python 后端实现。
- [x] **Phase 2**: Rust 性能优化扩展。
- [x] **Phase 3**: AI 驱动的审议层与影响评分系统。
- [-] **Phase 4**: 跨链审计集成 (进行中)。
- [ ] **Phase 5**: 零知识证明 (ZKP) 隐私保护通信。

---

## 🤝 贡献指南

我们欢迎所有形式的贡献！请遵循以下步骤：

1. Fork 本仓库。
2. 创建特性分支 (\`git checkout -b feature/AmazingFeature\`)。
3. 提交更改 (\`git commit -m 'Add some AmazingFeature'\`)。
4. 确保测试通过 (\`pytest\`)。
5. 推送到分支 (\`git push origin feature/AmazingFeature\`)。
6. 开启一个 Pull Request。

请参阅 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详细的代码规范。

---

## ❓ 常见问题 (FAQ)

**Q: 为什么我的消息被拒绝了？**
A: 请检查 \`constitutional_hash\` 是否正确。ACGS-2 要求所有操作必须匹配当前的宪法哈希 \`cdd01ef066bc6cf2\`。

**Q: 如何切换到 Rust 后端？**
A: 确保已安装 Rust 扩展，并在初始化 \`AgentBus\` 时设置 \`backend="rust"\`。

---

## 📄 许可证

本项目采用 MIT 许可证 - 详情请参阅 [LICENSE](LICENSE) 文件。

---

## 🙏 鸣谢

- 感谢 [Open Policy Agent](https://www.openpolicyagent.org/) 提供的强大策略引擎。
- 感谢所有参与 ACGS-2 宪法框架设计的治理专家。

---
*Constitutional Hash: \`cdd01ef066bc6cf2\`*
