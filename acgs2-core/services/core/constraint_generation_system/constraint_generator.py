"""Constitutional Hash: cdd01ef066bc6cf2
ACGS-2 Constraint Generator
使用Guidance和Outlines库强制LLM生成语法正确代码
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# 尝试导入约束库，如果不可用则使用fallback
try:
    import guidance

    GUIDANCE_AVAILABLE = True
except ImportError:
    guidance = None
    GUIDANCE_AVAILABLE = False

try:
    import outlines

    OUTLINES_AVAILABLE = True
except ImportError:
    outlines = None
    OUTLINES_AVAILABLE = False

from dynamic_updater import DynamicConstraintUpdater
from feedback_loop import FeedbackLoop
from language_constraints import LanguageConstraints
from quality_scorer import QualityScorer
from unit_test_generator import UnitTestGenerator

logger = logging.getLogger(__name__)


@dataclass
class GenerationRequest:
    """代码生成请求"""

    language: str
    task_description: str
    context: Optional[Dict[str, Any]] = None
    constraints: Optional[Dict[str, Any]] = None
    generate_tests: bool = True
    quality_check: bool = True


@dataclass
class GenerationResult:
    """代码生成结果"""

    code: str
    tests: Optional[str] = None
    quality_score: Optional[float] = None
    syntax_valid: bool = True
    generation_time: float = 0.0
    constraint_violations: List[str] = None
    feedback_data: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.constraint_violations is None:
            self.constraint_violations = []


class ConstraintGenerator:
    """
    约束生成器 - 使用Guidance/Outlines强制语法正确代码生成
    """

    def __init__(
        self,
        use_guidance: bool = True,
        use_outlines: bool = True,
        model_name: str = "gpt-4",
        enable_dynamic_update: bool = True,
        enable_feedback_loop: bool = True,
    ):
        """
        初始化约束生成器

        Args:
            use_guidance: 是否使用Microsoft Guidance
            use_outlines: 是否使用Outlines库
            model_name: LLM模型名称
            enable_dynamic_update: 是否启用动态约束更新
            enable_feedback_loop: 是否启用反馈循环
        """
        self.use_guidance = use_guidance and GUIDANCE_AVAILABLE
        self.use_outlines = use_outlines and OUTLINES_AVAILABLE
        self.model_name = model_name

        # 初始化组件
        self.language_constraints = LanguageConstraints()
        self.dynamic_updater = DynamicConstraintUpdater() if enable_dynamic_update else None
        self.unit_test_generator = UnitTestGenerator()
        self.quality_scorer = QualityScorer()
        self.feedback_loop = FeedbackLoop() if enable_feedback_loop else None

        # 统计信息
        self.stats = {
            "total_generations": 0,
            "successful_generations": 0,
            "syntax_errors_caught": 0,
            "quality_improvements": 0,
            "constraint_updates": 0,
        }

        logger.info(
            f"ConstraintGenerator initialized with Guidance: {self.use_guidance}, Outlines: {self.use_outlines}"
        )

    async def generate_code(self, request: GenerationRequest) -> GenerationResult:
        """
        生成约束代码

        Args:
            request: 生成请求

        Returns:
            生成结果
        """
        start_time = datetime.now(timezone.utc)

        try:
            # 获取语言特定的约束
            constraints = self._get_constraints(request)

            # 使用约束生成代码
            code = await self._generate_with_constraints(request, constraints)

            # 验证语法
            syntax_valid = self._validate_syntax(code, request.language)

            # 生成测试（如果请求）
            tests = None
            if request.generate_tests and syntax_valid:
                tests = await self.unit_test_generator.generate_tests(code, request.language)

            # 质量评分
            quality_score = None
            if request.quality_check and syntax_valid:
                quality_score = await self.quality_scorer.score_code(code, request.language)

            # 计算生成时间
            generation_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            # 创建结果
            result = GenerationResult(
                code=code,
                tests=tests,
                quality_score=quality_score,
                syntax_valid=syntax_valid,
                generation_time=generation_time,
            )

            # 更新统计
            self._update_stats(result)

            # 动态更新约束（如果启用）
            if self.dynamic_updater and result.syntax_valid:
                await self.dynamic_updater.update_constraints(request, result)

            # 反馈循环（如果启用）
            if self.feedback_loop:
                feedback_data = await self.feedback_loop.process_feedback(request, result)
                result.feedback_data = feedback_data

            logger.info(
                f"Code generation completed: syntax_valid={syntax_valid}, "
                f"quality_score={quality_score}, time={generation_time:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            generation_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            return GenerationResult(
                code="",
                syntax_valid=False,
                generation_time=generation_time,
                constraint_violations=[str(e)],
            )

    def _get_constraints(self, request: GenerationRequest) -> Dict[str, Any]:
        """获取适用于请求的约束"""
        # 获取基础语言约束
        constraints = self.language_constraints.get_constraints(request.language)

        # 合并请求特定的约束
        if request.constraints:
            constraints.update(request.constraints)

        # 应用动态更新（如果可用）
        if self.dynamic_updater:
            dynamic_constraints = self.dynamic_updater.get_dynamic_constraints(request.language)
            constraints.update(dynamic_constraints)

        return constraints

    async def _generate_with_constraints(
        self, request: GenerationRequest, constraints: Dict[str, Any]
    ) -> str:
        """使用约束生成代码"""
        prompt = self._build_generation_prompt(request, constraints)

        if self.use_guidance:
            return await self._generate_with_guidance(prompt, constraints)
        elif self.use_outlines:
            return await self._generate_with_outlines(prompt, constraints)
        else:
            return await self._generate_fallback(prompt, constraints)

    async def _generate_with_guidance(self, prompt: str, constraints: Dict[str, Any]) -> str:
        """使用Microsoft Guidance生成"""
        try:
            # 创建guidance程序
            program = guidance(prompt)

            # 应用约束
            if "json_schema" in constraints:
                program = program + guidance.gen(schema=constraints["json_schema"])
            elif "grammar" in constraints:
                program = program + guidance.gen(grammar=constraints["grammar"])

            # 执行生成
            result = await program()

            return result.text

        except Exception as e:
            logger.warning(f"Guidance generation failed: {e}")
            raise

    async def _generate_with_outlines(self, prompt: str, constraints: Dict[str, Any]) -> str:
        """使用Outlines生成"""
        try:
            # 创建模型
            model = outlines.models.openai(self.model_name)

            # 应用约束
            if "json_schema" in constraints:
                generator = outlines.generate.json(model, constraints["json_schema"])
            elif "grammar" in constraints:
                generator = outlines.generate.cfg(model, constraints["grammar"])
            else:
                generator = outlines.generate.text(model)

            # 生成
            result = generator(prompt)
            return result

        except Exception as e:
            logger.warning(f"Outlines generation failed: {e}")
            raise

    async def _generate_fallback(self, prompt: str, constraints: Dict[str, Any]) -> str:
        """Fallback生成（无约束库时使用）"""
        # 这里应该调用基础LLM API
        # 由于没有具体的LLM集成，这里返回示例代码
        logger.warning("Using fallback generation without constraints")

        # 简单的基于规则的代码生成
        if constraints.get("language") == "python":
            return self._generate_python_fallback(prompt, constraints)
        elif constraints.get("language") == "javascript":
            return self._generate_javascript_fallback(prompt, constraints)
        else:
            return f"# Generated code for {constraints.get('language', 'unknown')}\n# {prompt[:100]}..."

    def _generate_python_fallback(self, prompt: str, constraints: Dict[str, Any]) -> str:
        """Python代码fallback生成"""
        return f'''"""
