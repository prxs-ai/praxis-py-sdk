#!/usr/bin/env python3

import sys
import json
import os
import math
import re
from typing import Union


def safe_eval_expression(expression: str) -> dict:
    try:
        expression = expression.strip()
        
        allowed_names = {
            'abs': abs, 'round': round, 'min': min, 'max': max,
            'sum': sum, 'pow': pow,
            'sqrt': math.sqrt, 'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
            'log': math.log, 'log10': math.log10, 'exp': math.exp,
            'pi': math.pi, 'e': math.e
        }
        
        allowed_chars = set('0123456789+-*/().^ abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_,')
        if not all(c in allowed_chars for c in expression):
            return {
                "success": False,
                "error": "Expression contains invalid characters"
            }
        
        expression = expression.replace('^', '**')
        
        code = compile(expression, '<string>', 'eval')
        
        for name in code.co_names:
            if name not in allowed_names:
                return {
                    "success": False,
                    "error": f"Function or variable '{name}' is not allowed"
                }
        
        result = eval(code, {"__builtins__": {}}, allowed_names)
        
        return {
            "success": True,
            "expression": expression,
            "result": result,
            "result_type": type(result).__name__
        }
    except ZeroDivisionError:
        return {
            "success": False,
            "error": "Division by zero"
        }
    except ValueError as e:
        return {
            "success": False,
            "error": f"Math error: {str(e)}"
        }
    except SyntaxError as e:
        return {
            "success": False,
            "error": f"Syntax error: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def perform_basic_operation(num1: float, num2: float, operation: str) -> dict:
    try:
        operations = {
            'add': lambda x, y: x + y,
            'subtract': lambda x, y: x - y,
            'multiply': lambda x, y: x * y,
            'divide': lambda x, y: x / y if y != 0 else None,
            'power': lambda x, y: x ** y,
            'modulo': lambda x, y: x % y if y != 0 else None
        }
        
        if operation not in operations:
            return {
                "success": False,
                "error": f"Unknown operation: {operation}. Supported: {list(operations.keys())}"
            }
        
        result = operations[operation](num1, num2)
        if result is None:
            return {
                "success": False,
                "error": "Division by zero"
            }
        
        return {
            "success": True,
            "operation": operation,
            "operands": [num1, num2],
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def main():
    expression = os.environ.get('EXPRESSION') or os.environ.get('expression')
    operation = os.environ.get('OPERATION') or os.environ.get('operation')
    num1_str = os.environ.get('NUM1') or os.environ.get('num1')
    num2_str = os.environ.get('NUM2') or os.environ.get('num2')
    
    if expression:
        result = safe_eval_expression(expression)
    elif operation and num1_str and num2_str:
        try:
            num1 = float(num1_str)
            num2 = float(num2_str)
            result = perform_basic_operation(num1, num2, operation.lower())
        except ValueError:
            result = {
                "success": False,
                "error": "Invalid number format"
            }
    elif len(sys.argv) >= 2:
        if len(sys.argv) == 2:
            result = safe_eval_expression(sys.argv[1])
        elif len(sys.argv) == 4:
            try:
                num1 = float(sys.argv[1])
                operation = sys.argv[2]
                num2 = float(sys.argv[3])
                result = perform_basic_operation(num1, num2, operation.lower())
            except ValueError:
                result = {
                    "success": False,
                    "error": "Invalid number format in arguments"
                }
        else:
            result = {
                "success": False,
                "error": "Usage: EXPRESSION='2+2' or NUM1=5 OPERATION=add NUM2=3 or as args: '2+2' or '5 add 3'"
            }
    else:
        result = {
            "success": False,
            "error": "Provide EXPRESSION environment variable or NUM1, OPERATION, NUM2 variables"
        }
    
    print(json.dumps(result, indent=2))
    
    if not result.get("success", False):
        sys.exit(1)


if __name__ == "__main__":
    main()