# ACGS-2: Advanced Constitutional Governance System

**Constitutional Hash**: `cdd01ef066bc6cf2`
**Version**: 2.1.0

## 概述

ACGS-2 (Advanced Constitutional Governance System 2) 是一个增强型代理总线平台，具有宪法合规性、高性能消息传递、多租户隔离以及针对高风险决策的 AI 驱动审议功能。

该系统旨在为企业级 AI 应用提供安全、可控且高效的治理框架，确保所有代理行为符合预定义的宪法原则。

## 核心架构

### 1. 增强型代理总线 (Enhanced Agent Bus)
- **高性能**: 支持 Python (默认) 和 Rust (性能优化) 双后端。
- **安全性**: 基于宪法哈希验证的消息处理，支持多租户隔离。
- **灵活性**: 动态策略集成，支持 OPA (Open Policy Agent)。

### 2. 审议层 (Deliberation Layer)
- **风险评估**: 自动计算消息影响得分。
- **自适应路由**: 高影响消息 (得分 ≥ 0.8) 自动路由至审议队列。
- **多代理协作**: 集成 LLM 助手进行决策审查和共识达成。

### 3. 治理与合规
- **不可变审计**: 基于区块链技术的审计账本。
- **约束生成**: 从源头确保代码生成的语法和逻辑正确性。
- **实时监控**: 全面的系统健康检查和性能指标收集。

## 快速入门

### 环境要求
- Python 3.11+
- Redis (用于消息队列和代理注册)
- Rust (可选，用于高性能后端)

### 安装
```bash
# 安装开发依赖
pip install -e enhanced_agent_bus[dev]

# 构建 Rust 扩展 (可选)
cd enhanced_agent_bus/rust
cargo build --release
pip install -e .
```

### 运行测试
```bash
cd enhanced_agent_bus
python3 -m pytest tests/ -v
```

## 项目结构

- `enhanced_agent_bus/`: 核心消息总线实现。
- `services/`: 微服务集合（策略注册、审计、搜索等）。
- `policies/`: OPA Rego 策略文件。
- `docs/`: 详细的用户指南和研究文档。
- `scripts/`: 部署和维护脚本。

## 许可证

Copyright (c) 2025 ACGS-2 Project. All rights reserved.
