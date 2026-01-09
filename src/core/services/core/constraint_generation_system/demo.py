"""
Constitutional Hash: cdd01ef066bc6cf2
"""

#!/usr/bin/env python3
"""
ACGS-2 Constraint Generation System Demo
演示约束生成系统的功能
"""

# ruff: noqa: E402
import asyncio
import logging
import os
import sys

# Configure structured logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from constraint_generator import ConstraintGenerator, GenerationRequest
from language_constraints import LanguageConstraints
from quality_scorer import QualityScorer
from unit_test_generator import UnitTestGenerator

# Configure structured logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def demo_python_generation():
    """演示Python代码生成"""
    logger.info("Starting Python code generation demo", extra={"demo_type": "python_generation"})

    generator = ConstraintGenerator(
        use_guidance=False,
        use_outlines=False,
        enable_dynamic_update=False,
        enable_feedback_loop=False,
    )

    request = GenerationRequest(
        language="python",
        task_description="创建一个计算斐波那契数列的函数，要求包含类型提示和文档字符串",
        generate_tests=True,
        quality_check=True,
    )

    logger.info(
        "Processing generation request",
        extra={
            "language": request.language,
            "task_description": request.task_description,
            "generate_tests": request.generate_tests,
            "quality_check": request.quality_check,
        },
    )

    result = await generator.generate_code(request)

    logger.info(
        "Code generation completed",
        extra={
            "generation_time": result.generation_time,
            "syntax_valid": result.syntax_valid,
            "quality_score": result.quality_score,
            "code_length": len(result.code) if result.code else 0,
            "tests_generated": bool(result.tests),
        },
    )

    if result.code:
        logger.info(
            "Generated code preview",
            extra={
                "code_preview": result.code[:200] + "..." if len(result.code) > 200 else result.code
            },
        )

    if result.tests:
        test_preview = result.tests[:500] + "..." if len(result.tests) > 500 else result.tests
        logger.info(
            "Generated tests preview",
            extra={"test_preview": test_preview, "test_length": len(result.tests)},
        )

    logger.info("\n" + "=" * 50 + "\n")


async def demo_javascript_generation():
    """演示JavaScript代码生成"""
    logger.info(
        "Starting JavaScript code generation demo", extra={"demo_type": "javascript_generation"}
    )

    generator = ConstraintGenerator(
        use_guidance=False,
        use_outlines=False,
        enable_dynamic_update=False,
        enable_feedback_loop=False,
    )

    request = GenerationRequest(
        language="javascript",
        task_description="创建一个验证邮箱地址的函数",
        generate_tests=True,
        quality_check=True,
    )

    logger.info(
        "Processing JavaScript generation request",
        extra={
            "language": request.language,
            "task_description": request.task_description,
            "generate_tests": request.generate_tests,
            "quality_check": request.quality_check,
        },
    )

    result = await generator.generate_code(request)

    logger.info(
        "JavaScript code generation completed",
        extra={
            "generation_time": result.generation_time,
            "syntax_valid": result.syntax_valid,
            "quality_score": result.quality_score,
            "code_length": len(result.code) if result.code else 0,
            "tests_generated": bool(result.tests),
        },
    )

    if result.code:
        logger.info(
            "Generated JavaScript code preview",
            extra={
                "code_preview": result.code[:200] + "..." if len(result.code) > 200 else result.code
            },
        )

    if result.tests:
        test_preview = result.tests[:500] + "..." if len(result.tests) > 500 else result.tests
        logger.info(
            "Generated JavaScript tests preview",
            extra={"test_preview": test_preview, "test_length": len(result.tests)},
        )

    logger.info("\n" + "=" * 50 + "\n")


async def demo_language_constraints():
    """演示语言约束"""
    logger.info("=== 语言约束演示 ===")

    constraints = LanguageConstraints()

    languages = ["python", "javascript", "java", "cpp", "go"]

    for lang in languages:
        lang_constraints = constraints.get_constraints(lang)
    logger.info(f"{lang.upper()} 约束:")
    logger.info(f"  语言: {lang_constraints['language']}")
    logger.info(f"  缩进风格: {lang_constraints['indent_style']}")
    logger.info(f"  缩进大小: {lang_constraints['indent_size']}")
    logger.info(f"  最大行长: {lang_constraints['max_line_length']}")
    logger.info(f"  文件扩展名: {lang_constraints['file_extension']}")

    logger.info("=" * 50 + "\n")


