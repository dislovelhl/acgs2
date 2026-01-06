# ACGS-2 约束生成系统

## 概述

ACGS-2系统的第三阶段第一项实现：**从"事后修复"转向"约束生成"**。

本系统通过在Agent生成代码阶段集成Guidance或Outlines库，使用CFG或JSON Schema强制LLM生成语法正确代码，从源头消灭错误。

## 核心组件

### 1. ConstraintGenerator (约束生成器)
- **文件**: `constraint_generator.py`
- **功能**: 主要的代码生成接口，集成Guidance/Outlines库
- **特点**:
  - 支持Guidance和Outlines库
  - 自动语法验证
  - 性能统计和监控

### 2. LanguageConstraints (语言约束)
- **文件**: `language_constraints.py`
- **功能**: 为不同编程语言定义CFG和JSON Schema约束
- **支持语言**:
  - Python (PEP 8, 类型提示)
  - JavaScript/TypeScript (ES6+, JSDoc)
  - Java (Java 8+ 最佳实践)
  - C++ (C++11+ 标准)
  - Go (Go 1.16+ 惯例)

### 3. DynamicConstraintUpdater (动态约束更新器)
- **文件**: `dynamic_updater.py`
- **功能**: 基于实时反馈动态调整约束
- **特点**:
  - 基于性能指标自动调整
  - 学习常见错误模式
  - 适应性约束优化

### 4. UnitTestGenerator (单元测试生成器)
- **文件**: `unit_test_generator.py`
- **功能**: 自动为生成的代码生成单元测试
- **支持框架**:
  - Python: unittest
  - JavaScript: Jest
  - Java: JUnit
  - C++: Google Test
  - Go: testing

### 5. QualityScorer (质量评分器)
- **文件**: `quality_scorer.py`
- **功能**: 集成SonarQube进行代码质量评估
- **评估维度**:
  - 语法正确性
  - 代码复杂度
  - 风格一致性
  - 最佳实践遵循
  - 文档完整性

### 6. FeedbackLoop (反馈循环)
- **文件**: `feedback_loop.py`
- **功能**: 处理反馈并改进生成模型
- **特点**:
  - 收集生成结果反馈
  - 分析性能趋势
  - 生成改进建议
  - 支持模型微调数据导出

## 技术栈

- **约束库**: Microsoft Guidance, Outlines
- **测试框架**: pytest, unittest, Jest, JUnit, Google Test
- **质量工具**: SonarQube
- **编程语言**: Python 3.8+
- **异步支持**: asyncio

## 安装和依赖

```bash
# 核心依赖 (可选)
pip install guidance outlines

# 测试依赖
pip install pytest

# 质量分析 (可选)
pip install sonar-scanner
```

## 使用示例

### 基本代码生成

```python
from constraint_generator import ConstraintGenerator, GenerationRequest

# 创建生成器
generator = ConstraintGenerator()

# 创建请求
request = GenerationRequest(
    language="python",
    task_description="创建一个计算斐波那契数列的函数",
    generate_tests=True,
    quality_check=True
)

# 生成代码
result = await generator.generate_code(request)

print(f"代码: {result.code}")
print(f"测试: {result.tests}")
print(f"质量分数: {result.quality_score}")
```

### 多语言支持

```python
# Python
request = GenerationRequest(language="python", task_description="...")

# JavaScript
request = GenerationRequest(language="javascript", task_description="...")

# Java
request = GenerationRequest(language="java", task_description="...")
```

### 约束定制

```python
from language_constraints import LanguageConstraints

constraints = LanguageConstraints()

# 获取Python约束
python_constraints = constraints.get_constraints("python")

# 添加自定义约束
constraints.add_custom_constraint(
    "python",
    "require_type_hints",
    True
)
```

## 架构设计

