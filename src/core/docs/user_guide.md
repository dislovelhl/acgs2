# ACGS-2 User Guide

本指南旨在帮助开发者和系统管理员有效地使用 ACGS-2 平台。

## 1. 核心概念

### 1.1 宪法哈希 (Constitutional Hash)
ACGS-2 的核心是治理。每个消息必须携带当前的宪法哈希 `cdd01ef066bc6cf2`。如果哈希不匹配，消息将被立即拒绝，且不会进入处理流程。

### 1.2 审议机制
当消息的影响分数超过阈值（默认 0.8）时，它会自动进入审议流程。这意味着消息不会立即送达，而是需要经过 AI 专家或人工的进一步审查。

## 2. 实践示例

### 2.1 注册并发送高风险消息

```python
from enhanced_agent_bus.core import get_agent_bus
from enhanced_agent_bus.models import AgentMessage, MessageType, MessagePriority

async def high_risk_operation():
    bus = get_agent_bus()

    # 注册具有特定能力的代理
    await bus.register_agent(
        agent_id="admin_agent",
        capabilities=["financial_transfer", "policy_update"],
        tenant_id="finance_dept"
    )

    # 创建一个涉及财务转移的消息（高风险）
    message = AgentMessage(
        from_agent="admin_agent",
        to_agent="treasury_agent",
        message_type=MessageType.COMMAND,
        priority=MessagePriority.CRITICAL,
        content={
            "action": "transfer_funds",
            "amount": 50000,
            "currency": "USD",
            "tools": [{"name": "blockchain_transfer"}]
        },
        constitutional_hash="cdd01ef066bc6cf2",
        tenant_id="finance_dept"
    )

    # 发送消息
    result = await bus.send_message(message)

    # 检查是否进入审议
    if message.impact_score >= 0.8:
        print(f"消息已进入审议队列。影响分数: {message.impact_score}")
    else:
        print("消息已通过快速通道发送")
```

## 3. 边缘情况处理

### 3.1 审议超时 (Deliberation Timeout)
默认情况下，审议流程有 5-10 分钟的超时限制。如果在此时间内未达成共识或未获得批准：
- 消息状态将变为 `FAILED`。
- 系统会记录一个 `DeliberationTimeoutError`。
- **建议**: 对于关键操作，请实现重试逻辑或增加超时配置。

### 3.2 验证失败 (Validation Failure)
如果 `ValidationResult.is_valid` 为 `False`，请检查 `result.errors`。常见原因包括：
- 宪法哈希过期或错误。
- 代理未在当前租户中注册。
- 消息格式不符合架构要求。

## 4. 故障排除

| 问题 | 可能原因 | 解决方法 |
| :--- | :--- | :--- |
| `ConstitutionalHashMismatchError` | 使用了错误的哈希值 | 确保代码中使用 `cdd01ef066bc6cf2`。 |
| 消息无法送达 | 租户 ID 不匹配 | 检查发送者、接收者和消息的 `tenant_id` 是否一致。 |
| Rust 后端加载失败 | 编译环境不兼容 | 系统会自动回退到 Python 实现。如需高性能，请检查 `cargo build` 日志。 |
| Redis 连接错误 | Redis 服务未启动 | 检查 `REDIS_URL` 环境变量及服务状态。 |

## 5. 性能优化建议

1. **启用 Rust 后端**: 在高吞吐量生产环境中，务必编译并安装 Rust 扩展。
2. **批量处理**: 尽量减少频繁的小消息，使用批量处理模式。
3. **调整阈值**: 如果审议队列积压严重，可以通过 `AdaptiveRouter.set_impact_threshold()` 适当调整阈值，但需注意安全风险。
