#!/usr/bin/env python3
"""
ACGS-2 Constraint Generation System Demo
演示约束生成系统的功能
"""

import asyncio
import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from constraint_generator import ConstraintGenerator, GenerationRequest
from language_constraints import LanguageConstraints
from unit_test_generator import UnitTestGenerator
from quality_scorer import QualityScorer


async def demo_python_generation():
    """演示Python代码生成"""
    print("=== Python代码生成演示 ===")

    generator = ConstraintGenerator(
        use_guidance=False,
        use_outlines=False,
        enable_dynamic_update=False,
        enable_feedback_loop=False
    )

    request = GenerationRequest(
        language="python",
        task_description="创建一个计算斐波那契数列的函数，要求包含类型提示和文档字符串",
        generate_tests=True,
        quality_check=True
    )

    print(f"任务: {request.task_description}")
    result = await generator.generate_code(request)

    print(f"生成时间: {result.generation_time:.2f}秒")
    print(f"语法正确: {result.syntax_valid}")
    print(f"质量分数: {result.quality_score}")
    print("\n生成的代码:")
    print(result.code)

    if result.tests:
        print("\n生成的测试:")
        print(result.tests[:500] + "..." if len(result.tests) > 500 else result.tests)

    print("\n" + "="*50 + "\n")


async def demo_javascript_generation():
    """演示JavaScript代码生成"""
    print("=== JavaScript代码生成演示 ===")

    generator = ConstraintGenerator(
        use_guidance=False,
        use_outlines=False,
        enable_dynamic_update=False,
        enable_feedback_loop=False
    )

    request = GenerationRequest(
        language="javascript",
        task_description="创建一个验证邮箱地址的函数",
        generate_tests=True,
        quality_check=True
    )

    print(f"任务: {request.task_description}")
    result = await generator.generate_code(request)

    print(f"生成时间: {result.generation_time:.2f}秒")
    print(f"语法正确: {result.syntax_valid}")
    print(f"质量分数: {result.quality_score}")
    print("\n生成的代码:")
    print(result.code)

    if result.tests:
        print("\n生成的测试:")
        print(result.tests[:500] + "..." if len(result.tests) > 500 else result.tests)

    print("\n" + "="*50 + "\n")


async def demo_language_constraints():
    """演示语言约束"""
    print("=== 语言约束演示 ===")

    constraints = LanguageConstraints()

    languages = ['python', 'javascript', 'java', 'cpp', 'go']

    for lang in languages:
        lang_constraints = constraints.get_constraints(lang)
        print(f"{lang.upper()} 约束:")
        print(f"  语言: {lang_constraints['language']}")
        print(f"  缩进风格: {lang_constraints['indent_style']}")
        print(f"  缩进大小: {lang_constraints['indent_size']}")
        print(f"  最大行长: {lang_constraints['max_line_length']}")
        print(f"  文件扩展名: {lang_constraints['file_extension']}")
        print()

    print("="*50 + "\n")


async def demo_unit_test_generation():
    """演示单元测试生成"""
    print("=== 单元测试生成演示 ===")

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

    print("源代码:")
    print(python_code)

    tests = await test_gen.generate_tests(python_code, "python")

    print("\n生成的测试:")
    print(tests)

    print("\n" + "="*50 + "\n")


async def demo_quality_scoring():
    """演示质量评分"""
    print("=== 代码质量评分演示 ===")

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
    bad_code = '''
def sort(arr):return sorted(arr)  # 没有文档，没有错误处理
'''

    print("好的代码质量评分:")
    good_score = await scorer.score_code(good_code, "python")
    print(f"分数: {good_score}")

    print("\n差的代码质量评分:")
    bad_score = await scorer.score_code(bad_code, "python")
    print(f"分数: {bad_score}")

    print("\n" + "="*50 + "\n")


async def demo_system_stats():
    """演示系统统计"""
    print("=== 系统统计演示 ===")

    generator = ConstraintGenerator()

    # 生成一些代码来积累统计
    tasks = [
        "创建用户管理类",
        "实现数据验证函数",
        "构建API客户端",
        "设计配置管理器"
    ]

    for task in tasks:
        request = GenerationRequest(
            language="python",
            task_description=task,
            generate_tests=False,
            quality_check=False
        )
        await generator.generate_code(request)

    stats = generator.get_stats()
    print("系统统计:")
    print(f"  总生成次数: {stats['total_generations']}")
    print(f"  成功生成次数: {stats['successful_generations']}")
    print(f"  语法错误捕获: {stats['syntax_errors_caught']}")
    print(f"  质量改进次数: {stats['quality_improvements']}")
    print(f"  约束更新次数: {stats['constraint_updates']}")

    print("\n" + "="*50 + "\n")


async def main():
    """主演示函数"""
    print("ACGS-2 约束生成系统演示")
    print("从'事后修复'转向'约束生成'")
    print("="*50 + "\n")

    try:
        await demo_language_constraints()
        await demo_python_generation()
        await demo_javascript_generation()
        await demo_unit_test_generation()
        await demo_quality_scoring()
        await demo_system_stats()

        print("演示完成!")
        print("\n系统特点:")
        print("✓ Guidance/Outlines库集成")
        print("✓ CFG和JSON Schema约束定义")
        print("✓ 多语言支持 (Python, JavaScript, Java, C++, Go)")
        print("✓ 动态约束更新")
        print("✓ 单元测试自动生成")
        print("✓ SonarQube质量评分集成")
        print("✓ 反馈循环至模型微调")
        print("\n里程碑目标:")
        print("• 代码修复需求减80%")
        print("• 语法正确率>99.5%")
        print("• 生成任务中测试覆盖>90%")

    except Exception as e:
        print(f"演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())