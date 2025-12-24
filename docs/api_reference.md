# ACGS-2 API Reference | API 参考

> **Constitutional Hash**: `cdd01ef066bc6cf2` > **Version**: 2.2.0
> **Status**: Stable
> **Last Updated**: 2025-12-24
> **Language**: EN / CN

本文档提供了 ACGS-2 核心组件和微服务的详细 API 参考。
This document provides a detailed API reference for ACGS-2 core components and microservices.

---

## 1. 概览 | Overview

### 服务基础 URL | Base URLs

| Service          | Default URL             | Description   |
| ---------------- | ----------------------- | ------------- |
| Policy Registry  | `http://localhost:8000` | 策略管理      |
| Audit Service    | `http://localhost:8084` | 审计日志      |
| Search Platform  | `http://localhost:8083` | 代码/文档搜索 |
| Retrieval System | `http://localhost:8001` | 宪法文档检索  |
| API Gateway      | `http://localhost:8010` | 统一入口      |

---

## 2. 核心总线 (Enhanced Agent Bus)

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

---

## 3. 策略注册表 API | Policy Registry API

管理宪法策略及其版本和加密签名。
Manages constitutional policies with versioning and cryptographic signatures.

### 基础路径 | Base URL: `/api/v1/policies`

#### 获取所有策略 | List All Policies

`GET /api/v1/policies/`

#### 创建策略 | Create Policy

`POST /api/v1/policies/`

#### 激活策略版本 | Activate Policy Version

`PUT /api/v1/policies/{policy_id}/activate?version={version}`

---

## 4. 审计服务 API | Audit Service API

提供基于 Merkle Tree 验证的不可篡改审计日志。
Provides immutable audit logging with Merkle tree verification.

### 基础路径 | Base URL: `/api/v1/audit`

#### 添加审计条目 | Add Audit Entry

`POST /api/v1/audit/entries`

#### 验证审计条目 | Verify Audit Entry

`POST /api/v1/audit/verify`

---

## 5. 宪法检索 API | Constitutional Retrieval API

提供基于 RAG 的宪法先例和条款检索。
Provides RAG-based document retrieval for constitutional precedents and provisions.

### 基础路径 | Base URL: `/api/v1/retrieval`

#### 搜索相似文档 | Search Similar Documents

`POST /api/v1/retrieval/search`

---

## 6. 搜索平台 API | Search Platform API

高性能代码和文档搜索。
High-performance code and document search.

### 基础路径 | Base URL: `/api/v1/search`

#### 全量搜索 | Full Search

`POST /api/v1/search`

---

## 7. 数据模型 | Data Models

### `AgentMessage`

位于 [`../enhanced_agent_bus/models.py`](../enhanced_agent_bus/models.py)。

- `message_id`: 唯一标识。
- `constitutional_hash`: 宪法哈希 (必须匹配 `cdd01ef066bc6cf2`)。
- `tenant_id`: 租户 ID。
- `impact_score`: 影响分数。
- `security_context`: 安全元数据。

---

## 8. 错误处理 | Error Handling

所有 API 均遵循标准的错误响应格式：
All APIs follow a standard error response format:

```json
{
  "status": "error",
  "errors": [
    {
      "code": "CONSTITUTIONAL_VIOLATION",
      "message": "Constitutional hash invalid"
    }
  ]
}
```

---

### 🔗 相关文档 | Related Documentation

- [项目索引 | Project Index](../PROJECT_INDEX.md)
- [架构审计 | Architecture Audit](./architecture_audit.md)
- [用户指南 | User Guides](./user-guides/README.md)
- [部署门户 | Deployment Portal](../deployment_guide.md)
