# ACGS-2 架构重构计划

## 第一阶段：清理与统一 (Cleanup & Unification)
- [ ] **清理冗余核心实现**：
  - 分析 `core_legacy.py`, `core_rust.py`, `core_updated.py` 与 `core.py` 的差异。
  - 将所有必要功能合并到 `core.py`。
  - 删除冗余文件。
- [ ] **统一数据模型**：
  - 在 `models.py` 中合并 `Priority` 和 `MessagePriority`。
  - 确保 `AgentMessage` 使用强类型。
  - 将 `CONSTITUTIONAL_HASH` 移动到 `shared/constants.py`。
- [ ] **消除跨服务模型重复**：
  - 让 `services/audit_service/core/audit_ledger.py` 引用 `enhanced_agent_bus/models.py`。

## 第二阶段：解耦与依赖注入 (Decoupling & DI)
- [ ] **重构 EnhancedAgentBus**：
  - 引入 `AgentRegistry` 接口和 `RedisAgentRegistry` 实现。
  - 引入 `MessageRouter` 接口。
  - 使用构造函数注入依赖项。
- [ ] **重构 DeliberationLayer**：
  - 将 `ImpactScorer`, `AdaptiveRouter` 等作为依赖项注入。
  - 拆分 `process_message` 方法，遵循单一职责原则。
- [ ] **重构 MessageProcessor**：
  - 使用策略模式处理 Rust/Dynamic/Python 验证逻辑。

## 第三阶段：性能与扩展性 (Performance & Scalability)
- [ ] **分布式代理注册**：
  - 实现基于 Redis 的代理注册中心，支持多实例部署。
- [ ] **异步化审计操作**：
  - 将 `AuditLedger` 中的哈希计算和 Merkle Tree 操作改为异步。
  - 引入任务队列处理耗时的区块链提交操作。

## 第四阶段：配置与安全 (Configuration & Security)
- [ ] **统一配置管理**：
  - 使用 `pydantic-settings` 管理所有服务的配置。
  - 移除所有硬编码的敏感信息。
- [ ] **增强 API 安全性**：
  - 修复 `policy_registry` 中的 CORS 配置。
  - 为内部服务调用添加认证机制。

---
