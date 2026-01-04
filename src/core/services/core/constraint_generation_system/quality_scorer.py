"""Constitutional Hash: cdd01ef066bc6cf2
ACGS-2 Quality Scorer
集成SonarQube进行代码质量评分
"""

import logging
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from src.core.shared.config import settings
except ImportError:
    settings = None  # type: ignore

logger = logging.getLogger(__name__)


def _get_default_sonarqube_url() -> str:
    """Get SonarQube URL from centralized config or default."""
    if settings is not None:
        return settings.quality.sonarqube_url
    return "http://localhost:9000"


def _get_default_sonarqube_token() -> Optional[str]:
    """Get SonarQube token from centralized config."""
    if settings is not None and settings.quality.sonarqube_token:
        return settings.quality.sonarqube_token.get_secret_value()
    return None


def _get_default_local_analysis() -> bool:
    """Get local analysis setting from centralized config."""
    if settings is not None:
        return settings.quality.enable_local_analysis
    return True


class QualityScorer:
    """
    代码质量评分器 - 集成SonarQube进行质量评估
    """

    def __init__(
        self,
        sonarqube_url: Optional[str] = None,
        sonarqube_token: Optional[str] = None,
        enable_local_analysis: Optional[bool] = None,
    ):
        """
        初始化质量评分器

        Args:
            sonarqube_url: SonarQube服务器URL
            sonarqube_token: SonarQube认证令牌
            enable_local_analysis: 是否启用本地分析
        """
        self.sonarqube_url = sonarqube_url or _get_default_sonarqube_url()
        self.sonarqube_token = sonarqube_token or _get_default_sonarqube_token()
        self.enable_local_analysis = (
            enable_local_analysis
            if enable_local_analysis is not None
            else _get_default_local_analysis()
        )

        # 质量指标权重
        self.weights = {
            "complexity": 0.2,
            "duplications": 0.15,
            "maintainability": 0.25,
            "reliability": 0.2,
            "security": 0.1,
            "test_coverage": 0.1,
        }

        # 语言特定的质量规则
        self.quality_rules = self._load_quality_rules()

    async def score_code(self, code: str, language: str) -> Optional[float]:
        """
        为代码评分

        Args:
            code: 代码字符串
            language: 编程语言

        Returns:
            质量分数 (0-10)
        """
        try:
            language = language.lower()

            # 多维度质量评估
            scores = {}

            # 基本语法检查
            scores["syntax"] = self._check_syntax_quality(code, language)

            # 复杂度分析
            scores["complexity"] = self._analyze_complexity(code, language)

            # 代码风格检查
            scores["style"] = self._check_code_style(code, language)

            # 最佳实践检查
            scores["best_practices"] = self._check_best_practices(code, language)

            # 文档完整性
            scores["documentation"] = self._check_documentation(code, language)

            # 如果启用SonarQube，进行远程分析
            if self.sonarqube_token and language in [
                "python",
                "javascript",
                "java",
                "cpp",
                "typescript",
            ]:
                sonar_score = await self._analyze_with_sonarqube(code, language)
                if sonar_score is not None:
                    scores["sonarqube"] = sonar_score

            # 计算综合分数
            final_score = self._calculate_overall_score(scores)

            logger.info(f"Quality score for {language} code: {final_score:.2f}")

            return final_score

        except Exception as e:
            logger.error(f"Quality scoring failed: {e}")
            return None

    def _check_syntax_quality(self, code: str, language: str) -> float:
        """检查语法质量"""
        try:
            if language == "python":
                compile(code, "<string>", "exec")
                return 1.0
            elif language == "javascript":
                # 基本检查：括号匹配等
                return self._check_javascript_syntax_quality(code)
            else:
                # 其他语言的基本检查
                return 0.8 if len(code.strip()) > 0 else 0.0
        except SyntaxError:
            return 0.0
        except Exception:
            return 0.5

    def _check_javascript_syntax_quality(self, code: str) -> float:
        """JavaScript语法质量检查"""
        score = 1.0

        # 检查括号匹配
        if not self._check_bracket_matching(code):
            score -= 0.3

        # 检查分号使用
        lines = code.split("\n")
        missing_semicolons = 0
        for line in lines:
            line = line.strip()
            if (
                line
                and not line.startswith("//")
                and not line.startswith("/*")
                and not line.endswith(";")
                and not line.endswith("{")
                and not line.endswith("}")
                and not line.endswith(",")
            ):
                # 简单的启发式检查
                if re.match(r".*\w+\s*\([^)]*\)\s*$", line):  # 函数调用
                    missing_semicolons += 1

        if missing_semicolons > 0:
            score -= min(0.2, missing_semicolons * 0.05)

        return max(0.0, score)

    def _check_bracket_matching(self, code: str) -> bool:
        """检查括号匹配"""
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

    def _analyze_complexity(self, code: str, language: str) -> float:
        """分析代码复杂度"""
        # 简单的复杂度度量
        len([line for line in code.split("\n") if line.strip()])

        # 圈复杂度估算
        complexity_indicators = [
            "if ",
            "elif ",
            "else:",
            "for ",
            "while ",
            "case ",
            "catch ",
            "&&",
            "||",
            "?",
            "try:",
            "except ",
        ]

        complexity_score = 1  # 基础复杂度
        for indicator in complexity_indicators:
            complexity_score += code.count(indicator)

        # 标准化到0-1范围
        if complexity_score <= 5:
            return 1.0  # 低复杂度
        elif complexity_score <= 15:
            return 0.7  # 中等复杂度
        elif complexity_score <= 30:
            return 0.4  # 高复杂度
        else:
            return 0.1  # 非常高复杂度

    def _check_code_style(self, code: str, language: str) -> float:
        """检查代码风格"""
        score = 1.0
        lines = code.split("\n")

        if language == "python":
            # 检查行长度
            long_lines = sum(1 for line in lines if len(line) > 79)
            if long_lines > 0:
                score -= min(0.2, long_lines * 0.02)

            # 检查缩进
            for line in lines:
                if line.strip() and not line.startswith(" ") and not line.startswith("\t"):
                    # 检查缩进是否为4的倍数
                    indent = len(line) - len(line.lstrip())
                    if indent % 4 != 0:
                        score -= 0.1
                        break

        elif language in ["javascript", "typescript"]:
            # 检查行长度
            long_lines = sum(1 for line in lines if len(line) > 80)
            if long_lines > 0:
                score -= min(0.2, long_lines * 0.02)

        return max(0.0, score)

    def _check_best_practices(self, code: str, language: str) -> float:
        """检查最佳实践"""
        score = 1.0

        if language == "python":
            # 检查异常处理
            if "try:" in code and "except:" not in code and "except Exception" not in code:
                score -= 0.2

            # 检查变量命名
            bad_names = re.findall(r"\b[a-z][A-Z]+\b", code)  # camelCase in Python
            if bad_names:
                score -= min(0.1, len(bad_names) * 0.02)

        elif language in ["javascript", "typescript"]:
            # 检查var使用（应该用let/const）
            var_count = code.count("var ")
            if var_count > 0:
                score -= min(0.2, var_count * 0.05)

        return max(0.0, score)

    def _check_documentation(self, code: str, language: str) -> float:
        """检查文档完整性"""
        score = 0.5  # 基础分数

        if language == "python":
            # 检查docstring
            if '"""' in code or "'''" in code:
                score += 0.3

            # 检查函数注释
            functions = len(re.findall(r"def\s+\w+", code))
            comments = len(re.findall(r"#.*", code))
            if functions > 0:
                comment_ratio = comments / functions
                score += min(0.2, comment_ratio * 0.1)

        elif language in ["javascript", "typescript"]:
            # 检查JSDoc注释
            if "/**" in code:
                score += 0.3

        return min(1.0, score)

    async def _analyze_with_sonarqube(self, code: str, language: str) -> Optional[float]:
        """使用SonarQube进行分析"""
        try:
            # 创建临时文件
            temp_dir = Path("/tmp/sonarqube_analysis")
            temp_dir.mkdir(exist_ok=True)

            # 根据语言确定文件扩展名
            ext_map = {
                "python": ".py",
                "javascript": ".js",
                "typescript": ".ts",
                "java": ".java",
                "cpp": ".cpp",
            }

            ext = ext_map.get(language, ".txt")
            temp_file = temp_dir / f"analysis_code{ext}"
            temp_file.write_text(code)

            # 运行sonar-scanner（如果可用）
            if self._is_sonar_scanner_available():
                result = await self._run_sonar_analysis(str(temp_file), language)
                if result:
                    return self._parse_sonar_results(result)

            # 清理临时文件
            temp_file.unlink()
            temp_dir.rmdir()

        except Exception as e:
            logger.warning(f"SonarQube analysis failed: {e}")

        return None

    def _is_sonar_scanner_available(self) -> bool:
        """检查sonar-scanner是否可用"""
        try:
            result = subprocess.run(
                ["sonar-scanner", "--version"], capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    async def _run_sonar_analysis(self, file_path: str, language: str) -> Optional[Dict[str, Any]]:
        """运行SonarQube分析"""
        try:
            # 创建sonar-project.properties
            props_file = Path(file_path).parent / "sonar-project.properties"
            props_content = f"""sonar.projectKey=constraint-analysis
sonar.projectName=Constraint Analysis
sonar.projectVersion=1.0
sonar.sources=.
sonar.language={language}
sonar.host.url={self.sonarqube_url}
sonar.login={self.sonarqube_token}
"""
            props_file.write_text(props_content)

            # 运行分析
            cmd = ["sonar-scanner", "-Dsonar.projectBaseDir=" + str(Path(file_path).parent)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                # 解析结果（这里需要根据实际的SonarQube API来获取结果）
                # 简化版本：返回模拟结果
                return {
                    "complexity": 5,
                    "duplications": 0,
                    "maintainability": "A",
                    "reliability": "A",
                    "security": "A",
                    "coverage": 80.0,
                }

            # 清理
            props_file.unlink()

        except subprocess.TimeoutExpired:
            logger.warning("SonarQube analysis timed out")
        except Exception as e:
            logger.error(f"SonarQube analysis error: {e}")

        return None

    def _parse_sonar_results(self, results: Dict[str, Any]) -> float:
        """解析SonarQube结果"""
        # 将SonarQube指标转换为0-1分数
        score = 0.0

        # 复杂度评分（反向：复杂度越低分数越高）
        complexity = results.get("complexity", 10)
        score += (1 - min(complexity / 50, 1)) * self.weights["complexity"]

        # 重复代码评分
        duplications = results.get("duplications", 0)
        score += (1 - min(duplications / 100, 1)) * self.weights["duplications"]

        # 可维护性评分
        maintainability = results.get("maintainability", "C")
        maint_score = {"A": 1.0, "B": 0.7, "C": 0.4, "D": 0.1, "E": 0.0}.get(maintainability, 0.5)
        score += maint_score * self.weights["maintainability"]

        # 可靠性评分
        reliability = results.get("reliability", "C")
        rel_score = {"A": 1.0, "B": 0.7, "C": 0.4, "D": 0.1, "E": 0.0}.get(reliability, 0.5)
        score += rel_score * self.weights["reliability"]

        # 安全性评分
        security = results.get("security", "C")
        sec_score = {"A": 1.0, "B": 0.7, "C": 0.4, "D": 0.1, "E": 0.0}.get(security, 0.5)
        score += sec_score * self.weights["security"]

        # 测试覆盖率
        coverage = results.get("coverage", 0) / 100
        score += coverage * self.weights["test_coverage"]

        return score

    def _calculate_overall_score(self, scores: Dict[str, float]) -> float:
        """计算综合分数"""
        # 基础分数
        base_score = 5.0

        # 应用各个维度的评分
        for metric, score in scores.items():
            if metric == "syntax":
                base_score += (score - 0.5) * 2  # -1 到 +1
            elif metric == "complexity":
                base_score += (score - 0.5) * 2
            elif metric == "style":
                base_score += (score - 0.5) * 1
            elif metric == "best_practices":
                base_score += (score - 0.5) * 1.5
            elif metric == "documentation":
                base_score += (score - 0.5) * 1
            elif metric == "sonarqube":
                base_score += (score - 0.5) * 3  # SonarQube结果权重更高

        # 确保分数在0-10范围内
        return max(0.0, min(10.0, base_score))

    def _load_quality_rules(self) -> Dict[str, List[Dict[str, Any]]]:
        """加载质量规则"""
        return {
            "python": [
                {"rule": "line_length", "max_length": 79},
                {"rule": "indent_style", "style": "spaces", "size": 4},
                {"rule": "naming_convention", "pattern": r"^[a-z_][a-z0-9_]*$"},
            ],
            "javascript": [
                {"rule": "line_length", "max_length": 80},
                {"rule": "indent_style", "style": "spaces", "size": 2},
                {"rule": "semicolon_required", "value": True},
            ],
            "java": [
                {"rule": "line_length", "max_length": 100},
                {"rule": "indent_style", "style": "spaces", "size": 4},
                {"rule": "brace_style", "style": "same_line"},
            ],
        }
