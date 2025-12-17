# ACGS-2 系统部署指南

## 概述

本指南提供了ACGS-2系统的完整部署说明，包括本地开发环境、Kubernetes生产部署、CI/CD管道配置以及监控栈设置。

## 系统架构

ACGS-2采用微服务架构，由以下核心组件组成：

- **Rust消息总线** - 高性能消息传递
- **审议层** - 多代理决策制定
- **约束生成系统** - 业务规则约束
- **向量检索平台** - 相似性搜索
- **审计账本** - 不可变审计记录
- **自适应治理** - 动态策略执行

## 前置要求

### 系统要求
- Docker 20.10+
- Docker Compose 2.0+
- Kubernetes 1.24+
- kubectl 1.24+
- Helm 3.0+ (可选)

### 环境要求
- Linux/macOS/Windows (WSL2)
- 至少8GB RAM
- 至少20GB可用磁盘空间

## 本地开发部署

### 使用Docker Compose

1. **克隆仓库**
   ```bash
   git clone <repository-url>
   cd acgs2
   ```

2. **构建和启动服务**
   ```bash
   docker-compose up --build
   ```

3. **验证部署**
   ```bash
   # 检查服务状态
   docker-compose ps

   # 查看日志
   docker-compose logs -f

   # 运行健康检查
   curl http://localhost:8000/health
   ```

4. **停止服务**
   ```bash
   docker-compose down
   ```

### 开发环境配置

- **端口映射**:
  - Rust消息总线: 8080
  - 审议层: 8081
  - 约束生成: 8082
  - 向量搜索: 8083
  - 审计账本: 8084
  - 自适应治理: 8000

## Kubernetes生产部署

### 命名空间创建

```bash
kubectl apply -f k8s/namespace.yml
```

### 部署应用服务

1. **创建ConfigMaps和Secrets** (如需要)

2. **部署服务**
   ```bash
   kubectl apply -f k8s/deployment.yml
   kubectl apply -f k8s/service.yml
   ```

3. **验证部署**
   ```bash
   # 检查Pod状态
   kubectl get pods -n acgs2

   # 检查服务状态
   kubectl get services -n acgs2

   # 查看日志
   kubectl logs -f deployment/rust-message-bus -n acgs2
   ```

### 部署监控栈

1. **创建监控命名空间**
   ```bash
   kubectl create namespace acgs2-monitoring
   ```

2. **部署ELK栈**
   ```bash
   kubectl apply -f k8s/elk-elasticsearch-deployment.yml
   kubectl apply -f k8s/elk-logstash-deployment.yml
   kubectl apply -f k8s/elk-kibana-deployment.yml
   ```

3. **部署Prometheus栈**
   ```bash
   kubectl apply -f k8s/prometheus-deployment.yml
   kubectl apply -f k8s/alertmanager-deployment.yml
   kubectl apply -f k8s/node-exporter-deployment.yml
   kubectl apply -f k8s/redis-exporter-deployment.yml
   ```

4. **导入Kibana仪表板**
   ```bash
   # 通过Kibana UI导入 monitoring/kibana/acgs2-dashboard.ndjson
   ```

## CI/CD部署

### Jenkins管道

1. **配置Jenkins**
   - 安装Kubernetes插件
   - 配置Docker registry凭据
   - 设置kubeconfig凭据

2. **运行管道**
   ```bash
   # Jenkinsfile已配置，支持多环境部署
   # 参数:
   # - ENVIRONMENT: dev/staging/prod
   # - RUN_TESTS: true/false
   # - DEPLOY: true/false
   ```

### GitLab CI

1. **配置变量**
   ```yaml
   # 在GitLab项目设置中配置以下变量:
   # DOCKER_REGISTRY, KUBECONFIG, GCLOUD_SERVICE_KEY等
   ```

2. **部署到不同环境**
   - **开发环境**: 合并到develop分支自动触发
   - **暂存环境**: 合并到main分支自动触发
   - **生产环境**: 标签推送手动触发

## 蓝绿部署策略

### 部署新版本

1. **部署到绿色环境**
   ```bash
   ./scripts/blue-green-deploy.sh <new-image-tag>
   ```

2. **运行测试**
   ```bash
   ./scripts/health-check.sh adaptive-governance-green-service
   ```

3. **切换流量**
   ```bash
   ./scripts/blue-green-switch.sh 100  # 切换100%流量
   ```

4. **监控和验证**
   - 观察系统指标
   - 运行端到端测试
   - 验证业务功能

### 回滚策略

如果需要回滚到蓝色环境：

```bash
./scripts/blue-green-rollback.sh
```

## 监控和日志

### 访问监控界面

- **Kibana**: http://kibana.acgs2-monitoring.svc.cluster.local:5601
- **Prometheus**: http://prometheus.acgs2-monitoring.svc.cluster.local:9090
- **Alertmanager**: http://alertmanager.acgs2-monitoring.svc.cluster.local:9093

### 健康检查端点

- **整体健康**: `GET /health`
- **服务健康**: `GET /health/{service-name}`
- **就绪检查**: `GET /ready`
- **活性检查**: `GET /live`

### 告警配置

系统配置了以下告警：
- CPU/内存使用率过高
- 服务不可用
- 响应时间过长
- 磁盘空间不足
- Redis缓存命中率低

## 测试和验证

### 运行测试套件

```bash
# 端到端测试
python -m pytest testing/e2e_test.py -v

# 性能测试
python testing/performance_test.py

# 负载测试
locust -f testing/load_test.py --host http://your-host

# 故障恢复测试
python -m pytest testing/fault_recovery_test.py -v
```

### 验证检查清单

- [ ] 所有Pod运行正常
- [ ] 服务可以相互通信
- [ ] 健康检查端点返回200
- [ ] 监控指标正常收集
- [ ] 日志正确转发到ELK
- [ ] CI/CD管道成功运行
- [ ] 蓝绿部署测试通过

## 故障排除

### 常见问题

1. **Pod无法启动**
   ```bash
   kubectl describe pod <pod-name> -n acgs2
   kubectl logs <pod-name> -n acgs2
   ```

2. **服务无法访问**
   ```bash
   kubectl get endpoints -n acgs2
   kubectl describe service <service-name> -n acgs2
   ```

3. **镜像拉取失败**
   - 检查Docker registry凭据
   - 验证镜像标签是否存在

4. **监控数据缺失**
   ```bash
   kubectl logs -f deployment/prometheus -n acgs2-monitoring
   kubectl get pods -n acgs2-monitoring
   ```

### 日志收集

```bash
# 查看应用日志
kubectl logs -f deployment/<service-name> -n acgs2

# 查看监控栈日志
kubectl logs -f deployment/elasticsearch -n acgs2-monitoring
kubectl logs -f deployment/logstash -n acgs2-monitoring
```

## 安全考虑

- 为所有服务配置适当的资源限制
- 使用Kubernetes网络策略控制流量
- 定期更新Docker镜像
- 监控安全漏洞
- 配置适当的RBAC权限

## 性能优化

- 根据负载调整Pod副本数
- 配置适当的资源请求和限制
- 使用持久卷优化存储性能
- 配置适当的缓存策略
- 监控和调整JVM/应用性能

## 备份和恢复

- 定期备份Elasticsearch数据
- 配置持久卷快照
- 测试恢复过程
- 记录备份和恢复时间

---

*最后更新: 2025-12-17*
*版本: 1.0*