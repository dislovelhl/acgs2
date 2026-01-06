---
name: Security Hardening Plan
overview: ""
todos: []
---

# ACGS-2 Security Hardening and Quality Fixes

This plan addresses the findings from the `/sc:analyze` report, prioritized by severity.---

## Phase 1: Critical Security Fixes

### 1.1 Remove `eval()` from Tool Execution

**Files:**

- [`src/acgs2/components/tms.py`](src/acgs2/components/tms.py) (line 283)
- [`src/acgs2/components/cre.py`](src/acgs2/components/cre.py) (line 513)

**Change:** Replace `eval()` with a safe math parser. Use `ast.literal_eval` for simple literals or implement a whitelist-based expression evaluator.

```python
 # Before (DANGER)
result = eval(expression)

# After (safe)
import ast
import operator

SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}

def safe_eval_expr(expr: str) -> float:
    """Evaluate arithmetic expression safely."""
    tree = ast.parse(expr, mode='eval')
    return _eval_node(tree.body)

def _eval_node(node):
    if isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.BinOp):
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        return SAFE_OPS[type(node.op)](left, right)
    elif isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand)
        return SAFE_OPS[type(node.op)](operand)
    else:
        raise ValueError(f"Unsupported expression: {ast.dump(node)}")








```