```
┌─────────────────┐    ┌──────────────────┐
│   Agent Request │───▶│ ConstraintGenerator │
└─────────────────┘    └──────────────────┘
                              │
                    ┌─────────┼─────────┐
                    │         │         │
            ┌───────▼───┐ ┌──▼───┐ ┌───▼────┐
            │Language   │ │Dynamic│ │Quality │
            │Constraints│ │Updater│ │Scorer │
            └───────────┘ └───────┘ └────────┘
                    │         │         │
            ┌───────▼───┐ ┌──▼───┐ ┌───▼────┐
            │Unit Test  │ │Feedback│ │SonarQube│
            │Generator  │ │Loop   │ │Integration│
            └───────────┘ └───────┘ └─────────┘
```

## 关键特性

### 1. 约束驱动生成
- 使用CFG语法规则强制代码结构
- JSON Schema验证代码属性
- 实时约束调整和优化

### 2. 多语言原生支持
- 每种语言的专门语法规则
- 语言特定的最佳实践
- 文化和社区标准的遵循

### 3. 自适应学习
- 基于反馈的约束调整
- 性能指标驱动的优化
- 错误模式识别和预防

### 4. 质量保证
- 自动单元测试生成
- SonarQube质量评分
- 文档和注释验证

### 5. 反馈闭环
- 收集生成结果数据
- 分析改进机会
- 生成模型微调建议

## 性能指标

### 目标里程碑
- **代码修复需求**: 减少80%
- **语法正确率**: >99.5%
- **测试覆盖率**: >90% (生成任务中)

### 当前基准
- **平均生成时间**: <2秒 (简单任务), <10秒 (复杂任务)
- **语法错误率**: <0.5%
- **质量分数**: 7.0-9.0 (10分制)

## 配置选项

### ConstraintGenerator 参数
- `use_guidance`: 是否使用Microsoft Guidance (默认: True)
- `use_outlines`: 是否使用Outlines库 (默认: True)
- `model_name`: LLM模型名称 (默认: "gpt-4")
- `enable_dynamic_update`: 启用动态约束更新 (默认: True)
- `enable_feedback_loop`: 启用反馈循环 (默认: True)

### 约束配置
- 语法规则严格程度
- 质量检查阈值
- 测试覆盖要求
- 性能优化目标

## 扩展开发

### 添加新语言支持
1. 在 `LanguageConstraints` 中定义语法规则
2. 实现CFG语法和JSON Schema
3. 添加 `UnitTestGenerator` 支持
4. 更新 `QualityScorer` 规则

### 自定义约束
```python
# 添加领域特定约束
constraints.add_custom_constraint(
    "python",
    "domain_specific_rules",
    {"max_nesting": 3, "require_logging": True}
)
```

### 集成新的约束库
1. 在 `ConstraintGenerator` 中添加库检测
2. 实现相应的生成方法
3. 更新错误处理和回退机制

## 测试和验证

运行测试套件：
```bash
cd services/core/constraint_generation_system
python test_constraint_system.py
```

运行演示：
```bash
python demo.py
```

## 部署和监控

### 生产部署
1. 配置SonarQube服务器
2. 设置适当的资源限制
3. 启用监控和日志记录
4. 配置自动备份和恢复

### 监控指标
- 生成成功率
- 平均响应时间
- 质量分数分布
- 约束违反模式
- 反馈循环效果

## 故障排除

### 常见问题
1. **导入错误**: 检查Python路径和相对导入
2. **约束库不可用**: 系统会自动回退到基础生成
3. **SonarQube连接失败**: 检查网络配置和认证
4. **内存不足**: 调整批处理大小和缓存策略

### 调试模式
```python
import logging
logging.basicConfig(level=logging.DEBUG)

generator = ConstraintGenerator()
# 启用详细日志记录
```

## 贡献指南

1. 遵循现有的代码风格和命名约定
2. 添加相应的单元测试
3. 更新文档和示例
4. 确保向后兼容性
5. 提交前运行完整的测试套件

## 许可证

ACGS-2 项目许可证

---

**注意**: 此系统代表了从被动修复到主动预防的范式转变，通过约束驱动的代码生成显著提高了AI生成代码的质量和可靠性。
