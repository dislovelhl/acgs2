"""
ACGS-2 Language Constraints
为不同编程语言定义CFG和JSON Schema约束
"""

import logging
from typing import Dict, Any, Optional
import json

logger = logging.getLogger(__name__)


class LanguageConstraints:
    """
    语言约束管理器 - 为每种编程语言定义语法约束
    """

    def __init__(self):
        """初始化语言约束"""
        self.constraints = {}
        self._load_base_constraints()

    def _load_base_constraints(self):
        """加载基础语言约束"""
        # Python约束
        self.constraints['python'] = {
            'language': 'python',
            'file_extension': '.py',
            'indent_style': 'spaces',
            'indent_size': 4,
            'max_line_length': 79,
            'grammar_rules': self._get_python_grammar(),
            'json_schema': self._get_python_schema(),
            'syntax_patterns': [
                r'^def\s+\w+\s*\([^)]*\)\s*:',
                r'^class\s+\w+.*:',
                r'^if\s+.*:',
                r'^for\s+.*:',
                r'^while\s+.*:',
                r'^try\s*:',
                r'^except\s+.*:',
                r'^with\s+.*:',
            ],
            'forbidden_patterns': [
                r'^\s*except\s*:',  # 空的except块
                r'^\s*pass\s*$',     # 孤立的pass
            ]
        }

        # JavaScript约束
        self.constraints['javascript'] = {
            'language': 'javascript',
            'file_extension': '.js',
            'indent_style': 'spaces',
            'indent_size': 2,
            'max_line_length': 80,
            'grammar_rules': self._get_javascript_grammar(),
            'json_schema': self._get_javascript_schema(),
            'syntax_patterns': [
                r'^function\s+\w+\s*\([^)]*\)\s*{',
                r'^const\s+\w+\s*=',
                r'^let\s+\w+\s*=',
                r'^var\s+\w+\s*=',
                r'^if\s*\([^)]*\)\s*{',
                r'^for\s*\([^)]*\)\s*{',
                r'^while\s*\([^)]*\)\s*{',
                r'^try\s*{',
                r'^catch\s*\([^)]*\)\s*{',
            ],
            'forbidden_patterns': [
                r'^\s*}\s*$',  # 孤立的大括号
                r'console\.log\s*\([^)]*$',  # 未闭合的console.log
            ]
        }

        # TypeScript约束（继承JavaScript）
        self.constraints['typescript'] = self.constraints['javascript'].copy()
        self.constraints['typescript'].update({
            'language': 'typescript',
            'file_extension': '.ts',
            'type_annotations': True,
            'interface_support': True,
        })

        # Java约束
        self.constraints['java'] = {
            'language': 'java',
            'file_extension': '.java',
            'indent_style': 'spaces',
            'indent_size': 4,
            'max_line_length': 100,
            'grammar_rules': self._get_java_grammar(),
            'json_schema': self._get_java_schema(),
            'syntax_patterns': [
                r'^public\s+class\s+\w+',
                r'^public\s+static\s+void\s+main',
                r'^public\s+\w+\s+\w+\s*\([^)]*\)\s*{',
                r'^if\s*\([^)]*\)\s*{',
                r'^for\s*\([^)]*\)\s*{',
                r'^while\s*\([^)]*\)\s*{',
                r'^try\s*{',
                r'^catch\s*\([^)]*\)\s*{',
            ],
            'forbidden_patterns': [
                r'^\s*}\s*$',  # 孤立的大括号
                r'System\.out\.println\s*\([^)]*$',  # 未闭合的println
            ]
        }

        # C++约束
        self.constraints['cpp'] = {
            'language': 'cpp',
            'file_extension': '.cpp',
            'indent_style': 'spaces',
            'indent_size': 4,
            'max_line_length': 100,
            'grammar_rules': self._get_cpp_grammar(),
            'json_schema': self._get_cpp_schema(),
            'syntax_patterns': [
                r'#include\s*<.*>',
                r'int\s+main\s*\([^)]*\)\s*{',
                r'void\s+\w+\s*\([^)]*\)\s*{',
                r'class\s+\w+\s*{',
                r'if\s*\([^)]*\)\s*{',
                r'for\s*\([^)]*\)\s*{',
                r'while\s*\([^)]*\)\s*{',
                r'try\s*{',
                r'catch\s*\([^)]*\)\s*{',
            ],
            'forbidden_patterns': [
                r'^\s*}\s*$',  # 孤立的大括号
                r'std::cout\s*<<\s*[^;]*$',  # 未结束的cout
            ]
        }

        # Go约束
        self.constraints['go'] = {
            'language': 'go',
            'file_extension': '.go',
            'indent_style': 'tabs',
            'indent_size': 1,
            'max_line_length': 100,
            'grammar_rules': self._get_go_grammar(),
            'json_schema': self._get_go_schema(),
            'syntax_patterns': [
                r'package\s+\w+',
                r'import\s*\(',
                r'func\s+\w+\s*\([^)]*\)\s*{',
                r'if\s+.*{',
                r'for\s+.*{',
                r'switch\s+.*{',
                r'type\s+\w+\s+struct\s*{',
            ],
            'forbidden_patterns': [
                r'^\s*}\s*$',  # 孤立的大括号
                r'fmt\.Printf?\s*\([^)]*$',  # 未闭合的fmt.Print
            ]
        }

    def get_constraints(self, language: str) -> Dict[str, Any]:
        """
        获取指定语言的约束

        Args:
            language: 编程语言名称

        Returns:
            语言约束字典
        """
        language = language.lower()
        if language in self.constraints:
            return self.constraints[language].copy()
        else:
            logger.warning(f"No constraints defined for language: {language}")
            return self._get_default_constraints(language)

    def _get_default_constraints(self, language: str) -> Dict[str, Any]:
        """获取默认约束"""
        return {
            'language': language,
            'file_extension': f'.{language}',
            'indent_style': 'spaces',
            'indent_size': 4,
            'max_line_length': 80,
            'syntax_patterns': [],
            'forbidden_patterns': [],
        }

    def _get_python_grammar(self) -> str:
        """Python CFG语法"""
        return r"""
        start: statement+

        statement: simple_statement | compound_statement
        simple_statement: assignment | expression | pass_statement | return_statement
        compound_statement: if_statement | for_statement | while_statement | try_statement | with_statement | def_statement | class_statement

        assignment: NAME "=" expression
        expression: NAME | NUMBER | STRING | call | binary_expr
        call: NAME "(" arguments? ")"
        arguments: expression ("," expression)*

        if_statement: "if" expression ":" suite ("elif" expression ":" suite)* ("else" ":" suite)?
        for_statement: "for" NAME "in" expression ":" suite
        while_statement: "while" expression ":" suite
        try_statement: "try" ":" suite ("except" expression? ":" suite)+ ("finally" ":" suite)?
        with_statement: "with" expression ("as" NAME)? ":" suite
        def_statement: "def" NAME "(" parameters? ")" ":" suite
        class_statement: "class" NAME ":" suite

        parameters: NAME ("," NAME)*
        suite: NEWLINE INDENT statement+ DEDENT

        NAME: /[a-zA-Z_][a-zA-Z0-9_]*/
        NUMBER: /\d+/
        STRING: /"[^"]*"|'[^']*'/
        NEWLINE: /\n/
        INDENT: /[ \t]+/
        DEDENT: //
        """

    def _get_python_schema(self) -> Dict[str, Any]:
        """Python JSON Schema"""
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code that follows PEP 8 and is syntactically correct"
                },
                "functions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "parameters": {"type": "array", "items": {"type": "string"}},
                            "docstring": {"type": "string"}
                        }
                    }
                },
                "imports": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["code"]
        }

    def _get_javascript_grammar(self) -> str:
        """JavaScript CFG语法"""
        return r"""
        start: statement*

        statement: var_declaration | function_declaration | if_statement | for_statement | expression_statement | block

        var_declaration: ("var" | "let" | "const") NAME ("=" expression)? ";"
        function_declaration: "function" NAME "(" parameters? ")" block
        if_statement: "if" "(" expression ")" statement ("else" statement)?
        for_statement: "for" "(" var_declaration? ";" expression? ";" expression? ")" statement
        expression_statement: expression ";"
        block: "{" statement* "}"

        expression: assignment | call | binary_expr | NAME | NUMBER | STRING
        assignment: NAME "=" expression
        call: NAME "(" arguments? ")"
        arguments: expression ("," expression)*
        binary_expr: expression ("+" | "-" | "*" | "/") expression

        parameters: NAME ("," NAME)*
        NAME: /[a-zA-Z_$][a-zA-Z0-9_$]*/
        NUMBER: /\d+/
        STRING: /"[^"]*"|'[^']*'/
        """

    def _get_javascript_schema(self) -> Dict[str, Any]:
        """JavaScript JSON Schema"""
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "JavaScript code that follows best practices"
                },
                "functions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "parameters": {"type": "array", "items": {"type": "string"}},
                            "async": {"type": "boolean"}
                        }
                    }
                },
                "variables": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["code"]
        }

    def _get_java_grammar(self) -> str:
        """Java CFG语法"""
        return r"""
        start: class_declaration*

        class_declaration: "public" "class" NAME "{" class_body "}"
        class_body: (field_declaration | method_declaration)*

        field_declaration: ("public" | "private") type NAME ";"
        method_declaration: ("public" | "private") type NAME "(" parameters? ")" block

        type: "int" | "String" | "void" | NAME
        parameters: parameter ("," parameter)*
        parameter: type NAME

        block: "{" statement* "}"
        statement: var_declaration | if_statement | for_statement | return_statement | expression_statement
        var_declaration: type NAME ("=" expression)? ";"
        if_statement: "if" "(" expression ")" statement ("else" statement)?
        for_statement: "for" "(" var_declaration expression ";" expression ")" statement
        return_statement: "return" expression? ";"
        expression_statement: expression ";"

        expression: assignment | call | binary_expr | NAME | NUMBER | STRING
        assignment: NAME "=" expression
        call: NAME "(" arguments? ")"
        arguments: expression ("," expression)*
        binary_expr: expression ("+" | "-" | "*" | "/") expression

        NAME: /[a-zA-Z_][a-zA-Z0-9_]*/
        NUMBER: /\d+/
        STRING: /"[^"]*"|'[^']*'/
        """

    def _get_java_schema(self) -> Dict[str, Any]:
        """Java JSON Schema"""
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Java code that follows Java conventions"
                },
                "class_name": {"type": "string"},
                "methods": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "return_type": {"type": "string"},
                            "parameters": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                }
            },
            "required": ["code", "class_name"]
        }

    def _get_cpp_grammar(self) -> str:
        """C++ CFG语法"""
        return r"""
        start: (include_directive | function_definition | class_definition)*

        include_directive: "#include" ("<" NAME ">" | "\"" NAME "\"")
        function_definition: type NAME "(" parameters? ")" block
        class_definition: "class" NAME "{" class_body "}" ";"

        class_body: (access_specifier ":" member_declaration*)*
        access_specifier: "public" | "private" | "protected"
        member_declaration: field_declaration | method_declaration

        type: "int" | "void" | "string" | NAME
        parameters: parameter ("," parameter)*
        parameter: type NAME

        field_declaration: type NAME ";"
        method_declaration: type NAME "(" parameters? ")" block

        block: "{" statement* "}"
        statement: var_declaration | if_statement | for_statement | return_statement | expression_statement
        var_declaration: type NAME ("=" expression)? ";"
        if_statement: "if" "(" expression ")" statement ("else" statement)?
        for_statement: "for" "(" var_declaration expression ";" expression ")" statement
        return_statement: "return" expression? ";"
        expression_statement: expression ";"

        expression: assignment | call | binary_expr | NAME | NUMBER | STRING
        assignment: NAME "=" expression
        call: NAME "(" arguments? ")"
        arguments: expression ("," expression)*
        binary_expr: expression ("+" | "-" | "*" | "/") expression

        NAME: /[a-zA-Z_][a-zA-Z0-9_]*/
        NUMBER: /\d+/
        STRING: /"[^"]*"|'[^']*'/
        """

    def _get_cpp_schema(self) -> Dict[str, Any]:
        """C++ JSON Schema"""
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "C++ code that follows C++ best practices"
                },
                "includes": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "functions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "return_type": {"type": "string"},
                            "parameters": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                }
            },
            "required": ["code"]
        }

    def _get_go_grammar(self) -> str:
        """Go CFG语法"""
        return r"""
        start: package_declaration import_declaration* (function_declaration | type_declaration)*

        package_declaration: "package" NAME
        import_declaration: "import" ("(" STRING+ ")" | STRING)

        function_declaration: "func" NAME "(" parameters? ")" (type)? block
        type_declaration: "type" NAME type_spec
        type_spec: "struct" "{" field_declaration* "}" | "interface" "{" method_spec* "}"

        field_declaration: NAME type
        method_spec: NAME "(" parameters? ")" type

        type: "int" | "string" | "bool" | NAME
        parameters: parameter ("," parameter)*
        parameter: NAME type

        block: "{" statement* "}"
        statement: var_declaration | if_statement | for_statement | return_statement | expression_statement
        var_declaration: ("var" NAME type ("=" expression)? | NAME ":=" expression)
        if_statement: "if" expression block ("else" (if_statement | block))?
        for_statement: "for" expression? block
        return_statement: "return" expression?
        expression_statement: expression

        expression: assignment | call | binary_expr | NAME | NUMBER | STRING
        assignment: NAME "=" expression
        call: NAME "(" arguments? ")"
        arguments: expression ("," expression)*
        binary_expr: expression ("+" | "-" | "*" | "/") expression

        NAME: /[a-zA-Z_][a-zA-Z0-9_]*/
        NUMBER: /\d+/
        STRING: /"[^"]*"|'[^']*'/
        """

    def _get_go_schema(self) -> Dict[str, Any]:
        """Go JSON Schema"""
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Go code that follows Go conventions"
                },
                "package": {"type": "string"},
                "imports": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "functions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "parameters": {"type": "array", "items": {"type": "string"}},
                            "return_type": {"type": "string"}
                        }
                    }
                }
            },
            "required": ["code", "package"]
        }

    def add_custom_constraint(self, language: str, constraint_name: str, constraint_value: Any):
        """
        添加自定义约束

        Args:
            language: 编程语言
            constraint_name: 约束名称
            constraint_value: 约束值
        """
        language = language.lower()
        if language not in self.constraints:
            self.constraints[language] = self._get_default_constraints(language)

        self.constraints[language][constraint_name] = constraint_value
        logger.info(f"Added custom constraint {constraint_name} for {language}")

    def update_constraint(self, language: str, constraint_name: str, constraint_value: Any):
        """
        更新现有约束

        Args:
            language: 编程语言
            constraint_name: 约束名称
            constraint_value: 约束值
        """
        language = language.lower()
        if language in self.constraints:
            self.constraints[language][constraint_name] = constraint_value
            logger.info(f"Updated constraint {constraint_name} for {language}")
        else:
            logger.warning(f"Language {language} not found, cannot update constraint")