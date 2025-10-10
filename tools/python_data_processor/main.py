#!/usr/bin/env python3
"""Python Data Processor Tool for Dagger execution.
Demonstrates multi-language tool support with data analysis capabilities.
"""

import json
import os
import platform
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_env(key: str, default: str = "") -> str:
    """Get environment variable with default value."""
    return os.getenv(key, default)


def process_numeric_data(data: list[float]) -> dict[str, Any]:
    """Process numeric data and return statistics."""
    if not data:
        return {"error": "No data provided"}

    return {
        "count": len(data),
        "sum": sum(data),
        "mean": statistics.mean(data),
        "median": statistics.median(data),
        "min": min(data),
        "max": max(data),
        "range": max(data) - min(data),
        "std_dev": statistics.stdev(data) if len(data) > 1 else 0,
    }


def process_text_data(text: str) -> dict[str, Any]:
    """Process text data and return analysis."""
    if not text:
        return {"error": "No text provided"}

    words = text.split()
    sentences = text.split(".")

    return {
        "char_count": len(text),
        "word_count": len(words),
        "sentence_count": len([s for s in sentences if s.strip()]),
        "avg_word_length": sum(len(word) for word in words) / len(words)
        if words
        else 0,
        "unique_words": len(set(word.lower().strip(".,!?;:") for word in words)),
        "longest_word": max(words, key=len) if words else "",
    }


def analyze_file_data(file_path: str) -> dict[str, Any]:
    """Analyze data from a file."""
    try:
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}

        with open(file_path, encoding="utf-8") as f:
            content = f.read().strip()

        # Try to parse as JSON first
        try:
            data = json.loads(content)
            if isinstance(data, list) and all(
                isinstance(x, (int, float)) for x in data
            ):
                return {"type": "numeric", "analysis": process_numeric_data(data)}
            return {
                "type": "json",
                "analysis": {"structure": type(data).__name__, "content": data},
            }
        except json.JSONDecodeError:
            pass

        # Try to parse as comma-separated numbers
        try:
            numbers = [float(x.strip()) for x in content.split(",")]
            return {"type": "numeric", "analysis": process_numeric_data(numbers)}
        except ValueError:
            pass

        # Treat as text
        return {"type": "text", "analysis": process_text_data(content)}

    except Exception as e:
        return {"error": f"Failed to analyze file: {str(e)}"}


def get_system_info() -> dict[str, Any]:
    """Get system information."""
    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "architecture": platform.machine(),
        "tool_name": "python_data_processor",
        "execution_time": datetime.now().isoformat(),
        "working_dir": os.getcwd(),
    }


def main():
    """Main entry point for Dagger tool."""
    print("🐍 PYTHON DATA PROCESSOR STARTED")
    print("=" * 60)

    # Get parameters from environment variables
    operation = get_env("ARG_OPERATION", "stats")
    data_input = get_env("ARG_DATA", "")
    data_file = get_env("ARG_FILE", "")
    output_format = get_env("ARG_FORMAT", "text")

    print(f"📊 Operation: {operation}")
    print(f"💾 Data Input: {data_input[:50]}{'...' if len(data_input) > 50 else ''}")
    print(f"📁 Data File: {data_file}")
    print(f"📄 Output Format: {output_format}")
    print("-" * 60)

    # Process based on operation
    result = {
        "operation": operation,
        "success": False,
        "system_info": get_system_info(),
        "timestamp": int(time.time()),
    }

    try:
        print("⏳ Processing data...")
        time.sleep(0.5)  # Simulate processing

        if operation == "file" and data_file:
            # Analyze file
            file_result = analyze_file_data(data_file)
            result.update(file_result)
            result["success"] = "error" not in file_result

        elif operation == "numbers" and data_input:
            # Process numbers
            try:
                numbers = [float(x.strip()) for x in data_input.split(",")]
                result["analysis"] = process_numeric_data(numbers)
                result["success"] = True
            except ValueError as e:
                result["error"] = f"Invalid number format: {e}"

        elif operation == "text" and data_input:
            # Process text
            result["analysis"] = process_text_data(data_input)
            result["success"] = True

        elif operation == "stats" and data_input:
            # General statistics
            try:
                numbers = [float(x.strip()) for x in data_input.split(",")]
                result["analysis"] = process_numeric_data(numbers)
                result["success"] = True
            except ValueError:
                result["analysis"] = process_text_data(data_input)
                result["success"] = True

        else:
            result["error"] = f"Invalid operation '{operation}' or missing data"

    except Exception as e:
        result["error"] = f"Processing failed: {str(e)}"

    # Output results
    if result["success"]:
        print("✅ PROCESSING COMPLETED SUCCESSFULLY")
    else:
        print("❌ PROCESSING FAILED")
        if "error" in result:
            print(f"💥 Error: {result['error']}")

    print("-" * 60)

    if output_format.lower() == "json":
        print("📋 JSON OUTPUT:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("📋 PROCESSING RESULTS:")
        print(f"🎯 Operation: {result['operation']}")
        print(f"✅ Success: {result['success']}")

        if "analysis" in result:
            print("📊 Analysis Results:")
            for key, value in result["analysis"].items():
                print(f"   📈 {key}: {value}")

        if "error" in result:
            print(f"❌ Error: {result['error']}")

        sys_info = result["system_info"]
        print(f"🐍 Python: {sys_info['python_version']}")
        print(f"💻 Platform: {sys_info['platform']}")
        print(f"⏰ Executed: {sys_info['execution_time']}")

    print("-" * 60)
    print("🎉 PYTHON DATA PROCESSOR COMPLETED")

    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
