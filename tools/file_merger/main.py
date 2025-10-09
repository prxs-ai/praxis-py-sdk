#!/usr/bin/env python3

import json
import os
import sys
from pathlib import Path
from typing import List


def merge_files(
    file_paths: list[str], output_path: str = None, separator: str = "\n"
) -> dict:
    try:
        if not file_paths:
            return {"success": False, "error": "No input files specified"}

        merged_content = []
        file_info = []
        total_size = 0

        for file_path in file_paths:
            path = Path(file_path.strip())
            if not path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}

            try:
                with open(path, encoding="utf-8") as f:
                    content = f.read()
                    merged_content.append(content)

                    file_info.append(
                        {
                            "file": str(path),
                            "size": len(content),
                            "lines": len(content.split("\n")),
                        }
                    )
                    total_size += len(content)
            except UnicodeDecodeError:
                try:
                    with open(path, encoding="latin-1") as f:
                        content = f.read()
                        merged_content.append(content)

                        file_info.append(
                            {
                                "file": str(path),
                                "size": len(content),
                                "lines": len(content.split("\n")),
                                "encoding": "latin-1",
                            }
                        )
                        total_size += len(content)
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Could not read file {file_path}: {str(e)}",
                    }

        final_content = separator.join(merged_content)

        result = {
            "success": True,
            "files_merged": len(file_paths),
            "total_input_size": total_size,
            "output_size": len(final_content),
            "file_details": file_info,
            "separator_used": repr(separator),
        }

        if output_path:
            try:
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)

                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(final_content)

                result["output_file"] = str(output_file)
                result["output_written"] = True
            except Exception as e:
                result["output_error"] = str(e)
                result["output_written"] = False
        else:
            result["merged_content"] = final_content
            result["content_preview"] = (
                final_content[:500] + "..."
                if len(final_content) > 500
                else final_content
            )

        return result

    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    files_env = os.environ.get("FILES") or os.environ.get("files")
    output_path = os.environ.get("OUTPUT_PATH") or os.environ.get("output_path")
    separator = os.environ.get("SEPARATOR") or os.environ.get("separator") or "\n"

    if separator == "\\n":
        separator = "\n"
    elif separator == "\\t":
        separator = "\t"

    if files_env:
        file_paths = [f.strip() for f in files_env.split(",") if f.strip()]
    elif len(sys.argv) > 1:
        file_paths = sys.argv[1:]
        if len(file_paths) > 1 and not output_path:
            last_arg = file_paths[-1]
            if not Path(last_arg).exists() and "." in last_arg:
                output_path = file_paths.pop()
    else:
        result = {
            "success": False,
            "error": "Provide FILES environment variable (comma-separated) or file paths as arguments",
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)

    result = merge_files(file_paths, output_path, separator)
    print(json.dumps(result, indent=2))

    if not result.get("success", False):
        sys.exit(1)


if __name__ == "__main__":
    main()