async def demo_unit_test_generation():
    """演示单元测试生成"""
    logger.info("=== 单元测试生成演示 ===")

    test_gen = UnitTestGenerator()

    # Python示例代码
    python_code = '''
def calculate_factorial(n):
    """Calculate factorial of n"""
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return 1
    return n * calculate_factorial(n - 1)

class MathUtils:
    @staticmethod
    def is_prime(num):
        """Check if number is prime"""
        if num < 2:
            return False
        for i in range(2, int(num ** 0.5) + 1):
            if num % i == 0:
                return False
        return True
'''

    logger.info("源代码:")
    logger.info(python_code)

    tests = await test_gen.generate_tests(python_code, "python")

    logger.info("\n生成的测试:")
    logger.info(tests)

    logger.info("\n" + "=" * 50 + "\n")


async def demo_quality_scoring():
    """演示质量评分"""
    logger.info("=== 代码质量评分演示 ===")

    scorer = QualityScorer(enable_local_analysis=False)

    # 好的代码示例
    good_code = '''
def bubble_sort(arr):
    """
    Sort array using bubble sort algorithm.

    Args:
        arr (list): Array to sort

    Returns:
        list: Sorted array
    """
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr
'''

    # 差的代码示例
    bad_code = """
def sort(arr):return sorted(arr)  # 没有文档，没有错误处理
"""

    logger.info("好的代码质量评分:")
    good_score = await scorer.score_code(good_code, "python")
    logger.info(f"分数: {good_score}")

    logger.info("\n差的代码质量评分:")
    bad_score = await scorer.score_code(bad_code, "python")
    logger.info(f"分数: {bad_score}")

    logger.info("\n" + "=" * 50 + "\n")


async def demo_system_stats():
    """演示系统统计"""
    logger.info("=== 系统统计演示 ===")

    generator = ConstraintGenerator()

    # 生成一些代码来积累统计
    tasks = ["创建用户管理类", "实现数据验证函数", "构建API客户端", "设计配置管理器"]

    for task in tasks:
        request = GenerationRequest(
            language="python", task_description=task, generate_tests=False, quality_check=False
        )
        await generator.generate_code(request)

    stats = generator.get_stats()
    logger.info("系统统计:")
    logger.info(f"  总生成次数: {stats['total_generations']}")
    logger.info(f"  成功生成次数: {stats['successful_generations']}")
    logger.info(f"  语法错误捕获: {stats['syntax_errors_caught']}")
    logger.info(f"  质量改进次数: {stats['quality_improvements']}")
    logger.info(f"  约束更新次数: {stats['constraint_updates']}")

    logger.info("\n" + "=" * 50 + "\n")


async def main():
    """主演示函数"""
    logger.info(
        "Starting ACGS-2 Constraint Generation System Demo",
        extra={"system": "constraint_generation", "approach": "从'事后修复'转向'约束生成'"},
    )

    try:
        logger.info(
            "Running demo sequence",
            extra={
                "demos": [
                    "language_constraints",
                    "python_generation",
                    "javascript_generation",
                    "unit_test_generation",
                    "quality_scoring",
                    "system_stats",
                ]
            },
        )

        await demo_language_constraints()
        await demo_python_generation()
        await demo_javascript_generation()
        await demo_unit_test_generation()
        await demo_quality_scoring()
        await demo_system_stats()

        logger.info(
            "Demo sequence completed successfully",
            extra={
                "features": [
                    "Guidance/Outlines库集成",
                    "CFG和JSON Schema约束定义",
                    "多语言支持 (Python, JavaScript, Java, C++, Go)",
                    "动态约束更新",
                    "单元测试自动生成",
                    "SonarQube质量评分集成",
                    "反馈循环至模型微调",
                ]
            },
        )
        logger.info("\n里程碑目标:")
        logger.info("• 代码修复需求减80%")
        logger.info("• 语法正确率>99.5%")
        logger.info("• 生成任务中测试覆盖>90%")

    except Exception as e:
        logger.info(f"演示过程中出现错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
