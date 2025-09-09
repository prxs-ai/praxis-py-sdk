#!/usr/bin/env python3

import sys
import json
import os
from pathlib import Path


def format_json_data(data: str, indent_size: int = 2) -> dict:
    try:
        parsed_data = json.loads(data)
        
        formatted = json.dumps(parsed_data, indent=indent_size, ensure_ascii=False, sort_keys=True)
        minified = json.dumps(parsed_data, separators=(',', ':'), ensure_ascii=False)
        
        return {
            "success": True,
            "original_size": len(data),
            "formatted_size": len(formatted),
            "minified_size": len(minified),
            "formatted": formatted,
            "minified": minified
        }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Invalid JSON: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def format_json_file(file_path: str, indent_size: int = 2) -> dict:
    try:
        path = Path(file_path)
        if not path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}"
            }
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return format_json_data(content, indent_size)
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def main():
    file_path = os.environ.get('FILE_PATH') or os.environ.get('file_path')
    json_data = os.environ.get('JSON_DATA') or os.environ.get('json_data')
    indent_str = os.environ.get('INDENT') or os.environ.get('indent') or "2"
    
    try:
        indent_size = int(indent_str)
    except ValueError:
        indent_size = 2
    
    if file_path:
        result = format_json_file(file_path, indent_size)
    elif json_data:
        result = format_json_data(json_data, indent_size)
    elif len(sys.argv) > 1:
        arg = sys.argv[1]
        if Path(arg).exists():
            result = format_json_file(arg, indent_size)
        else:
            result = format_json_data(arg, indent_size)
    else:
        result = {
            "success": False,
            "error": "Either FILE_PATH or JSON_DATA environment variable required, or provide as command line argument"
        }
    
    print(json.dumps(result, indent=2))
    
    if not result.get("success", False):
        sys.exit(1)


if __name__ == "__main__":
    main()