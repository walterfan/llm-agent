"""
Calculator tool for the Personal Secretary agent.

Provides safe mathematical expression evaluation.
"""

import ast
import math
import operator
from typing import Any, Union

from pydantic import BaseModel, Field

from app.services.secretary_agent.tracing import trace_tool_call


class CalculatorInput(BaseModel):
    """Input schema for calculator tool."""

    expression: str = Field(
        description="Mathematical expression to evaluate (e.g., '2 + 2', 'sqrt(16)', '3 * 4 / 2')"
    )


class CalculatorResponse(BaseModel):
    """Response schema for calculator tool."""

    expression: str = Field(description="Original expression")
    result: Union[float, int, str] = Field(description="Calculation result")
    formatted: str = Field(description="Human-readable result")


# Allowed operators for safe evaluation
ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Allowed math functions
ALLOWED_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "exp": math.exp,
    "pow": pow,
    "floor": math.floor,
    "ceil": math.ceil,
    "pi": math.pi,
    "e": math.e,
}


class SafeEvaluator(ast.NodeVisitor):
    """
    Safe expression evaluator using AST.

    Only allows basic arithmetic operations and approved math functions.
    Prevents code execution and access to builtins.
    """

    def visit_Expression(self, node: ast.Expression) -> Any:
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> Any:
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant type: {type(node.value)}")

    # For Python < 3.8 compatibility
    def visit_Num(self, node: ast.Num) -> Any:
        return node.n

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        left = self.visit(node.left)
        right = self.visit(node.right)
        op_type = type(node.op)

        if op_type not in ALLOWED_OPERATORS:
            raise ValueError(f"Unsupported operator: {op_type.__name__}")

        return ALLOWED_OPERATORS[op_type](left, right)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        operand = self.visit(node.operand)
        op_type = type(node.op)

        if op_type not in ALLOWED_OPERATORS:
            raise ValueError(f"Unsupported operator: {op_type.__name__}")

        return ALLOWED_OPERATORS[op_type](operand)

    def visit_Call(self, node: ast.Call) -> Any:
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only simple function calls are allowed")

        func_name = node.func.id

        if func_name not in ALLOWED_FUNCTIONS:
            raise ValueError(f"Function not allowed: {func_name}")

        func = ALLOWED_FUNCTIONS[func_name]
        args = [self.visit(arg) for arg in node.args]

        return func(*args)

    def visit_Name(self, node: ast.Name) -> Any:
        # Allow access to constants like pi and e
        if node.id in ALLOWED_FUNCTIONS:
            value = ALLOWED_FUNCTIONS[node.id]
            if isinstance(value, (int, float)):
                return value
        raise ValueError(f"Name not allowed: {node.id}")

    def generic_visit(self, node: ast.AST) -> Any:
        raise ValueError(f"Unsupported operation: {type(node).__name__}")


def safe_eval(expression: str) -> Union[float, int]:
    """
    Safely evaluate a mathematical expression.

    Args:
        expression: Mathematical expression string

    Returns:
        Numeric result

    Raises:
        ValueError: If expression contains disallowed operations
    """
    try:
        tree = ast.parse(expression, mode="eval")
        evaluator = SafeEvaluator()
        return evaluator.visit(tree)
    except SyntaxError as e:
        raise ValueError(f"Invalid expression syntax: {e}")


@trace_tool_call
def calculate(expression: str) -> CalculatorResponse:
    """
    Evaluate a mathematical expression safely.

    Supports:
    - Basic arithmetic: +, -, *, /, //, %, **
    - Math functions: sqrt, sin, cos, tan, log, log10, exp, pow, floor, ceil
    - Constants: pi, e
    - Aggregations: abs, round, min, max, sum

    Args:
        expression: Mathematical expression to evaluate

    Returns:
        CalculatorResponse with the result
    """
    try:
        result = safe_eval(expression)

        # Format result
        if isinstance(result, float):
            if result.is_integer():
                formatted = str(int(result))
            elif abs(result) < 0.0001 or abs(result) > 1000000:
                formatted = f"{result:.6e}"
            else:
                formatted = f"{result:.6f}".rstrip("0").rstrip(".")
        else:
            formatted = str(result)

        return CalculatorResponse(
            expression=expression,
            result=result,
            formatted=f"{expression} = {formatted}",
        )

    except ValueError as e:
        return CalculatorResponse(
            expression=expression,
            result="Error",
            formatted=f"计算错误: {str(e)}",
        )
    except ZeroDivisionError:
        return CalculatorResponse(
            expression=expression,
            result="Error",
            formatted="计算错误: 除数不能为零",
        )
    except Exception as e:
        return CalculatorResponse(
            expression=expression,
            result="Error",
            formatted=f"计算错误: {str(e)}",
        )
