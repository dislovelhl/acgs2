#!/usr/bin/env python3
"""
ACGS-2 Constraint Generation System Tests
Modernized to use pytest and pytest-asyncio
"""

import os
import sys

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from constraint_generator import ConstraintGenerator, GenerationRequest, GenerationResult
from feedback_loop import FeedbackLoop
from language_constraints import LanguageConstraints
from quality_scorer import QualityScorer
from unit_test_generator import UnitTestGenerator


@pytest.fixture
def generator():
    """ConstraintGenerator fixture."""
    return ConstraintGenerator(
        use_guidance=False,
        use_outlines=False,
        enable_dynamic_update=True,
        enable_feedback_loop=True,
    )


def test_generation_request_creation():
    """测试生成请求创建"""
    request = GenerationRequest(
        language="python",
        task_description="Create a function to calculate fibonacci numbers",
        generate_tests=True,
        quality_check=True,
    )
    assert request.language == "python"
    assert request.generate_tests is True
    assert request.quality_check is True


def test_generation_result_creation():
    """测试生成结果创建"""
    result = GenerationResult(
        code="def fib(n): return n", syntax_valid=True, quality_score=8.5, generation_time=1.2
    )
    assert result.code == "def fib(n): return n"
    assert result.syntax_valid is True
    assert result.quality_score == 8.5
    assert result.generation_time == 1.2


@pytest.mark.asyncio
async def test_python_code_generation(generator):
    """测试Python代码生成"""
    request = GenerationRequest(
        language="python",
        task_description="Create a simple calculator class",
        generate_tests=True,
        quality_check=True,
    )
    result = await generator.generate_code(request)
    assert isinstance(result, GenerationResult)
    assert len(result.code) > 0
    assert result.syntax_valid is True
    assert result.quality_score is not None
    assert result.generation_time >= 0


@pytest.mark.asyncio
async def test_javascript_code_generation(generator):
    """测试JavaScript代码生成"""
    request = GenerationRequest(
        language="javascript",
        task_description="Create a function to validate email addresses",
        generate_tests=True,
        quality_check=True,
    )
    result = await generator.generate_code(request)
    assert isinstance(result, GenerationResult)
    assert len(result.code) > 0
    assert result.syntax_valid is True


def test_language_constraints_loading():
    """测试语言约束加载"""
    constraints = LanguageConstraints()
    python_constraints = constraints.get_constraints("python")
    assert python_constraints["language"] == "python"
    assert python_constraints["indent_style"] == "spaces"
    assert python_constraints["indent_size"] == 4


@pytest.mark.asyncio
async def test_unit_test_generation():
    """测试单元测试生成"""
    test_gen = UnitTestGenerator()
    python_code = """
def add_numbers(a, b):
    return a + b
"""
    tests = await test_gen.generate_tests(python_code, "python")
    assert tests is not None
    assert "unittest" in tests
    assert "test_add_numbers" in tests


@pytest.mark.asyncio
async def test_quality_scoring():
    """测试质量评分"""
    scorer = QualityScorer(enable_local_analysis=False)
    good_code = 'def hello(): print("world")'
    score = await scorer.score_code(good_code, "python")
    assert score is not None
    assert 0 <= score <= 10


@pytest.mark.asyncio
async def test_feedback_loop():
    """测试反馈循环"""
    feedback_loop = FeedbackLoop(min_samples_for_training=1)
    request = {"language": "python", "task_description": "test task"}
    result = GenerationResult(
        code="def test(): pass",
        syntax_valid=False,
        quality_score=6.0,
        generation_time=1.0,
        constraint_violations=["Missing docstring"],
    )
    feedback_result = await feedback_loop.process_feedback(request, result)
    assert feedback_result is not None
    summary = feedback_loop.get_feedback_summary()
    assert "total_samples" in summary


@pytest.mark.asyncio
async def test_full_pipeline(generator):
    """测试完整生成管道"""
    request = GenerationRequest(
        language="python",
        task_description="Create a library system",
        generate_tests=True,
        quality_check=True,
    )
    result = await generator.generate_code(request)
    assert isinstance(result, GenerationResult)
    assert result.syntax_valid is True
    if result.tests:
        assert "class" in result.tests
        assert "def test_" in result.tests
