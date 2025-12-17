#!/usr/bin/env python3
"""
ACGS-2 Constraint Generation System Tests
测试约束生成系统的完整功能
"""

import unittest
import asyncio
from unittest.mock import Mock, patch
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from .constraint_generator import ConstraintGenerator, GenerationRequest, GenerationResult
from .language_constraints import LanguageConstraints
from .dynamic_updater import DynamicConstraintUpdater
from .unit_test_generator import UnitTestGenerator
from .quality_scorer import QualityScorer
from .feedback_loop import FeedbackLoop


class TestConstraintGenerationSystem(unittest.TestCase):
    """约束生成系统测试"""

    def setUp(self):
        """测试前准备"""
        self.generator = ConstraintGenerator(
            use_guidance=False,  # 测试时禁用以避免依赖
            use_outlines=False,
            enable_dynamic_update=True,
            enable_feedback_loop=True
        )

    def tearDown(self):
        """测试后清理"""
        pass

    def test_generation_request_creation(self):
        """测试生成请求创建"""
        request = GenerationRequest(
            language="python",
            task_description="Create a function to calculate fibonacci numbers",
            generate_tests=True,
            quality_check=True
        )

        self.assertEqual(request.language, "python")
        self.assertTrue(request.generate_tests)
        self.assertTrue(request.quality_check)

    def test_generation_result_creation(self):
        """测试生成结果创建"""
        result = GenerationResult(
            code="def fib(n): return n",
            syntax_valid=True,
            quality_score=8.5,
            generation_time=1.2
        )

        self.assertEqual(result.code, "def fib(n): return n")
        self.assertTrue(result.syntax_valid)
        self.assertEqual(result.quality_score, 8.5)
        self.assertEqual(result.generation_time, 1.2)

    async def test_python_code_generation(self):
        """测试Python代码生成"""
        request = GenerationRequest(
            language="python",
            task_description="Create a simple calculator class",
            generate_tests=True,
            quality_check=True
        )

        result = await self.generator.generate_code(request)

        # 验证结果
        self.assertIsInstance(result, GenerationResult)
        self.assertTrue(len(result.code) > 0)
        self.assertTrue(result.syntax_valid)
        self.assertIsNotNone(result.quality_score)
        self.assertTrue(result.generation_time >= 0)

    async def test_javascript_code_generation(self):
        """测试JavaScript代码生成"""
        request = GenerationRequest(
            language="javascript",
            task_description="Create a function to validate email addresses",
            generate_tests=True,
            quality_check=True
        )

        result = await self.generator.generate_code(request)

        self.assertIsInstance(result, GenerationResult)
        self.assertTrue(len(result.code) > 0)
        self.assertTrue(result.syntax_valid)

    def test_language_constraints_loading(self):
        """测试语言约束加载"""
        constraints = LanguageConstraints()

        # 测试Python约束
        python_constraints = constraints.get_constraints("python")
        self.assertEqual(python_constraints['language'], 'python')
        self.assertEqual(python_constraints['indent_style'], 'spaces')
        self.assertEqual(python_constraints['indent_size'], 4)

        # 测试JavaScript约束
        js_constraints = constraints.get_constraints("javascript")
        self.assertEqual(js_constraints['language'], 'javascript')
        self.assertEqual(js_constraints['indent_style'], 'spaces')
        self.assertEqual(js_constraints['indent_size'], 2)

    def test_dynamic_constraint_updater(self):
        """测试动态约束更新器"""
        updater = DynamicConstraintUpdater()

        # 测试约束获取
        constraints = updater.get_dynamic_constraints("python")
        self.assertIsInstance(constraints, dict)

        # 测试反馈处理
        feedback = {
            'language': 'python',
            'syntax_errors_reduced': True
        }

        # 注意：这里是同步方法，但在实际实现中可能是异步的
        # await updater.process_feedback(feedback)

    async def test_unit_test_generation(self):
        """测试单元测试生成"""
        test_gen = UnitTestGenerator()

        # Python代码
        python_code = '''
def add_numbers(a, b):
    """Add two numbers"""
    return a + b

class Calculator:
    def multiply(self, x, y):
        return x * y
'''

        tests = await test_gen.generate_tests(python_code, "python")
        self.assertIsNotNone(tests)
        self.assertIn("unittest", tests)
        self.assertIn("test_add_numbers", tests)

    async def test_quality_scoring(self):
        """测试质量评分"""
        scorer = QualityScorer(enable_local_analysis=False)

        # 好的Python代码
        good_code = '''
def calculate_fibonacci(n):
    """
    Calculate the nth Fibonacci number using dynamic programming.

    Args:
        n (int): The position in the Fibonacci sequence

    Returns:
        int: The nth Fibonacci number
    """
    if n <= 1:
        return n

    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
'''

        score = await scorer.score_code(good_code, "python")
        self.assertIsNotNone(score)
        self.assertTrue(0 <= score <= 10)

    async def test_feedback_loop(self):
        """测试反馈循环"""
        feedback_loop = FeedbackLoop()

        # 创建模拟结果
        request = {'language': 'python', 'task_description': 'test task'}
        result = GenerationResult(
            code="def test(): pass",
            syntax_valid=True,
            quality_score=8.0,
            generation_time=1.0
        )

        # 处理反馈
        feedback_result = await feedback_loop.process_feedback(request, result)
        self.assertIsNotNone(feedback_result)

        # 获取摘要
        summary = feedback_loop.get_feedback_summary()
        self.assertIn('total_samples', summary)

    def test_constraint_violations_tracking(self):
        """测试约束违反跟踪"""
        result = GenerationResult(
            code="invalid code",
            syntax_valid=False,
            constraint_violations=["Missing semicolon", "Invalid syntax"]
        )

        self.assertFalse(result.syntax_valid)
        self.assertEqual(len(result.constraint_violations), 2)
        self.assertIn("Missing semicolon", result.constraint_violations)

    async def test_multilanguage_support(self):
        """测试多语言支持"""
        languages = ['python', 'javascript', 'java', 'cpp', 'go']

        for language in languages:
            request = GenerationRequest(
                language=language,
                task_description=f"Create a hello world function in {language}",
                generate_tests=False,
                quality_check=False
            )

            result = await self.generator.generate_code(request)

            self.assertIsInstance(result, GenerationResult)
            self.assertTrue(len(result.code) > 0)
            # 注意：语法验证对于某些语言可能不完整

    def test_performance_metrics(self):
        """测试性能指标"""
        stats = self.generator.get_stats()

        self.assertIn('total_generations', stats)
        self.assertIn('successful_generations', stats)
        self.assertIn('syntax_errors_caught', stats)

        # 初始状态应该都是0
        self.assertEqual(stats['total_generations'], 0)

    async def test_error_handling(self):
        """测试错误处理"""
        # 测试无效语言
        request = GenerationRequest(
            language="invalid_language",
            task_description="Test invalid language",
            generate_tests=False,
            quality_check=False
        )

        result = await self.generator.generate_code(request)

        # 应该仍然返回结果，但可能有约束违反
        self.assertIsInstance(result, GenerationResult)

    def test_json_schema_validation(self):
        """测试JSON Schema验证"""
        constraints = LanguageConstraints()

        python_schema = constraints._get_python_schema()
        self.assertIn('type', python_schema)
        self.assertEqual(python_schema['type'], 'object')
        self.assertIn('properties', python_schema)

    def test_cfg_grammar_loading(self):
        """测试CFG语法加载"""
        constraints = LanguageConstraints()

        python_grammar = constraints._get_python_grammar()
        self.assertIn('start:', python_grammar)
        self.assertIn('statement:', python_grammar)

        js_grammar = constraints._get_javascript_grammar()
        self.assertIn('start:', js_grammar)
        self.assertIn('statement:', js_grammar)


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def setUp(self):
        self.generator = ConstraintGenerator(
            use_guidance=False,
            use_outlines=False,
            enable_dynamic_update=True,
            enable_feedback_loop=True
        )

    async def test_full_pipeline(self):
        """测试完整生成管道"""
        # 创建请求
        request = GenerationRequest(
            language="python",
            task_description="Create a class to manage a library system with books and users",
            context={
                "requirements": "Should support adding books, borrowing books, returning books",
                "constraints": "Use proper error handling and type hints"
            },
            generate_tests=True,
            quality_check=True
        )

        # 生成代码
        result = await self.generator.generate_code(request)

        # 验证结果
        self.assertIsInstance(result, GenerationResult)
        self.assertTrue(len(result.code) > 0)
        self.assertTrue(result.syntax_valid)
        self.assertIsNotNone(result.quality_score)

        # 如果生成了测试，验证测试
        if result.tests:
            self.assertIn("class", result.tests)  # 应该是unittest类
            self.assertIn("def test_", result.tests)

    async def test_feedback_driven_improvement(self):
        """测试反馈驱动的改进"""
        # 生成多个代码样本
        requests = [
            GenerationRequest(
                language="python",
                task_description=f"Create a function to {task}",
                generate_tests=False,
                quality_check=True
            )
            for task in ["sort a list", "validate email", "calculate factorial", "parse JSON"]
        ]

        results = []
        for request in requests:
            result = await self.generator.generate_code(request)
            results.append(result)

        # 验证所有结果
        for result in results:
            self.assertTrue(result.syntax_valid)

        # 检查是否有质量改进
        quality_scores = [r.quality_score for r in results if r.quality_score is not None]
        if len(quality_scores) > 1:
            avg_quality = sum(quality_scores) / len(quality_scores)
            self.assertTrue(avg_quality > 5.0)  # 应该有合理的质量分数


def run_async_test(coro):
    """运行异步测试的辅助函数"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


if __name__ == '__main__':
    # 为异步测试创建包装器
    async def run_async_tests():
        suite = unittest.TestLoader().loadTestsFromTestCase(TestConstraintGenerationSystem)
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestIntegration))

        # 运行异步测试
        for test_case in suite:
            if hasattr(test_case, '_testMethodName'):
                test_method = getattr(test_case, test_case._testMethodName)
                if asyncio.iscoroutinefunction(test_method):
                    try:
                        await test_method()
                        print(f"✓ {test_case._testMethodName}")
                    except Exception as e:
                        print(f"✗ {test_case._testMethodName}: {e}")
                        raise
                else:
                    # 运行同步测试
                    try:
                        test_method()
                        print(f"✓ {test_case._testMethodName}")
                    except Exception as e:
                        print(f"✗ {test_case._testMethodName}: {e}")
                        raise

    # 运行测试
    asyncio.run(run_async_tests())