Generated Python code with constraints
Task: {prompt[:100]}...
"""

def generated_function():
    """Generated function with proper syntax"""
    try:
        # Implementation here
        result = "success"
        return result
    except Exception as e:
        logger.error(f"Error: {{e}}")
        raise

if __name__ == "__main__":
    generated_function()
'''

    def _generate_javascript_fallback(self, prompt: str, constraints: Dict[str, Any]) -> str:
        """JavaScript代码fallback生成"""
        return f"""/**
 * Generated JavaScript code with constraints
 * Task: {prompt[:100]}...
 */

function generatedFunction() {{
    try {{
        // Implementation here
        const result = "success";
        return result;
    }} catch (error) {{
        console.error(`Error: ${{error}}`);
        throw error;
    }}
}}

module.exports = {{ generatedFunction }};

// Usage
if (require.main === module) {{
    generatedFunction();
}}
"""

    def _build_generation_prompt(
        self, request: GenerationRequest, constraints: Dict[str, Any]
    ) -> str:
        """构建生成提示"""
        prompt_parts = [
            f"Generate {request.language} code for the following task:",
            f"Task: {request.task_description}",
            "",
        ]

        if request.context:
            prompt_parts.append("Context:")
            for key, value in request.context.items():
                prompt_parts.append(f"- {key}: {value}")
            prompt_parts.append("")

        if constraints:
            prompt_parts.append("Constraints:")
            for key, value in constraints.items():
                if key != "grammar" and key != "json_schema":  # 这些是技术约束
                    prompt_parts.append(f"- {key}: {value}")
            prompt_parts.append("")

        prompt_parts.extend(
            [
                "Requirements:",
                "- Code must be syntactically correct",
                "- Follow language best practices",
                "- Include proper error handling",
                "- Add meaningful comments",
                "",
            ]
        )

        return "\n".join(prompt_parts)

    def _validate_syntax(self, code: str, language: str) -> bool:
        """验证代码语法"""
        try:
            if language.lower() == "python":
                compile(code, "<string>", "exec")
                return True
            elif language.lower() == "javascript":
                # 简单的JS语法检查
                return self._validate_javascript_syntax(code)
            else:
                # 对于其他语言，执行基本检查
                return len(code.strip()) > 0 and not code.startswith("# Error")
        except SyntaxError:
            return False
        except Exception:
            return False

    def _validate_javascript_syntax(self, code: str) -> bool:
        """JavaScript语法验证"""
        # 基本检查
        try:
            # 检查括号匹配
            brackets = {"(": ")", "[": "]", "{": "}"}
            stack = []

            for char in code:
                if char in brackets:
                    stack.append(char)
                elif char in brackets.values():
                    if not stack:
                        return False
                    if brackets[stack[-1]] != char:
                        return False
                    stack.pop()

            return len(stack) == 0
        except (KeyError, IndexError, TypeError):
            # Bracket matching failed
            return False

    def _update_stats(self, result: GenerationResult):
        """更新统计信息"""
        self.stats["total_generations"] += 1

        if result.syntax_valid:
            self.stats["successful_generations"] += 1
        else:
            self.stats["syntax_errors_caught"] += 1

        if result.quality_score and result.quality_score > 8.0:
            self.stats["quality_improvements"] += 1

    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return self.stats.copy()

    async def update_constraints_from_feedback(self, feedback: Dict[str, Any]):
        """从反馈更新约束"""
        if self.dynamic_updater:
            await self.dynamic_updater.process_feedback(feedback)
            self.stats["constraint_updates"] += 1
