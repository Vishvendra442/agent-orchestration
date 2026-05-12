import ast
import operator
from langchain_core.tools import tool

from app.runtime.tools.registry import register_tool

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
}


def _safe_eval(node):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp):
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return _OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp):
        operand = _safe_eval(node.operand)
        return _OPS[type(node.op)](operand)
    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression. Supports +, -, *, /, **, %. Example: '(2 + 3) * 4'"""
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree)
        return str(result)
    except Exception as exc:
        return f"Calculation error: {exc}"


register_tool("calculator", calculator)
