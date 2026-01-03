"""Constitutional Hash: cdd01ef066bc6cf2
ACGS-2 Unit Test Generator
自动为生成的代码生成单元测试
"""

import ast
import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class UnitTestGenerator:
    """
    单元测试生成器 - 为生成的代码自动创建测试
    """

    def __init__(self, test_framework: str = "auto"):
        """
        初始化测试生成器

        Args:
            test_framework: 测试框架 ('auto', 'pytest', 'unittest', 'jest', 'junit')
        """
        self.test_framework = test_framework
        self.templates = self._load_test_templates()

    async def generate_tests(self, code: str, language: str) -> Optional[str]:
        """
        生成单元测试

        Args:
            code: 源代码
            language: 编程语言

        Returns:
            生成的测试代码
        """
        try:
            language = language.lower()

            if language == "python":
                return self._generate_python_tests(code)
            elif language in ["javascript", "typescript"]:
                return self._generate_javascript_tests(code)
            elif language == "java":
                return self._generate_java_tests(code)
            elif language == "cpp":
                return self._generate_cpp_tests(code)
            elif language == "go":
                return self._generate_go_tests(code)
            else:
                logger.warning(f"Test generation not supported for language: {language}")
                return None

        except Exception as e:
            logger.error(f"Test generation failed: {e}")
            return None

    def _generate_python_tests(self, code: str) -> Optional[str]:
        """生成Python单元测试"""
        try:
            # 解析代码获取函数和类
            tree = ast.parse(code)

            test_functions = []
            test_classes = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                    test_functions.append(self._generate_python_function_test(node))
                elif isinstance(node, ast.ClassDef):
                    test_classes.append(self._generate_python_class_test(node))

            if not test_functions and not test_classes:
                return None

            # 生成测试文件
            test_code = self._build_python_test_file(test_functions, test_classes)

            return test_code

        except SyntaxError:
            logger.warning("Cannot parse Python code for test generation")
            return None

    def _generate_python_function_test(self, func_node: ast.FunctionDef) -> str:
        """为Python函数生成测试"""
        func_name = func_node.name

        # 分析函数参数
        args = []
        for arg in func_node.args.args:
            if arg.arg != "self":
                args.append(arg.arg)

        # 生成测试用例
        test_cases = []

        # 基本测试用例
        if not args:
            test_cases.append(
                f"""
    def test_{func_name}_basic(self):
        \"\"\"Test basic functionality of {func_name}\"\"\"
        result = {func_name}()
        self.assertIsNotNone(result)"""
            )
        else:
            # 带参数的测试
            test_args = []
            for arg in args:
                if "str" in arg.lower() or "name" in arg.lower():
                    test_args.append(f'"{arg}_test"')
                elif "num" in arg.lower() or "count" in arg.lower() or "id" in arg.lower():
                    test_args.append("42")
                else:
                    test_args.append("None")

            args_str = ", ".join(test_args)

            test_cases.append(
                f"""
    def test_{func_name}_with_args(self):
        \"\"\"Test {func_name} with arguments\"\"\"
        result = {func_name}({args_str})
        self.assertIsNotNone(result)"""
            )

        # 边界条件测试
        if args:
            test_cases.append(
                f"""
    def test_{func_name}_edge_cases(self):
        \"\"\"Test {func_name} with edge cases\"\"\"
        # Test with None values
        try:
            result = {func_name}({", ".join(["None"] * len(args))})
            self.assertIsNotNone(result)
        except (TypeError, ValueError):
            # Expected for invalid inputs
            pass"""
            )

        return "\n".join(test_cases)

    def _generate_python_class_test(self, class_node: ast.ClassDef) -> str:
        """为Python类生成测试"""
        class_name = class_node.name

        test_code = f"""
    def test_{class_name}_instantiation(self):
        \"\"\"Test {class_name} instantiation\"\"\"
        instance = {class_name}()
        self.assertIsInstance(instance, {class_name})

    def test_{class_name}_methods(self):
        \"\"\"Test {class_name} methods\"\"\"
        instance = {class_name}()
        # Test basic method calls
        methods = [method for method in dir(instance) if not method.startswith('_')]
        for method in methods[:3]:  # Test first 3 methods
            try:
                method_obj = getattr(instance, method)
                if callable(method_obj):
                    # Try calling with no arguments
                    result = method_obj()
                    self.assertIsNotNone(result)
            except (TypeError, AttributeError):
                # Method may require arguments
                continue"""

        return test_code

    def _build_python_test_file(self, test_functions: List[str], test_classes: List[str]) -> str:
        """构建Python测试文件"""
        imports = """import unittest
import sys
import os

# Add the source directory to the path
sys.path.insert(0, os.path.dirname(__file__))
"""

        class_definition = """
class GeneratedCodeTest(unittest.TestCase):
    \"\"\"Unit tests for generated code\"\"\"

    def setUp(self):
        \"\"\"Set up test fixtures\"\"\"
        pass

    def tearDown(self):
        \"\"\"Tear down test fixtures\"\"\"
        pass"""

        # 添加测试方法
        all_tests = test_functions + test_classes
        test_methods = "\n".join(all_tests)

        main_section = """

if __name__ == '__main__':
    unittest.main()"""

        return imports + class_definition + test_methods + main_section

    def _generate_javascript_tests(self, code: str) -> Optional[str]:
        """生成JavaScript单元测试"""
        # 提取函数名
        func_pattern = r"function\s+(\w+)\s*\("
        functions = re.findall(func_pattern, code)

        if not functions:
            return None

        test_code = """const assert = require('assert');

describe('Generated Code Tests', function() {
"""

        for func in functions:
            test_code += f"""
    describe('{func}', function() {{
        it('should execute without errors', function() {{
            // Basic functionality test
            const result = {func}();
            assert(result !== undefined);
        }});

        it('should handle basic inputs', function() {{
            // Test with sample inputs
            try {{
                const result = {func}('test', 42);
                assert(result !== undefined);
            }} catch (error) {{
                // Function may not accept these arguments
                assert(error instanceof Error);
            }}
        }});
    }});"""

        test_code += """
});"""

        return test_code

    def _generate_java_tests(self, code: str) -> Optional[str]:
        """生成Java单元测试"""
        # 提取类名和方法名
        class_pattern = r"public\s+class\s+(\w+)"
        classes = re.findall(class_pattern, code)

        if not classes:
            return None

        class_name = classes[0]

        test_code = f"""import org.junit.Test;
import org.junit.Before;
import org.junit.After;
import static org.junit.Assert.*;

public class {class_name}Test {{

    private {class_name} instance;

    @Before
    public void setUp() {{
        instance = new {class_name}();
    }}

    @After
    public void tearDown() {{
        instance = null;
    }}

    @Test
    public void testInstantiation() {{
        assertNotNull(instance);
    }}

    @Test
    public void testBasicFunctionality() {{
        // Test basic functionality
        // This is a template - actual tests depend on the class methods
        assertTrue(true); // Placeholder assertion
    }}

    @Test
    public void testEdgeCases() {{
        // Test edge cases
        try {{
            // Test with null or invalid inputs
            assertTrue(true); // Placeholder assertion
        }} catch (Exception e) {{
            // Expected behavior
            assertNotNull(e);
        }}
    }}
}}"""

        return test_code

    def _generate_cpp_tests(self, code: str) -> Optional[str]:
        """生成C++单元测试"""
        # 简单的C++测试模板
        test_code = """#include <gtest/gtest.h>
#include <gmock/gmock.h>

// Include the generated code header
// #include "generated_code.h"

class GeneratedCodeTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Set up test fixtures
    }

    void TearDown() override {
        // Tear down test fixtures
    }
};

TEST_F(GeneratedCodeTest, BasicFunctionality) {
    // Test basic functionality
    EXPECT_TRUE(true); // Placeholder test
}

TEST_F(GeneratedCodeTest, EdgeCases) {
    // Test edge cases
    EXPECT_NO_THROW({
        // Test with various inputs
    });
}

int main(int argc, char **argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}"""

        return test_code

    def _generate_go_tests(self, code: str) -> Optional[str]:
        """生成Go单元测试"""
        # 提取包名和函数名
        package_pattern = r"package\s+(\w+)"
        packages = re.findall(package_pattern, code)

        func_pattern = r"func\s+(\w+)\s*\("
        functions = re.findall(func_pattern, code)

        if not packages or not functions:
            return None

        package_name = packages[0]

        test_code = f"""package {package_name}

import (
    "testing"
)

func TestGeneratedFunctions(t *testing.T) {{
    tests := []struct {{
        name string
        testFunc func()
    }}{{"""

        for func_name in functions[:3]:  # 测试前3个函数
            test_code += f"""
        {{
            name: "{func_name}",
            testFunc: func() {{
                // Call {func_name} and verify results
                result := {func_name}()
                if result == nil {{
                    t.Errorf("{func_name}() returned nil")
                }}
            }},
        }},"""

        test_code += """
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            tt.testFunc()
        })
    }
}

func TestEdgeCases(t *testing.T) {
    // Test edge cases
    t.Run("NilInputs", func(t *testing.T) {
        // Test with nil or zero values
        // This is a template - actual tests depend on function signatures
    })
}"""

        return test_code

    def _load_test_templates(self) -> Dict[str, Dict[str, str]]:
        """加载测试模板"""
        return {
            "python": {
                "class_template": """
class {class_name}Test(unittest.TestCase):
    def setUp(self):
        self.instance = {class_name}()

    def test_basic(self):
        self.assertIsNotNone(self.instance)
""",
                "function_template": """
    def test_{func_name}(self):
        result = {func_name}({args})
        self.assertIsNotNone(result)
""",
            },
            "javascript": {
                "describe_template": """
describe('{name}', function() {
    it('should work', function() {
        {test_code}
    });
});
""",
                "test_template": """
        const result = {func_name}({args});
        assert(result !== undefined);
""",
            },
        }

    def get_test_coverage_estimate(self, code: str, test_code: str, language: str) -> float:
        """
        估算测试覆盖率

        Args:
            code: 源代码
            test_code: 测试代码
            language: 编程语言

        Returns:
            覆盖率估算 (0-1)
        """
        try:
            # 简单的覆盖率估算
            if language == "python":
                # 解析源代码
                source_tree = ast.parse(code)
                source_functions = [
                    node.name for node in ast.walk(source_tree) if isinstance(node, ast.FunctionDef)
                ]

                # 检查测试代码中是否调用了这些函数
                covered_functions = 0
                for func_name in source_functions:
                    if f"{func_name}(" in test_code or f"{func_name}()" in test_code:
                        covered_functions += 1

                return covered_functions / len(source_functions) if source_functions else 0

            else:
                # 其他语言的简单估算
                return 0.5  # 保守估算

        except Exception:
            return 0.0

    def validate_test_code(self, test_code: str, language: str) -> bool:
        """
        验证测试代码的语法

        Args:
            test_code: 测试代码
            language: 编程语言

        Returns:
            是否语法正确
        """
        try:
            if language == "python":
                ast.parse(test_code)
                return True
            elif language in ["javascript", "typescript"]:
                # 基本检查
                return self._validate_js_test_syntax(test_code)
            else:
                return len(test_code.strip()) > 0
        except Exception:
            return False

    def _validate_js_test_syntax(self, code: str) -> bool:
        """验证JavaScript测试语法"""
        # 检查基本的describe/it结构
        if "describe(" not in code or "it(" not in code:
            return False

        # 检查括号匹配
        brackets = {"(": ")", "[": "]", "{": "}"}
        stack = []

        for char in code:
            if char in brackets:
                stack.append(char)
            elif char in brackets.values():
                if not stack or brackets[stack[-1]] != char:
                    return False
                stack.pop()

        return len(stack) == 0
