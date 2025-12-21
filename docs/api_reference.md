# ACGS-2 API Reference

> **Constitutional Hash**: `cdd01ef066bc6cf2`
> **Version**: 2.1.0
> **Status**: Stable
> **Last Updated**: 2025-12-20
> **Language**: CN

本文档提供了 ACGS-2 核心组件的详细 API 参考。

## 核心总线 (Enhanced Agent Bus)

### `EnhancedAgentBus` 类

位于 [`../enhanced_agent_bus/core.py`](../enhanced_agent_bus/core.py)。

#### `__init__(self, redis_url: str = DEFAULT_REDIS_URL, use_dynamic_policy: bool = False, policy_fail_closed: bool = False, use_kafka: bool = False, kafka_bootstrap_servers: str = "localhost:9092")`
初始化增强型代理总线。
- `redis_url`: Redis 连接字符串。
- `use_dynamic_policy`: 是否使用动态策略注册表。
- `policy_fail_closed`: 动态策略注册表失败时是否执行 fail-closed。
- `use_kafka`: 是否使用 Kafka 作为后端。

#### `async start(self) -> None`
启动总线服务，初始化连接和指标。

#### `async stop(self) -> None`
优雅地停止总线服务。

#### `async register_agent(self, agent_id: str, agent_type: str = "default", capabilities: List[str] = None, tenant_id: str = None) -> bool`
注册一个代理。
- `tenant_id`: 用于多租户隔离的关键标识。

#### `async send_message(self, message: AgentMessage) -> ValidationResult`
发送消息。在排队前会进行宪法哈希验证。

#### `async receive_message(self, timeout: float = 1.0) -> Optional[AgentMessage]`
从总线接收消息。

#### `async broadcast_message(self, message: AgentMessage) -> Dict[str, ValidationResult]`
在同一租户内广播消息。**严格执行租户隔离**。

---

## 消息处理器 (Message Processor)

### `MessageProcessor` 类

#### `async process(self, message: AgentMessage) -> ValidationResult`
处理消息，包括验证和执行注册的处理程序。支持 Rust 后端加速。

#### `register_handler(self, message_type: MessageType, handler: Callable) -> None`
为特定消息类型注册回调函数。

---

## OPA 客户端 (OPA Client)

### `OPAClient` 类

位于 [`../enhanced_agent_bus/opa_client.py`](../enhanced_agent_bus/opa_client.py)。

#### `__init__(self, opa_url: str = "http://localhost:8181", mode: str = "http", timeout: float = 5.0, cache_ttl: int = 300, enable_cache: bool = True, redis_url: str = None, fail_closed: bool = True)`
初始化 OPA 客户端。
- `fail_closed`: OPA 评估错误或不可用时是否拒绝请求。`True` 表示拒绝 (fail-closed)，`False` 表示允许 (fail-open)。

---

## 策略注册表客户端 (Policy Registry Client)

### `PolicyRegistryClient` 类

位于 [`../enhanced_agent_bus/policy_client.py`](../enhanced_agent_bus/policy_client.py)。

#### `__init__(self, registry_url: str = None, api_key: str = None, timeout: float = 5.0, cache_ttl: int = 300, fail_closed: bool = False)`
初始化策略注册表客户端。
- `fail_closed`: 策略注册表网络/解析错误时是否拒绝消息。`True` 表示拒绝 (fail-closed)，`False` 表示允许并记录警告。

---

## 审议层 (Deliberation Layer)

### `ImpactScorer` 类

位于 [`../enhanced_agent_bus/deliberation_layer/impact_scorer.py`](../enhanced_agent_bus/deliberation_layer/impact_scorer.py)。

#### `calculate_impact_score(self, message_content: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> float`
计算消息的影响分数 (0.0 - 1.0)。
- 维度包括：语义分析 (BERT)、权限要求、请求频率、历史上下文。

### `AdaptiveRouter` 类

位于 [`../enhanced_agent_bus/deliberation_layer/adaptive_router.py`](../enhanced_agent_bus/deliberation_layer/adaptive_router.py)。

#### `async route_message(self, message: AgentMessage, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]`
根据影响分数路由消息。
- **快速路径 (Fast Path)**: 分数 < 阈值 (默认 0.8)。
- **审议路径 (Deliberation Path)**: 分数 >= 阈值。

#### `async update_performance_feedback(self, message_id: str, actual_outcome: str, processing_time: float, feedback_score: float = None)`
提供反馈以供路由算法学习和调整阈值。

---

## 审计服务 (Audit Service)

### `AuditClient` 类

位于 [`../enhanced_agent_bus/audit_client.py`](../enhanced_agent_bus/audit_client.py)。

#### `__init__(self, audit_url: str = "http://localhost:8084", timeout: float = 2.0)`
初始化审计客户端。

#### `async log_validation(self, message_id: str, result: ValidationResult) -> bool`
将宪法验证结果记录到不可篡改的账本中。

#### `async log_policy_change(self, policy_id: str, change_type: str, details: Dict[str, Any]) -> bool`
记录策略变更信息。

---

## 数据模型 (Models)

### `AgentMessage`

位于 [`../enhanced_agent_bus/models.py`](../enhanced_agent_bus/models.py)。

- `message_id`: 唯一标识。
- `constitutional_hash`: 宪法哈希 (必须匹配 `cdd01ef066bc6cf2`)。
- `tenant_id`: 租户 ID。
- `impact_score`: 影响分数 (由系统自动填充或手动指定)。
- `security_context`: 包含策略版本等安全元数据。

---
### 🔗 Related Documentation
- [Project Index](../PROJECT_INDEX.md)
- [Architecture Audit](./architecture_audit.md)
- [Summary Index](./SUMMARY.md)
- [Deployment Portal](../deployment_guide.md)
