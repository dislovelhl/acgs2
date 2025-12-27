# Policy Registry Service

动态宪法策略注册表服务，提供版本化存储和管理宪法原则，支持Ed25519签名验证和实时通知。

## 功能特性

- **版本化策略管理**：支持语义化版本控制的宪法策略
- **Ed25519签名验证**：使用非对称加密确保策略完整性
- **多层缓存**：Redis分布式缓存 + 本地LRU缓存
- **实时通知**：WebSocket和Kafka集成
- **A/B测试支持**：策略变更影响评估
- **GitOps集成**：ArgoCD自动化部署
- **健康检查**：完整的监控和诊断API

## 快速开始

### 本地开发

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 启动服务：
```bash
python -m app.main
```

3. 访问API文档：
```
http://localhost:8000/docs
```

### Docker部署

```bash
docker build -t policy-registry .
docker run -p 8000:8000 policy-registry
```

### Kubernetes部署

```bash
kubectl apply -f k8s/deployment.yaml
```

## API使用示例

### 创建策略

```bash
curl -X POST "http://localhost:8000/api/v1/policies" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "constitutional_ai_safety",
    "content": {
      "max_response_length": 1000,
      "allowed_topics": ["science", "technology"],
      "prohibited_content": ["harmful_instructions"]
    },
    "format": "json",
    "description": "AI安全宪法原则"
  }'
```

### 创建策略版本

```bash
curl -X POST "http://localhost:8000/api/v1/policies/{policy_id}/versions" \
  -H "Content-Type: application/json" \
  -d '{
    "content": {...},
    "version": "1.0.0",
    "private_key_b64": "...",
    "public_key_b64": "..."
  }'
```

### 获取策略内容

```bash
curl "http://localhost:8000/api/v1/policies/{policy_id}/content?client_id=user123"
```

## 架构设计

### 核心组件

- **API层**：FastAPI RESTful接口
- **业务逻辑层**：策略管理、版本控制、签名验证
- **缓存层**：Redis + 本地缓存
- **通知层**：WebSocket + Kafka
- **安全层**：Ed25519加密签名

### 数据模型

- `Policy`：策略元数据
- `PolicyVersion`：版本化内容
- `PolicySignature`：Ed25519签名
- `KeyPair`：加密密钥对

### 安全机制

1. 策略内容使用Ed25519私钥签名
2. 公钥用于客户端验证
3. HashiCorp Vault存储私钥
4. 签名包含过期时间和指纹验证

## 配置

通过环境变量配置：

```bash
POLICY_REGISTRY_REDIS_URL=redis://localhost:6379
POLICY_REGISTRY_KAFKA_BOOTSTRAP_SERVERS=localhost:9092
POLICY_REGISTRY_DEBUG=true
```

## 监控

### 健康检查端点

- `GET /health/live` - 存活检查
- `GET /health/ready` - 就绪检查
- `GET /health/details` - 详细状态

### 指标

- 策略数量和状态
- 缓存命中率
- WebSocket连接数
- 签名验证延迟

## 开发

### 项目结构

```
services/policy_registry/
├── app/
│   ├── api/v1/          # API路由
│   ├── models/          # 数据模型
│   ├── services/        # 业务服务
│   └── main.py          # 应用入口
├── config/              # 配置
├── k8s/                 # Kubernetes部署
├── tests/               # 测试
├── requirements.txt     # 依赖
├── Dockerfile          # 容器化
└── README.md           # 文档
```

### 运行测试

```bash
pytest tests/
```

## 许可证

ACGS-2项目许可证
