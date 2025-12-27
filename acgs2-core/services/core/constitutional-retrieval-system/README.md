# ACGS-2 宪法检索与推理系统

## 概述

宪法检索与推理系统是ACGS-2系统升级计划第三阶段第二项的核心实现。该系统将宪法文档和历史判例存入向量数据库，支持语义索引和多模态检索。在模糊决策时，通过RAG（Retrieval-Augmented Generation）检索相似判例，并集成LLM推理增强决策质量。同时添加反馈循环持续更新索引，并扩展到多Agent协作共享向量知识库。

## 技术栈

- **向量数据库**: Qdrant / Milvus
- **检索增强**: LangChain
- **大语言模型**: OpenAI API (GPT-4)
- **嵌入模型**: Hugging Face Transformers (Sentence Transformers)
- **多Agent协作**: 自定义协调器

## 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Multi-Agent    │    │   Retrieval     │    │     LLM         │
│ Coordinator     │◄──►│    Engine       │◄──►│   Reasoner      │
│                 │    │   (RAG)         │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ▲                       ▲                       ▲
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Feedback      │    │  Document       │    │  Vector         │
│    Loop         │    │ Processor       │    │ Database        │
│                 │    │                  │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 核心组件

### 1. 向量数据库管理器 (VectorDatabaseManager)

- 支持Qdrant和Milvus两种向量数据库
- 提供统一的CRUD操作接口
- 自动处理连接管理和错误恢复

### 2. 文档处理器 (DocumentProcessor)

- 处理宪法文档和历史判例
- 智能分块和语义切分
- 使用Sentence Transformers生成嵌入向量

### 3. 检索引擎 (RetrievalEngine)

- 实现RAG检索机制
- 支持语义搜索和混合搜索
- 提供先例检索和宪法条款检索

### 4. LLM推理器 (LLMReasoner)

- 集成LangChain和OpenAI GPT-4
- 基于检索上下文进行推理增强
- 提供决策解释和一致性检查

### 5. 反馈循环 (FeedbackLoop)

- 收集决策反馈和性能指标
- 自动更新和优化索引
- 持续改进系统性能

### 6. 多Agent协调器 (MultiAgentCoordinator)

- 管理多个Agent的协作
- 共享向量知识库访问
- 提供同行协助和会话管理

## 安装和配置

### 依赖项

```bash
pip install qdrant-client pymilvus langchain langchain-openai sentence-transformers
```

### 环境变量

```bash
export OPENAI_API_KEY="your-openai-api-key"
export QDRANT_URL="http://localhost:6333"  # 或Milvus配置
```

### 初始化系统

```python
from constitutional_retrieval_system import (
    VectorDatabaseManager, DocumentProcessor, RetrievalEngine,
    LLMReasoner, FeedbackLoop, MultiAgentCoordinator
)

# 初始化组件
vector_db = VectorDatabaseManager(db_type="qdrant")
doc_processor = DocumentProcessor()
retrieval_engine = RetrievalEngine(vector_db, doc_processor)
llm_reasoner = LLMReasoner(retrieval_engine)
feedback_loop = FeedbackLoop(vector_db, doc_processor, retrieval_engine)
coordinator = MultiAgentCoordinator(
    vector_db, retrieval_engine, llm_reasoner, feedback_loop
)
```

## 使用示例

### 1. 索引宪法文档

```python
# 处理宪法文档
constitution_chunks = doc_processor.process_constitutional_document(
    constitution_text,
    {"title": "中华人民共和国宪法", "doc_type": "constitution"}
)

# 索引到向量数据库
await retrieval_engine.index_documents(constitution_chunks)
```

### 2. 检索相似先例

```python
# 检索相关宪法条款
constitutional_provisions = await retrieval_engine.retrieve_constitutional_provisions(
    "国家权力行使", limit=5
)

# 检索相似判例
precedents = await retrieval_engine.retrieve_precedents_for_case(
    "政府信息公开申请被拒绝", limit=10
)
```

### 3. LLM增强推理

```python
# 基于上下文进行推理
reasoning_result = await llm_reasoner.reason_with_context(
    "如何处理政府信息公开申请？",
    retrieved_documents,
    {"legal_domain": "administrative_law"}
)

print(f"推荐决策: {reasoning_result['recommendation']}")
print(f"置信度: {reasoning_result['confidence']}")
```

### 4. 多Agent协作

```python
# 注册Agent
await coordinator.register_agent("agent_001", {
    "agent_type": "constitutional_expert",
    "capabilities": ["constitutional_analysis"],
    "permissions": ["read", "write"]
})

# 开始协作会话
session_id = await coordinator.start_collaboration_session(
    "agent_001", "分析宪法相关问题"
)

# 执行协作查询
results = await coordinator.collaborative_query(
    session_id, "立法权行使的限制"
)
```

### 5. 反馈收集

```python
# 收集决策反馈
await feedback_loop.collect_decision_feedback(
    query="测试查询",
    retrieved_documents=results["results"],
    decision=reasoning_result,
    user_feedback={"rating": 4, "comments": "准确性良好"}
)

# 更新索引
update_result = await feedback_loop.update_index_from_feedback()
```

## 测试和验证

运行完整测试套件：

```bash
python -m constitutional_retrieval_system.test_constitutional_retrieval
```

测试覆盖：
- 文档处理和向量化
- 向量数据库操作
- RAG检索功能
- LLM推理增强
- 反馈循环机制
- 多Agent协作

## 性能指标

根据系统要求，目标性能指标：

- **模糊决策检索准确率**: ≥95%
- **推理增强后决策一致性**: ≥90%

## API参考

### VectorDatabaseManager

- `connect()`: 连接数据库
- `create_collection(name, dim)`: 创建集合
- `insert_vectors(collection, vectors, payloads, ids)`: 插入向量
- `search_vectors(collection, query_vector, limit)`: 搜索向量
- `delete_vectors(collection, ids)`: 删除向量

### RetrievalEngine

- `index_documents(documents)`: 索引文档
- `retrieve_similar_documents(query, limit)`: 语义检索
- `retrieve_precedents_for_case(case_desc, limit)`: 检索先例
- `hybrid_search(query, limit)`: 混合搜索

### LLMReasoner

- `reason_with_context(query, context, criteria)`: 上下文推理
- `assess_decision_consistency(decision, history)`: 一致性评估
- `generate_decision_explanation(decision, context)`: 生成解释

### MultiAgentCoordinator

- `register_agent(agent_id, info)`: 注册Agent
- `start_collaboration_session(agent_id, purpose)`: 开始会话
- `collaborative_query(session_id, query)`: 协作查询
- `contribute_knowledge(session_id, documents)`: 贡献知识

## 部署和扩展

### Docker部署

```dockerfile
FROM python:3.9-slim

COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt

EXPOSE 8000
CMD ["python", "-m", "constitutional_retrieval_system"]
```

### 扩展配置

- **向量数据库**: 支持分布式部署
- **缓存层**: Redis用于查询缓存
- **监控**: Prometheus指标收集
- **负载均衡**: Nginx反向代理

## 许可证

本项目遵循ACGS-2项目许可证。

## 贡献

请遵循以下步骤贡献代码：

1. Fork项目
2. 创建特性分支
3. 提交更改
4. 推送分支
5. 创建Pull Request

## 联系方式

项目维护者：ACGS-2 开发团队